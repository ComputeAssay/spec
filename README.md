# ASSAY-1 — The Deliverable Compute Specification

**A standard for describing, verifying, and comparing compute capacity as a deliverable good.**

Compute is being financialized: multiple exchanges are listing cash-settled GPU price futures. All of them price compute; none of them can deliver it, because the deliverable has never been defined. A GPU-hour is not a fungible unit — eight H100s on a shared Ethernet fabric and eight H100s in an NVLink domain with non-blocking InfiniBand are different goods for training and identical goods for batch inference. Whether one cluster can substitute for another is a networking-topology question the financial layer cannot answer.

ASSAY-1 is the missing layer: the record format, headline metrics, workload classes, substitutability grades, and verification harness that turn "compute" from a price you can hedge into capacity you can take delivery of. An **assay** is the test that determines a commodity's grade and purity. This is that test, for compute.

| File | Contents |
|---|---|
| [`ASSAY-1.md`](ASSAY-1.md) | The specification: 12-field-group record, CSD/NBD/DCB/PFI headline metrics, workload classes W1–W5, A/B/C/F substitutability grades, the basis calculation, assurance tiers, verification harness |
| [`assay_record.schema.json`](assay_record.schema.json) | Machine-readable record schema (JSON Schema) |

## Status

**v0.1 — draft for comment.** The spec states its own known weaknesses in §10; corrections and challenges are welcome as issues. The soft-penalty weights in §5.2 are a first calibration and will be refit publicly as transaction data accumulates — a benchmark earns standing by revising in the open.

## The publication

The **Delivered Compute Report** — a weekly survey of real GPU capacity graded against this spec, with every row sourced — is published by Compute Assay. Subscription link coming with issue #1.

## Versioning

RFC-style: field additions bump the minor version; grade-threshold changes are never applied retroactively — a graded snapshot is immutable. Changelog at the bottom of the spec.

## License

Specification text and schema: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite it, build on it, implement it — attribution to Compute Assay.
