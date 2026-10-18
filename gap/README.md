<!-- ai-generated: 90% - Copilot explained the measured client-server latency gap for the Lab 3 toxic -->

# Client-server latency gap

The test used a 100 ms downstream latency toxic with 10 ms of jitter and toxicity 1.0. In the open-loop run,
the client p99 was 238.9 ms, while the svcdesk request histogram's p99 was 133.3 ms. The measured gap was
0.2389 - 0.1333 = 0.1056 seconds. That is close to the toxic's nominal added delay: the downstream toxic delays
responses travelling from svcdesk through Toxiproxy to the client, but it is not part of svcdesk's own handler
duration. The remaining difference comes from the sampled jitter, network scheduling, client-side timing, and
the histogram's finite bucket interpolation. This is why a client-measured latency SLI can be worse than a
server-measured latency SLI even when the service itself is unchanged. The checker repeats the measurement
through the same toxic and permits variation between runs.
