# TICKET-040: An unexplained environment variable was hiding a CUDA toolchain mismatch

**Category:** CI/config / undocumented workaround
**Module:** vLLM serve environment (`VLLM_USE_FLASHINFER_SAMPLER=0`)

## Symptom
The vLLM start command carried `export VLLM_USE_FLASHINFER_SAMPLER=0` with no recorded
reason. Nobody maintaining the setup could say what it did or whether it was still needed.

Removing it as an experiment made the engine core fail at startup:

```
nvcc fatal   : Unknown option '--compress-mode=size'
ninja: build stopped: subcommand failed.
RuntimeError: Engine core initialization failed.
```

## Root cause
PyTorch and vLLM ship precompiled, but FlashInfer JIT-compiles its sampling kernels on
first use with whichever `nvcc` is on `PATH`. The WSL environment had two CUDA versions:

| Component | CUDA |
|---|---|
| PyTorch in the vLLM env (`torch 2.13.0+cu130`) | 13.0 |
| System `nvcc` (`/usr/bin/nvcc`, apt toolkit) | 12.0 |

FlashInfer passes `--compress-mode=size`, which the 12.0 compiler does not recognise, so
the build fails and the engine never starts. The variable routes sampling to the PyTorch
implementation, which needs no compilation.

## Fix
Kept the variable, now documented with the error it prevents and its cost: FlashInfer's
top-k/top-p sampling kernels, a negligible share of a decode step at one request at a
time. Upgrading the WSL toolkit to CUDA 13 is the alternative. It is worth measuring only
if throughput under concurrent load becomes a goal.

## Lesson
**An unexplained setting is a liability even when it works.** It cannot be safely removed,
changed or carried to a new machine, and the first person to tidy the config will delete
it. A workaround is finished only when the reason is written down next to it.

**Removing the setting is the fastest way to find its reason.** One controlled start
produced the exact error, the version mismatch and the cost, which is more than any
amount of reading about the flag would have.
