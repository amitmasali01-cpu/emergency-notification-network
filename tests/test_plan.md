
# Test Plan – Emergency Notification Network

## Objective
Verify that the UDP notification application works end to end over the Mininet + Ryu SDN
network, and that the SDN controller identifies and prioritises emergency traffic,
especially under congestion.

## Environment
- Ubuntu 20.04/22.04 VM, Mininet, Open vSwitch, Ryu (`pip install ryu`), `iperf` (v2), Python 3
- Topology: `sdn/topology.py` (2 switches, 1 server, 1 sender, 3 subscribers, 2 background hosts, 5 Mbps trunk)
- Controller: `sdn/controller.py` (`MODE=priority` = proposed, `MODE=static` = baseline)

## Functional Test Cases
| ID | Test | Steps | Expected result |
|----|------|-------|-----------------|
| F1 | Subscriber registration | Start server, start `client.py` on sub1/sub2/sub3 | Each prints `[SUCCESS] Subscriber registered.` and server logs `[REGISTER]` |
| F2 | Normal notification | Send option 1 from `snd` | All other subscribers display it; sender gets `[SERVER ACK]` with recipient count 3 |
| F3 | Emergency notification | Send option 2 from `snd` | All subscribers display it with priority EMERGENCY; server logs `DELIVERED` |
| F4 | Emergency classification | Send emergency, watch Ryu log | Controller logs `EMERGENCY flow ... high-priority queue` |
| F5 | Flow rules | `sudo ovs-ofctl -O OpenFlow13 dump-flows s1` | Priority-100 flows with `ip_dscp=46` and `set_queue:1` for emergency traffic |
| F6 | Delivery confirmation | Check server output / `server_log.csv` | Every emergency notification has a `DELIVERED` row |
| F7 | Duplicate handling | Resend same notification id | Server re-ACKs, does not forward twice; subscriber ignores duplicate |

## Challenging Scenarios
| ID | Scenario | Steps | Expected result |
|----|----------|-------|-----------------|
| C1 | Congestion | Run `iperf -u -c 10.0.0.7 -b 10M` from bg1 (trunk is 5 Mbps) while sending notifications | Controller logs `congestion DETECTED`; background flows moved to throttled queue; emergency notifications still delivered |
| C2 | Packet loss | Reuse the C1 overload (do not add `tc` rules on `s1-eth4`; they would replace the OVS QoS queues) | Emergency messages retransmitted by server until `DELIVERY_ACK`; `retries > 0` visible in `server_log.csv` |
| C3 | Subscriber failure | Kill one subscriber during an emergency | Server retries up to 5 times then logs `GAVE_UP`; others unaffected |

## Performance Evaluation
Run `sudo env PATH=$PATH python3 tests/run_experiments.py`. It runs four experiments, each
sending 40 EMERGENCY and 40 NORMAL notifications to 3 subscribers:

| Experiment | Controller mode | Background load |
|------------|-----------------|-----------------|
| static_no_congestion | static (baseline) | none |
| static_congestion | static (baseline) | 10 Mbps UDP |
| priority_no_congestion | priority (proposed) | none |
| priority_congestion | priority (proposed) | 10 Mbps UDP |

Metrics (written to `results/measurements.csv`):
- `latency_ms` – mean end-to-end latency (receive time − sender timestamp)
- `packet_loss_percent` – share of (notification, subscriber) pairs not delivered on the first transmission
- `delivery_rate_percent` – share of (notification, subscriber) pairs eventually delivered

## Success Criteria
- Under congestion, emergency latency and loss with `priority` mode are clearly lower than with `static` mode.
- Without congestion, both modes perform similarly (no overhead from prioritisation).
- Emergency delivery rate stays at or near 100% in `priority` mode.
