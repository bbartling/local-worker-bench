# Windows experiment snapshot

These are the Windows Cursor world-clock-lab handoff and supervised request
client saved on November 22, 2026. The source app ZIP and credentials are not
included. This is an educational standalone lab, not an application deployment.

The handoff retains that Windows host's paths and private LAN URL. The Python
client uses Windows RAM inspection, requires both 4B Q4 + 7B FP16 resident and
keeps them loaded. It is not the default portable worker or a Linux client.
The latest attempt stopped at 1.41 GiB free and restored the idle single-model
server; this snapshot does not mean those models are currently loaded.

For Mint with 4B Q4 + 30B Q4 use [the Mint checklist](../../docs/linux-mint-4b-30b-setup.md)
and [Linux handoff](../../docs/prompts/linux-mint-local-worker-handoff.md).
The ordinary repository client is portable and unloads models after each call.
