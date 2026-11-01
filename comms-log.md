---
lab4_comms:
  awareness: 2026-10-12T07:09:19Z
  detection: 2026-10-12T07:09:19Z
  classification: 2026-10-12T07:10:07Z
  nis2:
    early_warning_due: 2026-10-13T07:09:19Z
    notification_due: 2026-10-15T07:09:19Z
    notification_sent: 2026-10-12T07:30:00Z
    final_report_due: 2026-11-12T07:30:00Z
  ksc:
    early_warning_due: 2026-10-13T07:09:19Z
    notification_due: 2026-10-15T07:09:19Z
    notification_sent: 2026-10-12T07:40:00Z
    final_report_due: 2026-11-12T07:40:00Z
  dora:
    initial_due: 2026-10-12T11:10:07Z
    initial_sent: 2026-10-12T08:00:00Z
    intermediate_due: 2026-10-15T08:00:00Z
    intermediate_sent: 2026-10-14T08:00:00Z
    final_due: 2026-11-14T08:00:00Z
  log:
    - {at: 2026-10-12T07:09:19Z, to: incident response, what: Declare awareness and detection after the P1 page; begin NIS2 and KSC clocks.}
    - {at: 2026-10-12T07:10:07Z, to: DORA reporting lead, what: Classify the acknowledged P1 as major for this exercise and start the DORA clock.}
    - {at: 2026-10-12T07:30:00Z, to: competent NIS2 authority, what: Send the exercise notification before the 72-hour deadline.}
    - {at: 2026-10-12T07:40:00Z, to: CSIRT NASK, what: Send the KSC notification before its 72-hour deadline.}
    - {at: 2026-10-12T08:00:00Z, to: financial supervisor, what: Send the DORA initial notification before its four-hour deadline.}
    - {at: 2026-10-14T08:00:00Z, to: financial supervisor, what: Send the DORA intermediate report before its 72-hour deadline.}
---
<!-- ai-generated: 90% - drafted with AI assistance using the supplied regulatory-clock rules and incident timestamps -->

# Communications log: the regulators' clocks

## The three instants you defend

For this exercise, awareness under NIS2 and detection under the Polish KSC act are both set to the recorded P1 detection at 2026-10-12T07:09:19Z: that is the earliest supplied evidence that the shop incident was significant and detected. The DORA classification is set to the ticket acknowledgement at 07:10:07Z, when the on-call had confirmed the P1 impact and acknowledged the incident. These are exercise assumptions based on the recorded artifacts, not statements that a real legal assessment occurred.

## The log

The communications above are hypothetical submissions for the exercise. Each is scheduled before its computed deadline: the NIS2 and KSC notifications precede their 72-hour limits, the DORA initial notice precedes its four-hour limit, and the intermediate DORA report precedes its 72-hour limit. The final-report due dates are one calendar month after the corresponding notifications, as required by the supplied specification.
