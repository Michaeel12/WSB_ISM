---
lab5_triage:
  image: ghcr.io/michaeel12/wsb_ism@sha256:d86b364e6881e709f0610b67e91246d9a0a70ebb1dba1fa4ce3646e6d79a7035
  sarif_receipt: 455
---
<!-- ai-generated: 70% - Copilot drafted the text from the pipeline logs and bakeoff.json; the numbers were checked against the SARIF -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
One row per rule of one tool; a row may cover several locations, and the Reason says which.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| trivy | CVE-2025-62727 | fix | starlette 0.41.3 in the image had a Range header DoS; raised fastapi to 0.141.1 in requirements.txt, which pulls starlette 1.10.0 |
| trivy | CVE-2026-48818 | fix | starlette SSRF via UNC paths, fixed in 1.1.0; same change, fastapi 0.141.1 and uvicorn 0.52.4 in requirements.txt |
| trivy | CVE-2026-54283 | fix | starlette request.form() limits ignored, fixed in 1.3.1; the pin bump gives 1.10.0, the image gate then passed |
| semgrep | dockerfile.security.missing-user.missing-user | accept | Dockerfile line 29 has no USER, so the service runs as root; accepted for the course lab, a non-root user is the next step |

## Bake-off

The canary set has 8 defects: 3 in code, 3 credentials and 2 vulnerable pins. Trivy found 4 of them (both pins and two credentials) with 1 false positive, so precision 0.80, recall 0.50 and F1 0.62, the best of the five. Grype and OSV-Scanner each found only the 2 pins, with no false positives: precision 1.00 but recall 0.25. gitleaks found 2 credentials (github-pat and private-key) and flagged a JWT test fixture in token_fixtures.py as a false positive: precision 0.67, recall 0.25. Semgrep found 2 defects (the deserialization in rules_loader.py and the private key) but raised 4 false positives, mostly raw SQL strings and the same JWT fixture: precision 0.33, recall 0.25, F1 0.29, the weakest.

For a gate I would put Trivy first: it covers both dependencies and secrets, and its one false positive is the fixture, which a path rule can deal with. Grype and OSV-Scanner add nothing here because Trivy already finds the same two pins. Semgrep stays report-only because 4 of its 6 findings were noise, and a gate that cries wolf gets ignored.

Three defects were found by none of the five: the weak random token in reset_tokens.py (CWE-338), the broken access check in ticket_access.py, and the credential in mailer.py. They are logic and design flaws or secrets with no known pattern, and no pattern-based scanner sees them. The surprising cell was Semgrep: it missed the access check and the weak random token even though both are classic cases.

Every recall here is an upper bound. The defects were seeded by the course in small, clean modules, and studies of injected defects show detection rates several times higher than on real code, so on a real repository recall would be lower and false positives more numerous. With only 8 defects, one more or fewer found moves the scores by a lot.
