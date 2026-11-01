---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc]
---
<!-- ai-generated: 90% - drafted with AI assistance from the assigned recording and Prometheus queries; student review pending -->

# Postmortem: Checkout errors and elevated ad latency

## Date

The assigned recorded incident occurred on 2026-10-12; this postmortem was prepared from its supplied snapshot and ticket.

## Authors

Prepared with AI assistance for the student, using the assigned `lab4-rec-3` run; the on-call actions below describe the recording.

## Status

The recorded incident is complete and service recovered; the problem record and preventive actions remain open for review.

## Summary

Checkout requests failed after the product catalog began returning errors, while ad-service latency also rose. The snapshot reports a 394-second interval from fault onset to alert recovery.

## Impact

At 2026-10-12T07:10:45Z, the five-minute rate of checkout `PlaceOrder` errors was 0.00767/s and the rate of product-catalog server errors was 0.141/s. The ad-service server p99 was 796 ms, compared with 4.86 ms at 07:04:45Z. These are measurements from `traces_span_metrics_calls_total` and `traces_span_metrics_duration_milliseconds_bucket`; they describe the recorded window, not a count of unique affected customers.

## Root Causes

The `productCatalogFailure` flag is supported by downstream `GetProduct` errors and product-catalog server errors. The `adManualGc` flag is supported by the ad-service p99 increase from 4.86 ms in the healthy sample to 796 ms during the incident. The encrypted recording may contain a third resource-class flag; it is not guessed here.

## Trigger

The seeded fault became active at 2026-10-12T07:05:45Z. The available evidence points to seeded changes affecting product-catalog errors and ad-service latency; the exact third flag is not exposed by the recording.

## Resolution

The assigned recording shows service recovery by 07:12:19Z, when the detecting alert's firing run ended. The supplied ticket and transcript do not timestamp individual flag changes, so this report does not invent an order or per-flag mitigation time.

## Detection

`ShopCheckoutErrors` detected the incident at 07:09:19Z, 214 seconds after onset. The assigned ticket was acknowledged at 07:10:07Z, 48 seconds after detection; recovery followed 394 seconds after onset.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a product-catalog error-rate dashboard panel and a runbook query for downstream checkout failures. | prevent | Service team | ITSM-401 |
| Add an ad-service latency investigation step to the on-call checklist and rehearse the recorded mitigation. | process | On-call lead | ITSM-402 |

## Lessons Learned

### What went well

The checkout symptom produced a P1 page, the ticket was acknowledged after detection, and the recording contains a resolved alert run.

### What went wrong

The initial investigation transcript considered payment failure without supporting evidence; evaluating each claim against the snapshot ruled it out.

### Where we got lucky

The snapshot contains both the downstream product-catalog errors and the ad latency change, allowing two likely flags to be identified without guessing all flags in the pool.

## Timeline

- 2026-10-12T07:05:45Z — the seeded fault begins; the recorded baseline ends.
- 2026-10-12T07:09:19Z — `ShopCheckoutErrors` starts firing and the pager notification marks detection.
- 2026-10-12T07:10:07Z — the P1 ticket is acknowledged.
- 2026-10-12T07:12:19Z — the detecting alert's firing run ends; the incident is recovered in the recording.
- The recording does not expose exact individual flag-toggle times; no unsupported action timestamps are asserted.

## Supporting information

`incident/tsdb-snapshot.tar.gz`, `incident/ticket.json`, the assigned transcript, the four recomputed clocks from `itsmlab incident 4`, and the evaluated PromQL predictions in `ai-rca-eval.json` support this account. The queries and times in Impact are documented above for reproducibility.

## Problem record

- Incident record: P1 ticket 1224ad8d-06a8-4ae3-865a-da2015a4ddb5 from the assigned recording.
- Root cause: Seeded changes caused product-catalog errors and elevated ad-service latency; one resource-class cause remains unconfirmed.
- Known error: The recorded product-catalog failure mode is analyzed, but its underlying seeded configuration is not available locally.
- Workaround: The recorded run restored service before 07:12:19Z; the supplied artifacts do not reveal per-flag workaround timestamps.
