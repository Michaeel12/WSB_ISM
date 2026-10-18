---
lab3_first_draft:
  source: ai
  tool: "Copilot SDK in VS Code, 18 October 2026; drafted after an exploratory load"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]
  verdict: refuted
  evidence: {p99_seconds: 0.1324, bucket: [0.1, 0.25], relative_width: 1.133}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: 0.1324, bucket: [0.04, 0.5], relative_width: 3.474}
---
<!-- ai-generated: 100% - Copilot recorded its initial recommendation and the measured bucket arithmetic -->

Process note: the answer below was drafted after an exploratory load had already been run; this does not meet the
handout's prescribed order. The exploratory p99 and both verdict calculations are recorded transparently.

## Prompt

For the svcdesk Lab 3 endpoint GET /kb/search, suggest finite Prometheus histogram bucket boundaries in seconds
and an availability alert. This is a generic first draft, before the final service-specific ladder is designed.

## Answer

For a generic Python HTTP service, start with these finite boundaries in seconds: [0.005, 0.01, 0.025, 0.05,
0.075, 0.1, 0.25, 0.5, 0.75, 1, 2.5, 5, 7.5, 10]. For a 99% availability objective, define the bad-request
ratio as 5xx `/kb/search` requests divided by all `/kb/search` requests. A fast multiwindow alert can compare
that ratio over both 1h and 5m against `14.4 * (1 - 0.99)`, with `for: 5m`; label it `service: svcdesk`,
`slo: availability`, `severity: P1`. Measure the actual p99 and replace the generic buckets with finer
boundaries around the measured tail before treating this as production-ready.

## Verdict on the draft ladder

In the exploratory run, the measured p99 was 0.1324 s. The assistant's ladder puts it in (0.1, 0.25], a
0.1500 s bucket whose relative width is 0.1500 / 0.1324 = 1.133. That is far above the 0.20 limit, so the
draft verdict is **refuted**: `histogram_quantile` can place the reported p99 anywhere across that 150 ms
bucket.

## The draft alert rule

The draft's 14.4x multiwindow availability burn rule is kept as `KbSearchErrorsBurnFast`; a slower 6x alert was
added for sustained degradation. Both use the declared availability objective and a short window, and the fast
alert is P1 because the budget would be consumed quickly.

## Verdict on the instructor's flawed ladder

The same 0.1324 s p99 falls in the flawed ladder's (0.04, 0.5] bucket. Its 0.4600 s width is
0.4600 / 0.1324 = 3.474 times the p99, so the instructor's ladder is **refuted** as well.
