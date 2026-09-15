#!/usr/bin/env python3
# Assay Verification Harness — v0.1.0-alpha. MIT license.
# Probe: nccl-allreduce (ASSAY-1 §8.1). Wraps NVIDIA nccl-tests' all_reduce_perf, parses
# bus bandwidth, captures environment + §8.2 disclosures, emits self-hashed (optionally
# GPG-signed) JSON for registry ingestion. Stdlib only.
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time

HARNESS_VERSION = "0.1.0-alpha"
SPEC = "ASSAY-1 v0.1 §8"


def sh(cmd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return r.returncode, r.stdout.strip(), r.stderr.strip()
    except Exception as e:  # missing binary, timeout — recorded, not fatal
        return -1, "", str(e)


def capture_env():
    env = {"harness_version": HARNESS_VERSION, "spec": SPEC}
    code, out, _ = sh("nvidia-smi --query-gpu=name,driver_version,memory.total --format=csv,noheader")
    if code == 0 and out:
        rows = [r.split(", ") for r in out.splitlines()]
        env["gpu_name"] = rows[0][0]
        env["gpu_count_visible"] = len(rows)
        env["driver_version"] = rows[0][1]
        env["vram_total"] = rows[0][2]
    code, out, _ = sh("nvidia-smi topo -m", timeout=60)
    if code == 0:
        env["topology_matrix"] = out
    code, out, _ = sh("hostname")
    env["hostname"] = out if code == 0 else None
    return env


# all_reduce_perf table: size(B) count type redop root time algbw busbw #wrong (oop) ...
ROW = re.compile(r"^\s*(\d+)\s+\d+\s+\S+\s+\S+\s+[-\d]+\s+[\d.]+\s+([\d.]+)\s+([\d.]+)")


def parse_busbw(text):
    """Return {size_bytes: busbw_GBps} for out-of-place rows of all_reduce_perf output."""
    curve = {}
    for line in text.splitlines():
        m = ROW.match(line)
        if m:
            curve[int(m.group(1))] = float(m.group(3))
    return curve


def main():
    ap = argparse.ArgumentParser(description="Assay harness v0.1 — nccl-allreduce probe")
    ap.add_argument("--binary", default="all_reduce_perf", help="path to nccl-tests all_reduce_perf")
    ap.add_argument("--launcher", default="", help='multi-node launcher prefix, e.g. "mpirun -np 64 -hostfile hosts"')
    ap.add_argument("--gpus", type=int, default=0, help="GPUs for single-node run (-g)")
    ap.add_argument("--gpus-per-node", type=int, default=0, help="GPUs per node when using --launcher")
    ap.add_argument("--nonce", default="", help="registry-issued run nonce (without it: self-reported, not Verified)")
    ap.add_argument("--tenants", type=int, default=None, help="concurrent tenants on the fabric during the run (§8.2)")
    ap.add_argument("--allocation", default="", help="allocation description, e.g. '512 GPU / 64 node block' (§8.2)")
    ap.add_argument("--sign", default="", help="GPG key id — writes a detached .asc next to the output")
    ap.add_argument("--out", default="", help="output path (default assay-probe-<ts>.json)")
    args = ap.parse_args()

    if not args.launcher and not shutil.which(args.binary):
        sys.exit(f"FATAL: {args.binary} not found. Build https://github.com/NVIDIA/nccl-tests or pass --binary.")

    g = f" -g {args.gpus}" if args.gpus and not args.launcher else ""
    per_node = f" -g {args.gpus_per_node}" if args.gpus_per_node and args.launcher else ""
    cmd = f"{args.launcher} {args.binary} -b 16M -e 1G -f 2{g}{per_node}".strip()

    print(f"assay-harness {HARNESS_VERSION} · probe nccl-allreduce\n$ {cmd}", file=sys.stderr)
    started = time.time()
    code, out, err = sh(cmd, timeout=3600)
    if code != 0:
        sys.exit(f"FATAL: probe failed ({code}).\n{err or out}")
    curve = parse_busbw(out)
    if not curve:
        sys.exit("FATAL: could not parse busbw from all_reduce_perf output — pass the raw output to the registry instead.")

    one_gib = curve.get(1 << 30) or curve[max(curve)]
    result = {
        "probe": "nccl-allreduce",
        "spec": SPEC,
        "run_nonce": args.nonce or None,
        "verified_eligible": bool(args.nonce),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "duration_s": round(time.time() - started, 1),
        "command": cmd,
        "measured_allreduce_busbw_gbps": round(one_gib * 8, 1),  # GB/s -> Gbps
        "busbw_curve_GBps": {str(k): v for k, v in sorted(curve.items())},
        "disclosures": {  # §8.2 — recorded, cross-checked at ingestion
            "allocation": args.allocation or "NOT DECLARED",
            "concurrent_tenants": args.tenants,
        },
        "environment": capture_env(),
        "raw_output": out,
    }
    body = json.dumps(result, indent=1, sort_keys=True)
    result["sha256"] = hashlib.sha256(body.encode()).hexdigest()

    out_path = args.out or f"assay-probe-{time.strftime('%Y%m%d-%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    print(f"busbw @1GiB: {one_gib:.1f} GB/s ({one_gib * 8:.0f} Gbps) · wrote {out_path}", file=sys.stderr)

    if args.sign:
        code, _, err = sh(f"gpg --local-user {args.sign} --armor --detach-sign {out_path}", timeout=60)
        print(f"signed: {out_path}.asc" if code == 0 else f"WARN: gpg failed: {err}", file=sys.stderr)
    if not args.nonce:
        print("NOTE: no --nonce — this run ingests as self-reported, not Verified. Get one: reply 'harness' to any report issue.", file=sys.stderr)


if __name__ == "__main__":
    main()
