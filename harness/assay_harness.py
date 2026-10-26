#!/usr/bin/env python3
# Assay Verification Harness — v0.2.0. MIT license. https://computeassay.com/harness.html
# Probe: nccl-allreduce (ASSAY-1 §8.1). Wraps NVIDIA nccl-tests' all_reduce_perf, parses bus
# bandwidth, captures environment + §8.2 disclosures, binds the run to a public randomness-beacon nonce,
# and emits self-hashed (optionally GPG-signed) JSON for registry ingestion. Stdlib only.
#
#   ./assay_harness.py --self-test                       # parser check, no GPUs needed
#   ./assay_harness.py --gpus 8 --fetch-nonce            # single node
#   ./assay_harness.py --launcher "mpirun -np 64 -hostfile hosts" --gpus-per-node 8 \
#       --fetch-nonce --tenants 3 --allocation "64 GPU / 8 node block" --line-rate-gbps 3200
#   ./assay_harness.py --from-output run.log --nonce <N>  # you ran all_reduce_perf yourself
#   ./assay_harness.py --evidence-only --evidence nvidia-cre:cre-report.json \
#       --evidence clustermax-audit:audit.json --fetch-nonce   # bundle third-party acceptance evidence
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.request

HARNESS_VERSION = "0.2.0"
SPEC = "ASSAY-1 v0.1 §8"
NONCE_URL = "https://computeassay.com/api/nonce"

# Synthetic all_reduce_perf output in the exact nccl-tests table format — used only by --self-test.
SAMPLE = """#
#                                                              out-of-place                       in-place
#       size         count      type   redop    root     time   algbw   busbw #wrong     time   algbw   busbw #wrong
#        (B)    (elements)                               (us)  (GB/s)  (GB/s)            (us)  (GB/s)  (GB/s)
    16777216       4194304     float     sum      -1    194.3   86.35  151.11      0    193.8   86.57  151.50      0
    33554432       8388608     float     sum      -1    352.9   95.08  166.39      0    351.7   95.41  166.97      0
    67108864      16777216     float     sum      -1    669.4  100.25  175.44      0    668.1  100.45  175.79      0
   134217728      33554432     float     sum      -1   1291.6  103.92  181.86      0   1290.2  104.03  182.05      0
   268435456      67108864     float     sum      -1   2531.0  106.06  185.60      0   2529.4  106.13  185.72      0
   536870912     134217728     float     sum      -1   5008.7  107.19  187.58      0   5006.9  107.23  187.65      0
  1073741824     268435456     float     sum      -1   9961.2  107.79  188.64      0   9958.5  107.82  188.69      0
# Out of bounds values : 0 OK
# Avg bus bandwidth    : 176.69
"""


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
    code, out, _ = sh("ibstat -l 2>/dev/null || ls /sys/class/infiniband 2>/dev/null", timeout=30)
    if code == 0 and out:
        env["ib_devices"] = out.split()
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


def fetch_nonce():
    try:
        with urllib.request.urlopen(NONCE_URL, timeout=20) as r:
            body = json.loads(r.read().decode())
        return body["nonce"], body
    except Exception as e:
        sys.exit(f"FATAL: could not fetch a run nonce from {NONCE_URL}: {e}\n"
                 f"Get one in a browser at https://computeassay.com/harness.html#nonce and pass --nonce.")


def self_test():
    curve = parse_busbw(SAMPLE)
    assert len(curve) == 7, f"expected 7 rows, parsed {len(curve)}"
    assert curve[1 << 30] == 188.64, curve[1 << 30]
    assert curve[16 << 20] == 151.11
    print(f"self-test ok · parsed {len(curve)} rows · busbw @1GiB {curve[1 << 30]} GB/s "
          f"= {curve[1 << 30] * 8:.0f} Gbps", file=sys.stderr)


EVIDENCE_TYPES = {
    "clustermax-audit": "SemiAnalysis ClusterMAX audit output (their free, open audit tool)",
    "nvidia-cre": "NVIDIA Cluster Readiness Engine certification report (nvcrectl)",
    "nccl-log": "raw nccl-tests output (all_reduce_perf / all_to_all_perf)",
    "other": "any other acceptance artifact (burn-in log, provider report)",
}
PASS = {"pass", "passed", "ok", "success", "succeeded", "healthy", "true"}
FAIL = {"fail", "failed", "error", "unhealthy", "false", "thresholdviolation", "hardwarefailuredetected", "workloadfailed"}


def _count_status(node, acc):
    """Heuristic: count pass/fail values under status-like keys anywhere in a JSON document."""
    if isinstance(node, dict):
        for k, v in node.items():
            if isinstance(v, (str, bool)) and k.lower() in ("status", "result", "outcome", "verdict", "state", "reason", "passed", "ok"):
                t = str(v).lower().replace(" ", "")
                if t in PASS:
                    acc["pass"] += 1
                elif t in FAIL:
                    acc["fail"] += 1
            else:
                _count_status(v, acc)
    elif isinstance(node, list):
        for v in node:
            _count_status(v, acc)
    return acc


def attach_evidence(spec):
    """--evidence TYPE:PATH -> hashed, summarised record. The original file is the evidence; the summary is advisory."""
    if ":" not in spec:
        sys.exit(f"FATAL: --evidence expects TYPE:PATH (types: {', '.join(EVIDENCE_TYPES)})")
    kind, path = spec.split(":", 1)
    if kind not in EVIDENCE_TYPES:
        sys.exit(f"FATAL: unknown evidence type {kind!r} (types: {', '.join(EVIDENCE_TYPES)})")
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except OSError as e:
        sys.exit(f"FATAL: cannot read evidence {path}: {e}")
    rec = {"type": kind, "describes": EVIDENCE_TYPES[kind], "filename": path.rsplit("/", 1)[-1],
           "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "summary": None}
    text = raw.decode("utf-8", errors="replace")
    if kind == "nccl-log":
        curve = parse_busbw(text)
        if curve:
            top = max(curve)
            rec["summary"] = {"rows_parsed": len(curve), "busbw_GBps_at_largest": curve[top], "largest_bytes": top,
                              "busbw_gbps_at_largest": round(curve[top] * 8, 1)}
    else:
        try:
            doc = json.loads(text)
            counts = _count_status(doc, {"pass": 0, "fail": 0})
            rec["summary"] = {"format": "json", "top_level_keys": list(doc)[:20] if isinstance(doc, dict) else None,
                              "status_values_pass": counts["pass"], "status_values_fail": counts["fail"]}
        except ValueError:
            rec["summary"] = {"format": "text", "lines": text.count("\n") + 1,
                              "lines_mentioning_fail": sum(1 for ln in text.splitlines() if "fail" in ln.lower())}
    return rec


def main():
    ap = argparse.ArgumentParser(description=f"Assay harness {HARNESS_VERSION} — nccl-allreduce probe")
    ap.add_argument("--binary", default="all_reduce_perf", help="path to nccl-tests all_reduce_perf")
    ap.add_argument("--launcher", default="", help='multi-node launcher prefix, e.g. "mpirun -np 64 -hostfile hosts"')
    ap.add_argument("--gpus", type=int, default=0, help="GPUs for single-node run (-g)")
    ap.add_argument("--gpus-per-node", type=int, default=0, help="GPUs per process when using --launcher")
    ap.add_argument("--nonce", default="", help="run nonce from /api/nonce (without one: self-reported, not Verified)")
    ap.add_argument("--fetch-nonce", action="store_true", help=f"fetch a fresh nonce from {NONCE_URL}")
    ap.add_argument("--tenants", type=int, default=None, help="concurrent tenants on the fabric during the run (§8.2)")
    ap.add_argument("--allocation", default="", help="allocation description, e.g. '512 GPU / 64 node block' (§8.2)")
    ap.add_argument("--max-sellable", action="store_true", help="declare: this allocation equals the largest unit you sell (§8.2)")
    ap.add_argument("--line-rate-gbps", type=float, default=None, help="vendor-published per-GPU scale-out line rate, for delivered/line-rate")
    ap.add_argument("--from-output", default="", help="parse an existing all_reduce_perf log instead of running")
    ap.add_argument("--sign", default="", help="GPG key id — writes a detached .asc next to the output")
    ap.add_argument("--out", default="", help="output path (default assay-probe-<ts>.json)")
    ap.add_argument("--self-test", action="store_true", help="check the parser against a bundled sample and exit")
    ap.add_argument("--evidence", action="append", default=[], metavar="TYPE:PATH",
                    help="attach acceptance evidence produced by another tool, hashed into the result. Repeatable. "
                         "TYPE is one of: " + ", ".join(EVIDENCE_TYPES))
    ap.add_argument("--evidence-only", action="store_true",
                    help="skip the probe and emit a nonce-bound evidence bundle from --evidence files alone")
    args = ap.parse_args()

    if args.self_test:
        return self_test()

    nonce_meta = None
    if args.fetch_nonce:
        args.nonce, nonce_meta = fetch_nonce()
        print(f"nonce issued {nonce_meta.get('issued_utc')} · expires {nonce_meta.get('expires_utc')}", file=sys.stderr)

    evidence = [attach_evidence(e) for e in args.evidence]
    if args.evidence_only:
        if not evidence:
            sys.exit("FATAL: --evidence-only needs at least one --evidence TYPE:PATH")
        started = time.time()
        result = {
            "probe": "evidence-bundle", "spec": SPEC, "harness_version": HARNESS_VERSION,
            "run_nonce": args.nonce or None, "nonce_issued_utc": (nonce_meta or {}).get("issued_utc"),
            "verified_eligible": False,
            "bundled_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
            "evidence": evidence,
            "note": "Third-party acceptance evidence, hashed and bound to the run nonce. The nonce proves when the bundle "
                    "was made, not when the evidence was generated; registry review reads the original files. "
                    "A Verified DCB grade still requires the nccl-allreduce probe.",
            "disclosures": {"allocation": args.allocation or "NOT DECLARED", "allocation_is_max_sellable": bool(args.max_sellable),
                            "concurrent_tenants": args.tenants},
        }
        body = json.dumps(result, indent=1, sort_keys=True)
        result["sha256"] = hashlib.sha256(body.encode()).hexdigest()
        out_path = args.out or f"assay-evidence-{time.strftime('%Y%m%d-%H%M%S')}.json"
        with open(out_path, "w") as f:
            json.dump(result, f, indent=1, sort_keys=True)
        for e in evidence:
            print(f"evidence {e['type']}: {e['filename']} sha256 {e['sha256'][:16]}… summary {e['summary']}", file=sys.stderr)
        print(f"wrote {out_path}", file=sys.stderr)
        if args.sign:
            code, _, err = sh(f"gpg --local-user {args.sign} --armor --detach-sign {out_path}", timeout=60)
            print(f"signed: {out_path}.asc" if code == 0 else f"WARN: gpg failed: {err}", file=sys.stderr)
        return

    started = time.time()
    if args.from_output:
        with open(args.from_output) as f:
            out = f.read()
        cmd = f"(parsed from {args.from_output})"
    else:
        if not args.launcher and not shutil.which(args.binary):
            sys.exit(f"FATAL: {args.binary} not found. Build https://github.com/NVIDIA/nccl-tests or pass --binary.")
        g = f" -g {args.gpus}" if args.gpus and not args.launcher else ""
        per_node = f" -g {args.gpus_per_node}" if args.gpus_per_node and args.launcher else ""
        cmd = f"{args.launcher} {args.binary} -b 16M -e 1G -f 2{g}{per_node}".strip()
        print(f"assay-harness {HARNESS_VERSION} · probe nccl-allreduce\n$ {cmd}", file=sys.stderr)
        code, out, err = sh(cmd, timeout=3600)
        if code != 0:
            sys.exit(f"FATAL: probe failed ({code}).\n{err or out}")

    curve = parse_busbw(out)
    if not curve:
        sys.exit("FATAL: could not parse busbw from all_reduce_perf output — send the raw output to the registry instead.")

    one_gib = curve.get(1 << 30) or curve[max(curve)]
    gbps = round(one_gib * 8, 1)  # GB/s -> Gbps
    result = {
        "probe": "nccl-allreduce",
        "spec": SPEC,
        "harness_version": HARNESS_VERSION,
        "run_nonce": args.nonce or None,
        "nonce_issued_utc": (nonce_meta or {}).get("issued_utc"),
        "verified_eligible": bool(args.nonce),
        "started_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(started)),
        "duration_s": round(time.time() - started, 1),
        "command": cmd,
        "measured_allreduce_busbw_gbps": gbps,
        "busbw_at_bytes": (1 << 30) if (1 << 30) in curve else max(curve),
        "busbw_curve_GBps": {str(k): v for k, v in sorted(curve.items())},
        "line_rate_reference_gbps": args.line_rate_gbps,
        "delivered_over_line_rate": round(gbps / args.line_rate_gbps, 3) if args.line_rate_gbps else None,
        "disclosures": {  # §8.2 — recorded, cross-checked at ingestion
            "allocation": args.allocation or "NOT DECLARED",
            "allocation_is_max_sellable": bool(args.max_sellable),
            "concurrent_tenants": args.tenants,
        },
        "evidence": evidence,
        "environment": capture_env() if not args.from_output else {"harness_version": HARNESS_VERSION, "spec": SPEC, "note": "parsed from log; environment not captured"},
        "raw_output": out,
    }
    body = json.dumps(result, indent=1, sort_keys=True)
    result["sha256"] = hashlib.sha256(body.encode()).hexdigest()

    out_path = args.out or f"assay-probe-{time.strftime('%Y%m%d-%H%M%S')}.json"
    with open(out_path, "w") as f:
        json.dump(result, f, indent=1, sort_keys=True)
    ratio = f" · {result['delivered_over_line_rate']:.0%} of line rate" if result["delivered_over_line_rate"] else ""
    print(f"busbw @{result['busbw_at_bytes'] >> 20} MiB: {one_gib:.1f} GB/s ({gbps:.0f} Gbps){ratio} · wrote {out_path}", file=sys.stderr)

    if args.sign:
        code, _, err = sh(f"gpg --local-user {args.sign} --armor --detach-sign {out_path}", timeout=60)
        print(f"signed: {out_path}.asc" if code == 0 else f"WARN: gpg failed: {err}", file=sys.stderr)
    if not args.nonce:
        print("NOTE: no nonce — this run ingests as self-reported, not Verified. Re-run with --fetch-nonce.", file=sys.stderr)
    else:
        print("Next: send the JSON (and .asc) to the registry — see https://computeassay.com/harness.html#submit", file=sys.stderr)


if __name__ == "__main__":
    main()
