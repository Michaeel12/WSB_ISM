<!-- ai-generated: 90% - drafted with AI assistance by comparing both evaluated transcripts and their PromQL results -->

# Investigator comparison

The recorded Qwen investigator and the Copilot SDK investigator both found evidence of checkout trouble and downstream product-catalog errors. The recorded transcript used client-side checkout spans (`GetProduct` and `PlaceOrder`); the second investigator checked product-catalog server errors directly. Both measurements are consistent with a product-catalog failure affecting checkout, and both predictions were false at the healthy comparison time and true during the incident.

The recorded investigator proposed a payment failure, but its `PaymentService/Charge` query returned no series. The second investigator independently tested payment server errors and also found no supporting series. Both scorecards therefore mark the payment hypothesis as contradicted rather than carrying it into the root-cause claim.

The investigations differed on the additional signal. The recorded model speculated about a broad load or resource bottleneck from aggregate errors. The second query isolated a large ad-service p99 increase, from a healthy single-digit millisecond value to 796 ms during the incident. That supports an ad-latency symptom and makes `adManualGc` plausible, but neither transcript can read the hidden flag state from a metric. The postmortem therefore identifies the flag as an evidence-based inference and does not invent the third resource-class flag. The second investigator used direct read-only Prometheus HTTP queries; it did not use the supplied MCP server, which is recorded explicitly in its ledger.
