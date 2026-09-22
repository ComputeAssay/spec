# ASSAY-1: The Deliverable Compute Specification

**Version 0.1 — Draft for Comment**

A standard for describing, verifying, and comparing compute capacity as a deliverable good.

---

## 0. Why this document exists

As of October 2026, compute becomes a financially traded commodity. CME/NYMEX will list H100 and B200 rental index futures; ICE has announced a competing suite on a rival index; a third venue has announced perpetuals on the same benchmarks.

Every one of these instruments is **cash-settled against a price index**. None of them delivers anything. A buyer holding a long position in a shortage receives money, not GPUs.

That is a functioning financial market sitting on top of a physical market that has no specification, no delivery standard, and no public record of what capacity actually exists.

Every mature commodity has both layers. Crude has Brent *and* cargo specs, delivery points, and quality differentials. Power has a forward curve *and* firm-vs-interruptible tiers, scheduling, and transmission rights. Compute has an index and nothing underneath it.

ASSAY-1 is the missing layer.

### 0.1 The core error this specification corrects

**A GPU-hour is not a fungible unit, and substitutability is not a property of a fleet.**

Substitutability is a *relation* between two fleets **with respect to a workload class**. Eight H100s on an oversubscribed shared Ethernet fabric and eight H100s inside an NVLink domain with a rail-optimized non-blocking InfiniBand plane are:

- **identical goods** for batch inference,
- **different goods** for large-model serving,
- **not comparable goods** for frontier-scale training.

The existing indexes count chips. This specification describes deliverable capacity.

### 0.2 What ASSAY-1 governs

1. **The Record** — the field set describing one fleet (§2).
2. **The Headline Metrics** — four derived numbers that summarize deliverability (§3).
3. **The Workload Classes** — the reference workloads substitutability is judged against (§4).
4. **The Substitutability Grade** — the A/B/C/F relation between two fleets for a class (§5).
5. **The Basis** — the published spread between index price and delivered effective price (§6).
6. **Assurance Tiers** — how much any given record should be trusted (§7).
7. **The Verification Harness** — the open benchmark that earns a Verified badge (§8).

---

## 1. Definitions

| Term | Definition |
|---|---|
| **Fleet** | A set of accelerators under one operator, at one site, sharing one scale-out fabric and one power feed, offered under one commercial construct. The atomic unit of this registry. |
| **Allocation** | A contiguous subset of a Fleet offered to a single tenant for a defined term. |
| **Scale-up domain** | The set of accelerators sharing a coherent high-bandwidth interconnect (NVLink/NVSwitch, Infinity Fabric). Load/store or near-load/store semantics. |
| **Scale-out fabric** | The packet-switched network joining scale-up domains (InfiniBand, RoCEv2, Slingshot, proprietary Ethernet). |
| **Reference Configuration** | The canonical fleet definition per silicon generation against which throughput ratios are normalized (§4.3). |
| **Index Price** | The published third-party benchmark rental rate a futures contract settles against. |
| **Delivered Effective Price** | What the buyer actually pays per unit of *work completed*, not per GPU-hour billed (§6.2). |
| **Basis** | Delivered Effective Price − Index Price. The quantity this registry exists to publish. |

---

## 2. The Record

Twelve field groups. Fields marked **[R]** are required for a record to be publishable; **[V]** are required for Verified assurance tier.

### A. Identity & Provenance

| Field | Type | Notes |
|---|---|---|
| `fleet_id` **[R]** | string | registry-assigned, immutable |
| `operator` **[R]** | string | Legal entity offering the capacity |
| `operator_class` **[R]** | enum | `hyperscaler` \| `neocloud` \| `colo_tenant` \| `enterprise_private` \| `broker_inventory` \| `sovereign` |
| `is_resale` **[R]** | bool | Capacity being resold rather than owned |
| `underlying_operator` | string | Required if `is_resale` is true |
| `resale_permitted` **[R]** | enum | `yes` \| `no` \| `unknown` — whether the underlying contract permits transfer. Gates §6 delivery eligibility. |
| `first_observed` / `last_verified` **[R]** | date | |

### B. Silicon

| Field | Type | Notes |
|---|---|---|
| `accelerator_model` **[R]** | string | Vendor part, e.g. `NVIDIA H100 SXM5`, `AMD MI300X` |
| `accelerator_count` **[R]** | int | Total in fleet |
| `accelerators_per_node` **[R]** | int | |
| `host_cpu` | string | |
| `host_cpu_cores_per_accelerator` | float | Matters for data-loader-bound workloads |
| `sriov_or_passthrough` | enum | `bare_metal` \| `passthrough` \| `vgpu` \| `container` — virtualization overhead |
| `mig_partitioned` | bool | Multi-instance partitioning changes the unit entirely |

### C. Memory & Capacity

| Field | Type | Notes |
|---|---|---|
| `hbm_gb_per_accelerator` **[R]** | int | |
| `hbm_bandwidth_tbps` | float | Vendor spec |
| `host_dram_gb_per_node` | int | |
| `aggregate_hbm_per_scale_up_domain_gb` **[R]** | int | *Derived.* The hard gate for large-model serving. |

### D. Scale-Up Domain

| Field | Type | Notes |
|---|---|---|
| `scale_up_interconnect` **[R]** | enum | `nvlink4` \| `nvlink5` \| `infinity_fabric` \| `pcie_only` \| `other` |
| `scale_up_domain_size` **[R]** | int | Accelerator count in one coherent domain. **The single most consequential field in this record.** 8 and 72 are different products. |
| `scale_up_bandwidth_gbps_per_accelerator` | int | Bidirectional |
| `nvswitch_topology` | enum | `full_fat` \| `partial` \| `none` |

### E. Scale-Out Fabric

*The field group no other catalog collects, and the reason this registry can exist.*

| Field | Type | Notes |
|---|---|---|
| `fabric_type` **[R]** | enum | `ib_ndr` \| `ib_xdr` \| `roce_v2` \| `spectrum_x` \| `slingshot` \| `proprietary` \| `tcp_only` |
| `nic_bandwidth_gbps_per_accelerator` **[R]** | int | Aggregate compute-plane bandwidth ÷ accelerator count |
| `nics_per_node` | int | |
| `topology` **[R]** | enum | `rail_optimized_fat_tree` \| `fat_tree` \| `dragonfly` \| `torus` \| `flat` \| `undisclosed` |
| `oversubscription_leaf_to_spine` **[R]** | string | e.g. `1:1`, `2:1`, `4:1` |
| `non_blocking_domain_size` **[R]** | int | Largest accelerator count at 1:1 bisection. See §3.2. |
| `adaptive_routing` | bool | |
| `congestion_control` | enum | `dcqcn` \| `pfc_only` \| `credit_based` \| `timely` \| `proprietary` \| `none` |
| `lossless_configured` | bool | |
| `in_network_reduction` | bool | SHARP or equivalent |
| `storage_plane_separate` **[R]** | bool | Shared storage and compute planes cause head-of-line collapse under checkpoint load |
| `tenant_isolation` **[R]** | enum | `dedicated_fabric` \| `partitioned` \| `shared_with_noisy_neighbors` |
| `measured_allreduce_busbw_gbps` **[V]** | float | See §8.1. The only honest number in this group. |

### F. Storage & Data Path

| Field | Type | Notes |
|---|---|---|
| `scratch_type` | enum | `local_nvme` \| `parallel_fs` \| `object_only` |
| `scratch_read_gbps_per_node` | float | |
| `checkpoint_write_gbps_aggregate` | float | Gates maximum viable run length |
| `dataset_ingress_cost_per_tb` | float | |
| `egress_cost_per_tb` **[R]** | float | A material and frequently hidden adder (§6.2) |

### G. Power & Thermal

| Field | Type | Notes |
|---|---|---|
| `cooling` **[R]** | enum | `air` \| `rear_door_hx` \| `direct_to_chip_liquid` \| `immersion` |
| `rack_power_density_kw` **[R]** | float | Gates which silicon can physically be hosted |
| `contracted_load_mw` **[R]** | float | |
| `power_cost_usd_per_mwh` | float | Where disclosed |
| `pue_trailing_12mo` | float | |

### H. Site & Grid

| Field | Type | Notes |
|---|---|---|
| `site_country` / `site_region` **[R]** | string | |
| `iso_rto_or_utility` **[R]** | string | e.g. ERCOT, PJM, SPP |
| `grid_status` **[R]** | enum | `energized` \| `interconnect_agreement_signed` \| `in_queue` \| `behind_the_meter` \| `hybrid` |
| `energization_date_actual_or_forecast` **[R]** | date | |
| `firm_mw` / `interruptible_mw` **[R]** | float | The split that determines §3.4 |
| `curtailment_notice_minutes` | int | |
| `curtailment_hours_trailing_12mo` | float | Actual, not contractual |
| `onsite_generation_mw` | float | |
| `network_latency_ms_to_major_metros` | map | For latency-bound serving |

### I. Commercial & Delivery Terms

| Field | Type | Notes |
|---|---|---|
| `contract_forms_offered` **[R]** | array | `on_demand` \| `spot_preemptible` \| `reserved_1yr` \| `reserved_3yr` \| `bare_metal_lease` |
| `list_price_usd_per_accelerator_hour` **[R]** | float | |
| `observed_transacted_price` **[V]** | float | Assurance Tier 2+ only (§7) |
| `minimum_allocation` **[R]** | int | |
| `provisioning_lead_time_days` **[R]** | int | Time from signature to usable capacity |
| `preemption_notice_seconds` | int | |
| `sla_availability_pct` | float | |
| `sla_remedy` | enum | `credits` \| `refund` \| `none` |
| `transferable` **[R]** | bool | Can the allocation be assigned to a third party? Gates secondary-market eligibility. |

### J. Reliability & Operations

| Field | Type | Notes |
|---|---|---|
| `node_mtbf_hours` | float | |
| `job_interruption_rate_per_1000_gpu_days` **[V]** | float | The number that decides whether multi-week training is possible |
| `hot_spare_pct` | float | |
| `healthcheck_automation` | bool | |
| `median_time_to_replace_failed_node_hours` | float | |

### K. Compliance & Sovereignty

| Field | Type | Notes |
|---|---|---|
| `export_control_regime` **[R]** | string | Governs who may lawfully take delivery |
| `data_residency_guarantees` | array | |
| `certifications` | array | SOC 2, ISO 27001, HIPAA, FedRAMP |
| `sanctioned_ownership_screen` **[R]** | enum | `clear` \| `flagged` \| `unscreened` |

### L. Attestation

| Field | Type | Notes |
|---|---|---|
| `assurance_tier` **[R]** | int | 0–3, see §7 |
| `attesting_party` | string | |
| `attestation_date` **[R]** | date | |
| `harness_run_id` **[V]** | string | Links to §8 output |
| `harness_version` **[V]** | string | |

---

## 3. The Headline Metrics

Four derived numbers. These are the registry's public vocabulary — the thing quoted in contracts and press.

### 3.1 CSD — Coherent Scale Domain
`scale_up_domain_size`, and its aggregate HBM.

**Why it matters:** a model whose weights plus KV cache exceed the CSD's aggregate HBM cannot be served without crossing into the scale-out fabric, which is one to two orders of magnitude slower. This is a *cliff*, not a slope. A fleet with CSD=8 and a fleet with CSD=72 are not the same product at any price.

### 3.2 NBD — Non-Blocking Domain
Largest accelerator count reachable at 1:1 bisection bandwidth.

**Why it matters:** a training job requesting 2,048 accelerators on a fleet with NBD=512 will spend its life in incast collapse. Advertised fleet size is meaningless above NBD.

### 3.3 DCB — Delivered Collective Bandwidth
Measured all-reduce bus bandwidth (GB/s) at 1 GiB message size, across the largest allocation the operator will sell, under production tenancy conditions. Measured, not derived from line rate.

**Why it matters:** this is the single number that separates spec-sheet fabric from working fabric. Line rate is what you bought. DCB is what you got. The ratio between them is the truth about oversubscription, congestion control, cabling quality, and noisy neighbors — all at once.

**DCB is the flagship metric of this registry.** Everything else is context for it.

### 3.4 PFI — Power Firmness Index
`firm_mw / contracted_load_mw`, penalized by trailing-12-month curtailment hours and short notice periods.

```
PFI = (firm_mw / contracted_load_mw)
      × (1 − min(curtailment_hours_12mo / 8760, 1))
      × notice_factor
```
where `notice_factor` = 1.0 if notice ≥ 60 min, 0.9 if ≥ 10 min, 0.7 if < 10 min or undisclosed.

**Why it matters:** as grid-flexibility contracts spread, "1,000 MW of capacity" increasingly means "600 MW firm and 400 MW the utility can take back." A buyer signing a multi-week training run against interruptible power is buying a different good than they think. PFI makes that visible and priceable.

---

## 4. Workload Classes

Substitutability is judged per class. Five classes, chosen because each has a distinct binding constraint.

| Class | Name | Binding constraint | East-west traffic |
|---|---|---|---|
| **W1** | Batch inference / embedding | HBM capacity per accelerator | None |
| **W2** | Interactive serving | Latency to user, CSD ≥ tensor-parallel width | Intra-node |
| **W3** | Large-model serving | Aggregate HBM within CSD | Intra-CSD, heavy |
| **W4** | Fine-tuning / mid-scale training | NBD, checkpoint bandwidth | Moderate |
| **W5** | Frontier-scale training | DCB, NBD, interruption rate, PFI | Extreme, sustained |

### 4.1 Class parameters

Each class declares the workload parameters a buyer supplies:

- **W1:** `model_weights_gb`, `throughput_target_tok_s`
- **W2:** `model_weights_gb`, `tp_width`, `ttft_target_ms`, `user_metros[]`
- **W3:** `model_weights_gb`, `kv_cache_gb_at_target_concurrency`, `tp_width`, `ep_width`
- **W4:** `accelerator_count_requested`, `checkpoint_gb`, `checkpoint_interval_min`, `run_duration_hours`
- **W5:** `accelerator_count_requested`, `run_duration_hours`, `collective_intensity` (`low`/`med`/`high`), `max_tolerable_restarts`

### 4.2 Reference Configurations

Throughput normalization requires a canonical fleet per silicon generation. Reference Configuration = the vendor's flagship reference architecture at 1:1 non-blocking, dedicated fabric, bare metal, liquid- or air-cooled per vendor spec, PFI = 1.0.

**Seed reference values — VERIFY AGAINST CURRENT VENDOR DATASHEETS BEFORE PUBLICATION:**

| Silicon | HBM/accel | CSD | Typical scale-out/accel | Approx. TDP/accel |
|---|---|---|---|---|
| H100 SXM5 | 80 GB HBM3 | 8 | 400 Gb/s | ~700 W |
| H200 SXM | 141 GB HBM3e | 8 | 400 Gb/s | ~700 W |
| B200 (HGX) | 192 GB HBM3e | 8 | 400–800 Gb/s | ~1,000 W |
| GB200 NVL72 | 192 GB HBM3e | 72 | 400–800 Gb/s | rack-level ~120 kW |
| MI300X | 192 GB HBM3 | 8 | 400 Gb/s | ~750 W |

These seed values exist so the grader can run. They are not authoritative. Publishing a wrong number once destroys a benchmark business permanently — treat the reference table as the highest-scrutiny artifact in the company.

### 4.3 Quality dimension (reserved)

Every workload class carries a `quality_basis` field, **null in all v0.x records**. It reserves the slot for the unit-of-work layer (quality-adjusted delivered intelligence — the kWh step) so that when quality adjustment is defined, historical series remain valid rather than being rebuilt. A benchmark that breaks its own history loses its standing permanently; this field exists so ASSAY-1 never has to.

---

## 5. The Substitutability Grade

For an ordered pair (fleet A → fleet B) and a workload class W with parameters P, the grade answers: *if my job runs on A, what happens when it runs on B?*

| Grade | Meaning | Throughput delta |
|---|---|---|
| **A** | Drop-in. No change to job configuration. | ≤ 5% |
| **B** | Runs after configuration change — parallelism strategy, batch size, sharding. | 5–25% |
| **C** | Runs after code, model, or architecture change, or with material loss. | 25–60% |
| **F** | Does not run, or loss exceeds 60%. | > 60% |

### 5.1 Hard gates (any one → F)

- `aggregate_hbm_per_scale_up_domain_gb` < required weights + KV cache **(W2, W3)**
- `non_blocking_domain_size` < `accelerator_count_requested` × 0.5 **(W5)**
- `export_control_regime` prohibits the buyer
- `grid_status` ≠ `energized` and required-by date < `energization_date`
- `resale_permitted` = `no` and `is_resale` = `true`
- `accelerator_model` architecture incompatible with a compiled/quantized artifact **(vendor-crossing: NVIDIA ↔ AMD is never grade A for W3–W5)**

### 5.2 Soft penalties (accumulate, then map to grade)

| Condition | Class weight |
|---|---|
| DCB ratio B/A < 0.9 | W4 ×1, W5 ×3 |
| `scale_up_domain_size` B < A | W2 ×1, W3 ×3, W5 ×1 |
| `oversubscription` worse than A | W4 ×1, W5 ×2 |
| `tenant_isolation` = `shared_with_noisy_neighbors` | W2 ×2, W4 ×1, W5 ×2 |
| `storage_plane_separate` = false, checkpoint-heavy | W4 ×2, W5 ×2 |
| `job_interruption_rate` B > A × 2 | W4 ×1, W5 ×3 |
| PFI B < 0.9 | W5 ×3, W4 ×1 |
| `sriov_or_passthrough` worse than `bare_metal` | W5 ×1 |
| Latency to required metro > target | W2 ×4 |
| HBM/accel B < A | W1 ×3, W3 ×2 |

Score 0 → A. 1–3 → B. 4–8 → C. >8 → F.

*These weights are a first calibration and should be refit against observed transaction data as soon as there is any. Publishing them openly and revising them publicly is a feature, not a weakness — it is how a benchmark earns standing.*

---

## 6. The Basis

### 6.1 The definition

```
Basis(fleet, class, tenor) = Delivered Effective Price − Index Price
```

Published per silicon generation, per region, per workload class, per tenor. Example output:

> **H100 · US-West · W5 · Nov-26: basis +$0.94/accel-hr**

The futures contract settles on the index. The buyer's real cost is index + basis. Nobody publishes the basis. That gap is the entire commercial opening.

### 6.2 Delivered Effective Price

```
DEP = (contract_price_per_accel_hour / throughput_ratio_vs_reference)
      + egress_adder
      + storage_adder
      + idle_on_failure_adder
      + curtailment_risk_premium
      + provisioning_carry
```

- `throughput_ratio_vs_reference` — from §5 grading against the Reference Configuration. A fleet delivering 70% of reference throughput at 90% of reference price has a *higher* effective price.
- `idle_on_failure_adder` = `job_interruption_rate` × mean restart cost × run length. On a long W5 run this can exceed 15% of headline price.
- `curtailment_risk_premium` = (1 − PFI) × expected value of lost work.
- `provisioning_carry` = cost of capital over `provisioning_lead_time_days`.

### 6.3 Why this is defensible

The index publishers are financial data firms. Computing DEP requires knowing what a fabric actually delivers, what a checkpoint collapse costs, and what curtailment does to a run. That is a networking and systems problem wearing a finance hat. The people building the financial layer would have to hire the expertise; the registry has to hire the finance, which is far easier to buy.

---

## 7. Assurance Tiers

Every record carries a tier. Never publish a number without its tier. This is the honest answer to "operators will lie."

| Tier | Source | Confidence |
|---|---|---|
| **0** | Public rate card / marketing collateral, machine-collected | Low. Price directionally useful, fabric fields near-worthless. |
| **1** | Operator self-attestation via structured submission | Medium. Puts a name against a claim. Reputationally costly to falsify. |
| **2** | Buyer- or broker-reported transaction, ≥2 independent sources | High for price and terms. |
| **3** | **Assay Verified** — harness executed, output signed, within 90 days | High for everything, including DCB. |

Records decay: Tier 3 → Tier 1 after 90 days without re-run. Tier 2 → Tier 0 after 180 days. Publish decay openly.

---

## 8. The Verification Harness

An open-source, MIT-licensed benchmark suite an operator runs on their own fleet. Output is signed and submitted; the operator earns a **Assay Verified** badge.

**This solves the cold-start problem.** The registry does not need access to clusters it does not own. Operators run the harness because verified fleets sell faster and at better terms — the same reason merchants sought Underwriters Laboratories listing and vendors publish SPEC results. Verification is a supplier-pull, not a buyer-push.

### 8.1 Required probes

| Probe | Measures | Output field |
|---|---|---|
| `nccl-allreduce` | busbw at 1 GiB across max sellable allocation | `measured_allreduce_busbw_gbps` (DCB) |
| `nccl-alltoall` | MoE / expert-parallel viability | `measured_alltoall_busbw_gbps` |
| `csd-probe` | Actual coherent domain size and intra-domain bandwidth | Validates §2.D claims |
| `checkpoint-burst` | Sustained aggregate write during simulated checkpoint | `checkpoint_write_gbps_aggregate` |
| `serving-latency` | TTFT and inter-token latency at fixed concurrency | W2 grading input |
| `soak-72h` | Node failures and job restarts over 72 h under load | `job_interruption_rate` |
| `power-telemetry` | Rack draw during sustained load; correlates to curtailment exposure | Validates §2.G |

### 8.2 Anti-gaming rules

- Probes run under production tenancy, not on a drained cluster. The harness records concurrent tenant count.
- Allocation size must equal the maximum the operator will actually sell — no benchmarking a golden 64-node slice of a fleet sold in 512-node blocks.
- Results signed with a run nonce issued by the registry; results older than the nonce window are rejected.
- Refusal to publish a completed run is itself recorded. An operator who runs and withholds is flagged.

### 8.3 The measured grade and the assay certificate

A **measured grade** is a §5 substitutability grade (A/B/C/F) computed from *measured* metrics — DCB (§3.3) and its siblings — for a stated workload class, not from disclosures. It is Tier 3 (§7). Only a measured grade earns a certificate; a disclosure grade (Tier 0–1) never does. A grade is always with respect to a workload class; there is no context-free measured grade (§0.1).

**Two source classes, both measured, stated on the certificate.** Independence is not binary and is not hidden:

- `first-party-assay` — the registry rented the fleet and ran the harness itself.
- `operator-submitted` — the operator ran the open harness on its own metal and signed the output; the registry verified the signature, the run nonce, and the §8.2 disclosures, **not the metal.**

Both yield a real measured number (unlike a disclosure grade); they differ in independence, and the difference is a required field on the certificate, not a footnote. Operator-submitted is the supplier-pull default (§8): it needs no capital, and the operator publishes its *own* fleet, which sidesteps third-party benchmark-publication restrictions.

**The assay certificate** (`assay_certificate.schema.json`) is the machine-readable, signed attestation of a measured grade for one fleet and one workload class. It carries: the primary measured metric and its delivered-over-line-rate ratio; the §8.2 tenancy disclosures (concurrent tenants, allocation, whether the allocation equals the maximum sellable); the measurement window; the **decay/expiry** term (§7 — a measured grade expires 90 days after its window without re-run, so staleness is a *defined event*, not a silent condition); the run nonce, harness version, and probe; and a **ledger inclusion proof.**

**The ledger.** Every measurement lands in a public, append-only record of GPG-signed commits, each anchored to a trusted timestamp (OpenTimestamps → Bitcoin). A signed git history *is* a hash-chained transparency log; the anchor closes the trusted-time gap. The result is verifiable **without trusting the registry** — signature, commit chain, and Bitcoin anchor are all independently checkable — and it is un-backdatable: a history begun today is provably ahead of one begun tomorrow, forever. This is the "time-accumulated state" the whole standard rests on, and it costs nothing to run. (Implementation: the working note in the project's `measurement-ledger.md`.)

**What the certificate attests, and what it does not.** It attests *what was measured, under which disclosed conditions, when, signed by whom* — a true and checkable fact. It does **not**, for operator-submitted runs, assert the metal was not gamed; that is the province of §8.2 and of repeated sampling (§10.2), and the harder anti-gaming machinery (attestation, seeded non-recognizable workloads) is intentionally staged for when a grade moves contract money. n=1 honesty holds: a certificate attests its window, never the fleet in general.

**Purpose.** The certificate exists to be **referenced by a contract** — a credit covenant, an EFP delivery term, a procurement warranty — by its `certificate_id` and inclusion proof, rather than a marketing page. That is the standard → reference → settlement path in §9 made concrete: the settlement standard a market cites is built from an object like this one, verifiable and neutral. A price index can be cloned; a certificate that a counterparty's executed agreement points to cannot.

---

## 9. Publication

| Product | Cadence | Access |
|---|---|---|
| **Delivered Compute Report** | Weekly | Free. Headline basis by silicon/region/class, one fleet teardown, commentary. The distribution engine. |
| **Registry API** | Continuous | Paid. Full records, grades, historical basis series. |
| **Basis Benchmarks** | Daily | Paid. The reference series contracts cite. |
| **Verified Badge Program** | On demand | Free to operator; the flywheel's fuel. |

The sequence is deliberate and is the same one every commodity price reporting agency ran: **publish free and be right → become the reference → become the settlement standard → become the venue.** Skipping steps kills you; there is no shortcut from newsletter to exchange.

---

## 10. Known weaknesses of this specification

Stated plainly, because a spec that hides its soft spots does not get adopted.

1. **The soft-penalty weights in §5.2 are invented.** They are an engineer's prior, not a fit to data. Until there are several hundred observed transactions, grades B and C are opinion.
2. **DCB is gameable at the margin** despite §8.2. A determined operator can schedule the run during a quiet window. Repeated sampling is the only real defense and it costs the operator goodwill.
3. **Tier 0 is most of the world — but for basis, it is the *right* part of the world.** Hyperscaler and enterprise contracts are under NDA, so this registry under-represents hyperscaler *volume*. For measuring **global capacity**, that is a genuine gap. For measuring **basis against the listed contracts, it is not** — because the CME × Silicon Data H100 and B200 compute futures (listing 2026-10-05) settle on the *neocloud, non-hyperscaler on-demand* rental index (tickers SDH100RT / SDB200RT); Silicon Data publishes hyperscaler pricing as a **separate reading the contracts do not reference**. The relevant universe for basis is the settlement constituent set — which is exactly the transparent neocloud population this registry covers densely. Coverage is aimed *at* the settlement segment, not away from it. The honest residual gap is enterprise-private and colocation capacity, which trades on neither the index nor this registry.
4. **`resale_permitted` may be `no` almost everywhere.** If the major suppliers contractually forbid transfer, the deliverable secondary market in §6 is confined to neoclouds and brokers.
5. **The whole thesis is levered to scarcity.** If accelerator supply loosens and prices flatten, hedging demand thins, basis compresses toward zero, and this becomes a small trade-press business.
6. **Silicon generations churn faster than specifications.** Every 12–18 months the Reference Configuration table needs rebuilding, and each rebuild breaks historical series continuity.
7. **The index publishers can hire fabric engineers.** The moat is a head start plus a standard that gets adopted before they move. It is a race, not a wall.

---

*ASSAY-1 v0.1. Draft for comment. Nothing in this document is investment advice or a representation about any named company or product.*

**Changelog**
- v0.1.2 (2026-09-20) — rewrote §10.3: the neocloud skew is correct targeting, not a weakness, because the CME × Silicon Data settlement index (SDH100RT / SDB200RT) is itself neocloud/non-hyperscaler on-demand. Residual gap narrowed to enterprise-private + colocation.
- v0.1.1 (2026-09-10, migrated to repo) — added §4.3 reserved quality dimension, per the design requirement that workload classes survive the move from delivered capacity to delivered work without breaking historical series.
- v0.1 (2026-09) — initial draft: record, headline metrics, workload classes, substitutability grade, basis, assurance tiers, harness.
