# Import the Suite-3 winner GGUF into stock Ollama as qwen38-standard-q4.
# Does not change Ollama's global install path; creates/replaces one local tag.
$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Cache = Join-Path $Root 'results\model-cache\qwen38-standard-q4'
$Gguf = Join-Path $Cache 'Qwen3.8-27B.Q4_K_M.gguf'
$Manifest = Join-Path $Cache 'verified-manifest.json'
$Template = Join-Path $Root 'examples\paging\qwen38-standard-q4.Modelfile'
$Tag = 'qwen38-standard-q4'

if (-not (Test-Path $Gguf)) { throw "Missing winner GGUF: $Gguf" }
if (-not (Test-Path $Manifest)) { throw "Missing verified-manifest.json — refuse unverified import" }
if (-not (Test-Path $Template)) { throw "Missing Modelfile template: $Template" }

$Modelfile = Join-Path $Cache 'Modelfile'
Copy-Item -Force $Template $Modelfile
Push-Location $Cache
try {
  & ollama create $Tag -f $Modelfile
  if ($LASTEXITCODE) { throw "ollama create failed: $LASTEXITCODE" }
  & ollama show $Tag
  Write-Output "Imported Ollama tag: $Tag"
}
finally {
  Pop-Location
}
