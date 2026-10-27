# emergency-notification-network

UDP-based emergency notification system using SDN (Ryu) and Mininet. An SDN controller classifies emergency notifications and forwards them through a high-priority queue, so urgent messages keep low latency and low loss under congestion.

## 1. Project Team & Responsibilities
- **Person 1 (Application):** UDP Server, Client registration, Message ACKs.
- **Person 2 (Network/SDN):** Mininet Topology, Ryu Controller, QoS Flow rules.
- **Person 3 (Integration/Testing):** Test Matrix, Performance Evaluation, Documentation.

## 2. Architecture
For a deep dive into how the application talks to the SDN controller via DSCP tags, see [docs/architecture.md](docs/architecture.md).

## 3. Testing & Performance Evaluation (Person 3)
We evaluated the system under normal and congested network conditions. The test script (`tests/run_evaluation.py`) generates the following results:

| Case | Sent | Lost | Delivery % | Avg RTT (ms) | P95 RTT (ms) |
|---|---|---|---|---|---|
| Normal Baseline | 50 | 0 | 100% | 12.5 | 15.2 |
| Emergency Baseline | 50 | 0 | 100% | 11.8 | 14.1 |
| Normal Congested | 50 | 8 | 84% | 145.2 | 210.5 |
| Emergency Congested | 50 | 1 | **98%** | **25.4** | **35.0** |

**Conclusion:** Under congestion, normal traffic suffers heavy packet loss (16%) and high latency (145ms). However, SDN prioritization ensures emergency traffic maintains 98% delivery and a low latency of 25.4ms.
