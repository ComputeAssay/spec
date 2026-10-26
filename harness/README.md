# Assay Verification Harness

**v0.2.0 — the `nccl-allreduce` probe, plus third-party acceptance evidence.** MIT-licensed, runs on your own metal, emits
signed JSON the registry ingests. This is the measured tier of [ASSAY-1](../spec/ASSAY-1.md)
(§8): grades on computeassay.com describe what sellers publish; a harness run replaces the
claim with a measurement.

**Status:** v0.2.0. v0.1 implements one probe of the seven in §8.1 — measured all-reduce bus
bandwidth (DCB) across your largest sellable allocation. It is the probe that matters most:
DCB is the number that separates a training cluster from eight GPUs sharing a name. The
remaining probes (`nccl-alltoall`, `csd-probe`, `checkpoint-burst`, `serving-latency`,
`soak-72h`, `power-telemetry`) land in order of buyer demand.

## What you need

- The fleet you actually sell — not a golden slice (§8.2: allocation must equal the maximum
  you sell as one unit; the run records what it saw).
- [nccl-tests](https://github.com/NVIDIA/nccl-tests) built for your stack (`all_reduce_perf`
  on `$PATH`, or point `--binary` at it).
- Your usual multi-node launcher (mpirun/srun) if the allocation spans nodes.
- A run nonce: `--fetch-nonce` pulls one from https://computeassay.com/api/nonce. Nonces are
  rounds of the public [drand](https://drand.love) randomness beacon, so anyone can check a run
  was not started before the nonce existed. Valid 72 h. Results without a nonce are ingested
  as self-reported, not Verified.

## Run

```bash
# check the parser first (no GPUs needed)
./assay_harness.py --self-test

# single node, 8 GPUs
./assay_harness.py --gpus 8 --fetch-nonce

# multi-node: wrap your launcher; the harness parses the combined output
./assay_harness.py --launcher "mpirun -np 64 -hostfile hosts.txt" --gpus-per-node 8 \
    --fetch-nonce --tenants 3 --allocation "64 GPU / 8 node block" --max-sellable \
    --line-rate-gbps 3200

# already ran all_reduce_perf yourself? parse the log
./assay_harness.py --from-output run.log --nonce <NONCE>
```

Output: `assay-probe-<timestamp>.json` — busbw at 1 GiB plus the 16 MiB–512 MiB curve,
environment capture, the §8.2 disclosures (allocation size, concurrent tenant count, run
window), and a SHA-256 self-hash. Sign it (`--sign <GPG-KEY>`) or send it as-is with the
nonce; we verify plausibility against your published specs either way.

## Anti-gaming (§8.2, enforced at ingestion)

- Runs under production tenancy — `--tenants` is recorded and cross-checked.
- Allocation = max sellable unit, recorded.
- Nonce window: results older than the nonce are rejected.
- Running and withholding is itself recorded.

## Founding cohort

The first operators through the harness are graded **free** — we run the probe with your
team, you keep the raw output, the teardown publishes either way. See
[computeassay.com/operators.html](https://computeassay.com/operators.html).

## Third-party acceptance evidence (v0.2.0)

Acceptance tests already exist; a buyer shouldn't have to pick one. `--evidence TYPE:PATH` (repeatable) hashes another
tool's output into the result and binds it to the run nonce, so a counterparty can later check that the report they are
shown is the one that was bundled.

```bash
# attach evidence to a probe run
./assay_harness.py --launcher "mpirun -np 64 -hostfile hosts.txt" --gpus-per-node 1 --fetch-nonce \
    --evidence nvidia-cre:cre-report.json --evidence clustermax-audit:audit-output.json

# bundle evidence alone, no probe
./assay_harness.py --evidence-only --fetch-nonce --evidence clustermax-audit:audit-output.json
```

| Type | Source | What the harness reads |
|---|---|---|
| `clustermax-audit` | SemiAnalysis's free ClusterMAX audit tool | hash; pass/fail status counts (JSON) or lines mentioning failure |
| `nvidia-cre` | NVIDIA Cluster Readiness Engine report | hash; pass/fail status counts |
| `nccl-log` | raw nccl-tests output | hash; bus bandwidth at the largest message size |
| `other` | burn-in logs, provider reports | hash only |

The summary is advisory; review reads the original file. The nonce proves when evidence was *bundled*, not generated,
so under ASSAY-TT-1 it must be produced inside the acceptance window. An evidence bundle alone never earns a Verified
DCB grade — that still takes the `nccl-allreduce` probe.

