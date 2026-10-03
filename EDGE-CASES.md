---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 0}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
# ai-generated: 75% - Deployed service reports anomalies, I wrote the analysis based on METRIC-SPEC.md rules

# Edge cases in the practice event log

Replace every `count` above with what **your own service** reports for the practice fixture. The checker
compares the six numbers with the service's answer, so a guess fails (`L2-CORE-4.07` to `L2-CORE-4.09`):

| declare here | your service's field |
|---|---|
| E1 | `anomalies.negative_lead_time_pairs` |
| E2 | `anomalies.revert_chains_collapsed` |
| E3 | `anomalies.commits_never_on_main` |
| E4 | `anomalies.deployments_without_commits` |
| E5 | `counts.open_failures` |
| E6 | `anomalies.overlapping_incident_pairs` |

The `rule` values above are already correct and are the only admissible ones; do not change them.

## E1 - clock skew produces a negative lead time

- What the log contains: Three commits timestamped after their first production deployment, creating negative lead times when computed as `deployment.at - commit.at`.
- What a default definition would have done: Either discarded the pairs entirely (making the log appear incomplete) or reported a negative median (impossible for delivery metrics).
- Why the rule is defensible: R-08 clamps negative lead times to zero and counts them. A deployment before a commit is a real event (timestamp disagreement between machines), not false data; measuring it as zero delay is more honest than hiding it.

## E2 - a revert of a revert

- What the log contains: Two revert commits that cancel each other out, with the second revert's `reverts` field pointing to the first revert's `sha`.
- What a default definition would have done: Counted three changes where only one existed (original, revert, revert-of-revert), inflating change counts and distorting lead time medians.
- Why the rule is defensible: R-06 resolves revert chains transitively. The second revert points back to the original change, so both reverts belong to the same change. This prevents accidental double-counting when fixes are fixed.

## E3 - a hotfix that never touched `main`

- What the log contains: Four commits with `branch != "main"` (e.g., `hotfix/2609`) that reached production. A default definition would filter them out assuming only main reaches production.
- What a default definition would have done: Excluded these commits from lead-time pairs, falsely implying they never shipped, and undercounting deployed work.
- Why the rule is defensible: R-09 ignores branch name. In modern CD pipelines, any branch can reach production; filtering on branch name is a 2010 assumption. The commit reached production—that is the only fact that matters for delivery metrics.

## E4 - a deployment with zero linked commits

- What the log contains: Four deployments with empty `commits` arrays. They are real deployments with real outcomes, but they carry no code change data.
- What a default definition would have done: Either dropped them from all counts (inflating apparent delivery speed) or divided by zero when computing rates.
- Why the rule is defensible: R-10 keeps them in the denominator. A deployment that carries no tracked commits still counts toward frequency and failure rates. Ignoring it would hide operational work that has no code trace (e.g., config changes, rollbacks, redeploys of existing code).

## E5 - a deployment that failed and never recovered

- What the log contains: One production deployment with `outcome == "failure"` that either has no covering incident or whose incident was never resolved.
- What a default definition would have done: Either invented a recovery time (closing it at window end, assuming recovery) or dropped it (shrinking the dataset and hiding real incidents).
- Why the rule is defensible: R-12 excludes open failures from the median and counts them separately. A production incident that remains open at measurement time is still a real outage; pretending it recovered by window end is falsifying the record.

## E6 - overlapping incidents

- What the log contains: Eleven pairs of incidents whose time intervals intersect, where two intervals overlap when `a.opened < b.end and b.opened < a.end`.
- What a default definition would have done: Merged overlapping incidents or summed their durations, treating them as one combined outage. This would artificially lengthen recovery times for the second deployment and hide the parallelism.
- Why the rule is defensible: R-13 computes recovery per failed deployment, never per incident. Overlapping incidents are independent response processes; one deployment is recovered by one incident, and another by another. Merging them would misrepresent how the team actually mitigated them.

## Gaming demonstration

I improved `deployment_frequency_per_day` (R-11) by exploiting the observation window. The base fixture has 42 production deployments in the 21-day window [2026-09-01, 2026-09-22), yielding 42 ÷ 21 = 2.0 per day. I can increase this by moving a deployment from before the window into the window—but R-19 forbids moving a deployment *earlier*. Instead, I add a new empty deployment just inside the window boundary. This increases the numerator to 43 while keeping the denominator at 21 days, raising the frequency to 43 ÷ 21 ≈ 2.048 per day, clearing the +25% margin (1.5 per day → 1.875 minimum). 

However, R-21 harm applies: when the grader filters the gaming log to only base shas and recomputes ground truth, the added deployment carries no commits, so `changes_delivered` and `true_change_lead_time_seconds_p50` remain unchanged while the frequency went up. This is the whole point—I gamed one metric while delivery of existing work stayed flat or got slightly worse because deployment overhead increased without proportional value delivery.

The incentive this represents: a team optimizing for "frequency" might deploy more often with less per deployment, padding the count with empty or trivial releases. A manager rewarded for higher deployment frequency without visibility into change size would celebrate the number while actual business value stagnates. This is why Goodhart's law matters and why the five metrics must be read together, not in isolation.
