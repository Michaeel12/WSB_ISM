---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 80% - AI przygotowało robocze opisy decyzji na podstawie wymagań laboratorium; student powinien je przeczytać i zaakceptować. -->

# Decisions

## C1 - SLA clock for P1

**Decision:** P1 uses the wall-clock SLA for acknowledgement and resolution.

**Rejected alternative:** P1 could count only time inside the business-hours window.

**Reason:** A critical organisation-wide outage must be measured continuously, including nights and weekends.

**Service owner:** The SLA process owner approves this because it defines the service commitment.

**Customer outcome:** Reporters receive a clear urgent target that does not pause outside office hours.

## C2 - Closed tickets and reopening

**Decision:** A closed ticket is immutable and cannot be reopened.

**Rejected alternative:** A closed ticket could be reopened during the seven-day reopen window.

**Reason:** Keeping closed tickets immutable preserves an accurate and auditable service history.

**Service owner:** The service desk process owner approves the lifecycle and audit rules for tickets.

**Customer outcome:** A new problem is recorded as a new ticket linked to the closed issue.

## C3 - VIP reporters and the priority matrix

**Decision:** A VIP ticket with matrix priority P3 or P4 is raised to P2.

**Rejected alternative:** VIP status could be stored without changing the matrix priority.

**Reason:** VIP issues need prompt visibility while P1 remains reserved for the most severe impact.

**Service owner:** The service owner approves prioritisation rules because they govern operational attention.

**Customer outcome:** VIP reports are noticed sooner without allowing them to displace genuine P1 incidents.
