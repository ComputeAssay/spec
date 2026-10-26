#!/usr/bin/env python3
# Verify the Compute Assay forecast ledger (https://computeassay.com/data/forecasts.jsonl). MIT license.
# Each line is a JSON record whose `hash` is sha256 of the record without `hash`, serialized exactly as
# JavaScript's JSON.stringify would (no spaces, insertion key order), and whose `prev_hash` is the
# previous line's hash (genesis = 64 zeros). Any edit, deletion, insertion or reorder breaks the chain.
#   python3 verify_ledger.py forecasts.jsonl
import hashlib
import json
import sys
from collections import OrderedDict


def main(path):
    prev = "0" * 64
    n = 0
    with open(path) as f:
        for n, line in enumerate((l for l in f if l.strip()), 1):
            rec = json.loads(line, object_pairs_hook=OrderedDict)
            h = rec.pop("hash")
            if rec.get("prev_hash") != prev:
                sys.exit(f"BROKEN at line {n}: prev_hash does not match line {n - 1}")
            body = json.dumps(rec, separators=(",", ":"), ensure_ascii=False)
            if hashlib.sha256(body.encode()).hexdigest() != h:
                sys.exit(f"BROKEN at line {n}: hash does not match content")
            prev = h
    print(f"ok · {n} records · head {prev}")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "forecasts.jsonl")
