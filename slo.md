---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 30d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
    latency:
      objective: 0.99
      threshold_seconds: 0.14
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.14"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 432}
  alerts:
    - {alert: KbSearchErrorsBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchErrorsBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 95% - Copilot drafted the objectives and rationale from the measured Lab 3 profile -->

# SLO for `GET /kb/search`

## Availability

The availability SLI is the rate of non-5xx `/kb/search` responses divided by all `/kb/search` responses. The
99% objective allows a 1% error budget: 432 minutes in a 30-day window. The first load measured 7 upstream
failures among about 2,400 responses (roughly 0.3%), so 99% is achievable while still leaving room for the
occasional failure in `kb-index`, which is outside `svcdesk`'s control. A sustained dependency outage remains
visible as consumed budget rather than being hidden by retries or cached results.

## Latency

The latency SLI counts requests at or below 0.14 seconds, divided by all `/kb/search` requests. The measured
client p50 was 24.5 ms and p99 was 138.5 ms; the threshold therefore sits just above the slow mode and is a
finite histogram boundary, rather than an interpolated guess. The 99% objective gives the same 432-minute
budget as availability. This allows a small tail to exceed the target without treating the ordinary 20-30 ms
responses as slow.

## Alerts

| alert | SLI | burn rate | long / short window | budget spent when it fires | severity: page or chat |
|---|---|---:|---|---|---|
| KbSearchErrorsBurnFast | availability | 14.4 | 1h / 5m | about 2% in one hour | P1 page |
| KbSearchErrorsBurnSlow | availability | 6 | 6h / 30m | about 5% in six hours | P2 chat |

The fast alert pages because this burn rate could exhaust the full budget in about 1.7 days, and continued
customer-visible 5xx errors need intervention at any hour. The slower alert goes to chat: it catches a sustained
degradation with enough time to investigate during working hours, without waking someone for a short burst. Both
alerts require the burn to remain high in the short window, so they reset promptly when the incident ends.

## Buckets

The first exploratory measurement put q at 132.4 ms in the AI draft ladder's (100 ms, 250 ms] bucket. That
bucket is 150 ms wide, or 113.3% of q, so it cannot resolve the p99. The later designed ladder puts the measured
138.5 ms q in (130 ms, 140 ms], a 10 ms bucket (7.2% of q). The buckets from 110 ms through 150 ms are spaced
10 ms apart, resolving the entire ±10% band around q; the remaining boundaries cover ordinary response times
and the longer tail.
