// Experimental, opt-in Windows resident-layer streaming for CPU mmap weights.
// Keeps virtual mappings and live inference state; evicts only mapped weight pages.
// Included after llama-model.h in the pinned llama-context.cpp translation unit.
#pragma once
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <psapi.h>
#include <cstdlib>
#include <cstdio>
#include <cstring>
#include <string>
#include <vector>

static size_t lwb_rss_bytes() {
    PROCESS_MEMORY_COUNTERS counters{};
    counters.cb = sizeof(counters);
    return K32GetProcessMemoryInfo(GetCurrentProcess(), &counters, sizeof(counters))
        ? counters.WorkingSetSize : 0;
}

static size_t lwb_resident_samples(std::vector<PSAPI_WORKING_SET_EX_INFORMATION> & samples) {
    if (samples.empty()) return 0;
    if (!K32QueryWorkingSetEx(GetCurrentProcess(), samples.data(),
            static_cast<DWORD>(samples.size()*sizeof(samples[0])))) return 0;
    size_t count = 0;
    for (const auto & sample : samples) count += sample.VirtualAttributes.Valid ? 1 : 0;
    return count;
}

static bool lwb_layer_eval(ggml_tensor * tensor, bool ask, void * user_data) {
    int layer = -1;
    const bool is_layer = std::sscanf(tensor->name, "l_out-%d", &layer) == 1;
    const bool is_final = std::strcmp(tensor->name, "result_output") == 0;
    if (ask) return is_layer || is_final;
    if (!is_layer && !is_final) return true;

    auto * model = static_cast<llama_model *>(user_data);
    const std::string prefix = is_layer ? "blk." + std::to_string(layer) + "." : "";
    struct range { void * data; size_t bytes; };
    std::vector<range> ranges;
    std::vector<PSAPI_WORKING_SET_EX_INFORMATION> samples;
    size_t bytes = 0;
    for (const auto & entry : model->tensors_by_name) {
        const bool block = entry.first.rfind("blk.", 0) == 0;
        if ((is_layer && entry.first.rfind(prefix, 0) != 0) || (is_final && block)) continue;
        ggml_tensor * weight = entry.second;
        if (weight->data == nullptr) continue;
        MEMORY_BASIC_INFORMATION info{};
        if (!VirtualQuery(weight->data, &info, sizeof(info)) || info.Type != MEM_MAPPED) continue;
        const size_t size = ggml_nbytes(weight);
        if (size == 0) continue;
        ranges.push_back({weight->data,size}); bytes += size;
        // Sample first/middle/last pages per weight, bounded by tensor count.
        for (size_t offset : {size_t(0),size/2,size-1}) {
            PSAPI_WORKING_SET_EX_INFORMATION sample{};
            sample.VirtualAddress = reinterpret_cast<void *>(
                (reinterpret_cast<uintptr_t>(weight->data)+offset) & ~uintptr_t(4095));
            samples.push_back(sample);
        }
    }
    const size_t before = lwb_resident_samples(samples);
    const size_t rss_before = lwb_rss_bytes();
    size_t requests = 0, errors = 0;
    for (const auto & r : ranges) {
        SetLastError(ERROR_SUCCESS);
        const BOOL ok = VirtualUnlock(r.data,r.bytes);
        const DWORD error = GetLastError();
        // Microsoft documents FALSE/ERROR_NOT_LOCKED as the expected result
        // when removing unlocked pages from this process's working set.
        if (ok || error == ERROR_NOT_LOCKED) requests++;
        else errors++;
    }
    const size_t after = lwb_resident_samples(samples);
    std::fprintf(stderr,
        "LWB_STREAM {\"layer\":%d,\"final\":%s,\"weight_ranges\":%zu,"
        "\"weight_span_bytes\":%zu,\"eviction_requests\":%zu,\"unexpected_errors\":%zu,"
        "\"sampled_pages\":%zu,\"resident_samples_before\":%zu,\"resident_samples_after\":%zu,"
        "\"rss_before\":%zu,\"rss_after\":%zu}\n",
        layer,is_final?"true":"false",ranges.size(),bytes,requests,errors,
        samples.size(),before,after,rss_before,lwb_rss_bytes());
    return errors == 0;
}

static bool lwb_layer_stream_enabled() {
    const char * env = std::getenv("LWB_LAYER_STREAM");
    return env != nullptr && std::strcmp(env,"1") == 0;
}
#endif
