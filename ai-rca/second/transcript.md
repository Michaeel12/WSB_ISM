# Copilot SDK investigator transcript

agent: Copilot SDK assistant in VS Code
model: runtime model identifier not exposed

## Question

Checkout errors paged at 07:09:19Z on 2026-10-12. Investigate 07:00Z to 07:20Z. What is the cause?

## Investigation

The assigned `lab4-rec-3` snapshot was served locally by Prometheus at `http://127.0.0.1:19090`. I queried that read-only HTTP API directly; this transcript does not claim that the course MCP server was used.

### Query 1: product-catalog server errors

At `2026-10-12T07:10:45Z`:

```promql
sum(rate(traces_span_metrics_calls_total{service_name="product-catalog",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) > 0.05
```

Result: `0.14103330555555557`.

At `2026-10-12T07:00:45Z`, the same comparison returned no series.

### Query 2: ad-service p99 latency

At `2026-10-12T07:10:45Z`:

```promql
max(histogram_quantile(0.99,sum by (le)(rate(traces_span_metrics_duration_milliseconds_bucket{service_name="ad",span_kind="SPAN_KIND_SERVER"}[5m])))) > 500
```

Result: `796` milliseconds.

At `2026-10-12T07:00:45Z`, the same comparison returned no series. This establishes elevated latency, not the identity of its flag.

### Query 3: payment server errors

At `2026-10-12T07:10:45Z`:

```promql
sum(rate(traces_span_metrics_calls_total{service_name="payment",span_kind="SPAN_KIND_SERVER",status_code="STATUS_CODE_ERROR"}[5m])) > 0.05
```

Result: no series.

## Findings

Hypothesis C1: The product-catalog service is returning failed server requests, propagating errors to checkout.

Hypothesis C2: The ad service's server-side p99 latency rises sharply during the incident; adManualGc is a plausible seeded change.

Hypothesis C3: The payment service is failing server requests and is the source of the checkout errors.

The snapshot supports product-catalog errors and a separate ad-service latency increase. The payment-error prediction is contradicted by the data. The telemetry does not identify a feature-flag key directly, so the ad flag remains an inference rather than a metric fact.
