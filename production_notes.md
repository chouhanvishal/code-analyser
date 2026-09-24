# Production Readiness Notes: Autonomous Code-Change Service

This document describes the architectural, operational, and lifecycle considerations for running the autonomous code-change service at production scale.

---

## 1. Scaling Architecture

### Limitations of Single-Node Server
The current service handles concurrent requests using a threaded HTTP server and local Docker executions. In high-throughput production environments:
- Long-running LLM generation and Docker test runs saturate local CPU, memory, and disk I/O.
- Docker-in-Docker / socket mounting poses concurrency limits and potential noisy-neighbor resource contention.

### Production Solution: Event-Driven Queue & Ephemeral Worker Pool
```
                  ┌────────────────────┐
                  │   API Gateway /    │
                  │   Load Balancer    │
                  └─────────┬──────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │  FastAPI Ingestion │ (Validates schema, auth, deadlines)
                  └─────────┬──────────┘
                            │
                            ▼
                  ┌────────────────────┐
                  │ Job Queue / Broker │ (e.g., Redis Streams, AWS SQS, Temporal)
                  └─────────┬──────────┘
                            │
        ┌───────────────────┼───────────────────┐
        ▼                   ▼                   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Task Worker  │    │ Task Worker  │    │ Task Worker  │ (Auto-scaled on K8s)
│  (Sandbox)   │    │  (Sandbox)   │    │  (Sandbox)   │
└──────────────┘    └──────────────┘    └──────────────┘
```

1. **Decoupled Job Orchestration**:
   - Ingestion API receives the request, stores the snapshot in object storage (S3/GCS), and places a job message onto a queue with deadline metadata.
   - Workers consume jobs asynchronously using **Temporal.io** or **Celery** with strict workflow timers.
2. **Ephemeral Sandbox Execution**:
   - Instead of sharing a host Docker daemon, worker pods execute tasks inside micro-VMs or isolated sandbox containers (e.g., **AWS Firecracker**, **gVisor / Kata Containers**, or **Kubernetes ephemeral pods**) with strict cgroup memory and CPU quotas.
3. **Horizontal Pod Autoscaling (HPA)**:
   - Workers scale dynamically based on queue depth and pending deadlines.

---

## 2. Observability & Monitoring

### Metrics (Prometheus / Datadog)
- **Acceptance & Gate Metrics**:
  - `service_requests_total`: Total requests categorized by outcome (`accept`, `reject_static`, `reject_apply`, `reject_test`, `timeout`, `null_diff`).
  - `service_gate_rejection_rate`: Percentage of candidate diffs caught by the delivery gate.
- **Latency & Timings**:
  - `service_duration_seconds` (histogram): Total time to completion versus allocated deadline.
  - `llm_request_duration_seconds`: Model inference latency per turn.
  - `sandbox_test_duration_seconds`: Time spent executing tests in the sandbox.
- **Cost & Token Tracking**:
  - `llm_tokens_total` (input / output) labeled by model and task.
  - `llm_cost_usd_total`: Accumulated spend in real time.

### Distributed Tracing & Structured Logging
- OpenTelemetry instrumentation on every request spanning:
  1. Archive extraction & baseline test run.
  2. Each LLM agent turn (prompt, response, tool execution).
  3. Gate validation stages (static, apply, test).
- Correlation ID (`request_id`) propagated across all log lines.

---

## 3. Cost Control & LLM Optimization

1. **Model Cascading / Tiered Routing**:
   - Start task inspection and simple bug fixes with lightweight, low-cost models (e.g., `gemini-2.5-flash` or `gpt-4o-mini`).
   - Escalate to high-reasoning models (e.g., `claude-3-5-sonnet` or `o1-mini`) only if baseline tests fail or initial diff attempts fail verification.
2. **Prompt Optimization & Context Compaction**:
   - Truncate repetitive tool outputs and large compiler logs.
   - Cache common repository dependency files or initial repository summaries.
3. **Strict Budget Caps**:
   - Enforce per-request token caps (e.g., max $0.05 per request) to prevent run-away agent loops.

---

## 4. Absorbing Breaking Changes to Request Contract

If the client updates the request contract (e.g., changing payload schema, adding environment metadata, changing response format):

1. **API Versioning**:
   - Expose explicit versioned routes (`POST /v1/solve`, `POST /v2/solve`).
   - Retain backward compatibility on existing paths until client deprecation window completes.
2. **Tolerant Schema Readers**:
   - Use Pydantic / dataclasses with lenient parsing (`extra = "ignore"`) to prevent unannounced additive fields from breaking serialization.
3. **Feature Flags & Adaptive Handlers**:
   - Inspect request payload attributes dynamically; if new parameters (e.g., `toolchain_hints`, `memory_limit_mb`) are provided, adapt the sandbox configuration seamlessly.
