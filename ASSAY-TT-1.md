# ASSAY-TT-1 — Standard compute tranche and transfer term sheet

*Draft for comment · v0.1 · 2026-10-26*

## Committed compute needs an exit valve

The largest buyers of AI compute have signed hundreds of billions of dollars of multi-year, largely non-cancelable capacity, much of it delivering between 2026 and 2031. Suppliers sign tranches whose delivery dates depend on power and construction they do not fully control. Lenders finance both sides. What none of them can do is move a commitment: most cloud and capacity contracts restrict assignment, there is no standard unit to transfer, and no shared test of whether the thing being transferred was delivered. ASSAY-TT-1 is the missing paperwork: a standard tranche, keyed to ASSAY-1 grades, and a pre-approvable sublease and assignment addendum.

> **What this is.** A term sheet — the commercial skeleton a lawyer turns into contract language — published so providers, buyers and lenders converge on one form instead of negotiating transferability bilaterally every time. It is not legal advice and not a contract. Bracketed items are open for comment. Providers willing to pre-approve the addendum for their capacity: reply to any issue of the [report](https://computeassay.substack.com) with "transfer".

## Part 1 — The standard tranche

A tranche is the smallest unit of committed compute that can be delivered, accepted, graded and transferred on its own. Every field is either an ASSAY-1 record field or a contract term that references one.

| Term | Proposal |
|---|---|
| tranche_id | Registry-assigned, immutable. One tranche, one delivery date. |
| Site | The ASSAY-1 `site_id` with its Site & Grid fields (§2 H): `iso_rto_or_utility`, `grid_status`, `energization_date_actual_or_forecast`, `firm_mw` / `interruptible_mw`. The tranche inherits the site's [delivery-risk grade](https://computeassay.com/delivery.html) until accepted. |
| Quantity | Accelerator model and count, contiguous allocation size (the largest block sold as one unit), contracted MW. |
| Delivery window | Target handover date and a [60]-day grace window. Late beyond the window: the buyer may terminate that tranche alone, without liability, and the tranche's prepayments are refunded [pro rata]. |
| Acceptance test | Within [10] days of handover the buyer may run the [ASSAY harness](https://computeassay.com/harness.html) across the full contiguous allocation under production tenancy (§8.2). Accepted if measured DCB ≥ [85]% of the published per-GPU scale-out line rate and the substitutability grade for the contracted workload class is at least the contracted grade. A failed test is a delivery failure, not a credit. |
| Availability | Defined on workload health, not node liveness: a node counts as unavailable while its fabric links flap or its collectives stall beyond [X] seconds. Measurement window and remedies stated as numbers. (See the [contract gotcha list](https://computeassay.com/contracts.html) for why node-up SLAs are not availability.) |
| Term and price | Start on acceptance, not on signature. Price per GPU-hour, escalator if any, take-or-pay percentage, and whether idle hours bill. |
| Hardware substitution | Allowed only to an equal-or-better grade for the contracted workload class, measured, with notice. No silent swaps under an identified-asset test. |
| transferable | The ASSAY-1 `transferable` field, set from Part 2: `true` if the provider has pre-approved ASSAY-TT-1 for this capacity; `consent` if transfer needs consent not to be unreasonably withheld; `false` otherwise. Only `true` tranches are secondary-market eligible. |
| Credit support | Who posts what (prepayment, letter of credit, parent guarantee), and that it moves with the tranche on assignment. |

## Part 2 — Sublease and assignment addendum (term sheet)

| Term | Proposal |
|---|---|
| Parties | Provider; Original Buyer; Transferee. Attaches to an existing capacity agreement; the agreement's terms govern except as stated here. |
| Permitted transfers | The Original Buyer may (a) sublease all or part of a tranche, or (b) assign a whole tranche, to a Qualified Transferee. |
| Qualified Transferee | Passes the provider's standard KYC and sanctions screen; meets [the provider's published credit threshold] or posts equivalent credit support; agrees to the provider's acceptable-use policy. The provider may name up to [N] direct competitors as excluded, published in advance — not chosen per deal. |
| Consent | Pre-approved for Qualified Transferees. The provider has [10] business days after notice to object on a stated, objective ground in this addendum. Silence is consent. No consent fee beyond a capped administrative fee of [$X or Y bps of remaining contract value]. |
| Minimum unit | One whole tranche for assignment. For subleases, contiguous blocks of at least [one scale-out domain / 64 GPUs], so a transfer never fragments a fabric. |
| Economics | Price, term, escalators and take-or-pay pass through unchanged. Original Buyer and Transferee settle any premium or discount between themselves; the provider's revenue is unaffected. |
| Liability | Assignment: novation — the Original Buyer is released once the Transferee's credit support is in place. Sublease: the Original Buyer stays primarily liable to the provider. |
| Delivery risk follows the tranche | Termination rights for late delivery or failed acceptance, and availability remedies, transfer with the tranche. A transferee buys exactly the rights the Original Buyer had. |
| Tenant isolation | On handover the provider re-images and attests storage wipe; the Original Buyer's data, credentials and network configuration never pass to the Transferee. |
| Confidentiality | Pricing terms may be disclosed to a bona fide prospective Transferee under NDA. Without this clause no buyer can be shown what they would be buying. |
| Recording | Each transfer is recorded with the tranche_id and, where measured, the assay certificate hash, so the next counterparty, lender or auditor sees the chain of title and the last measured grade. |
| Governing law | [Party choice]. |

## Why a provider would sign this

It sounds like a concession. It is the opposite. A transferable commitment is worth more to the buyer, so it supports a longer term, a larger tranche and less prepayment haggling. It lowers the provider's own financing cost, because a lender can value collateral that has a secondary market, and the provider's revenue does not change when a tranche changes hands. Above all, it moves a stranded commitment to a buyer who will use it, instead of into a dispute when demand dips. The first providers to pre-approve get a visible `transferable: true` on every graded offering in the registry.

## How it connects

[Delivery risk](https://computeassay.com/delivery.html) prices a tranche before it exists. The [harness](https://computeassay.com/harness.html) accepts it when it arrives. ASSAY-TT-1 lets it move after that. Together they cover the full life of a compute commitment, from forecast to delivery to transfer, on one standard.

Version history: v0.1 draft, 2026-10-26. Comments and redlines: reply to any issue of the report, or open an issue in this repository. Licensed CC BY 4.0 — copy it into your paper.
