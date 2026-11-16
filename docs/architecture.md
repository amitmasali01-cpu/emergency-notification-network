# System Architecture – Emergency Notification Network

## 1. Introduction

The Emergency Notification Network is designed to deliver normal and emergency notifications using UDP communication and Software-Defined Networking (SDN).

The system uses a central Python server, multiple subscriber clients, Open vSwitches, and a Ryu SDN controller. Emergency notifications receive higher network priority through DSCP marking, OpenFlow rules, and Quality of Service (QoS) queues.

## 2. Overall Architecture

The system consists of the following components:

1. **UDP Server:** Receives notifications, manages subscriber registration, and distributes messages.
2. **UDP Clients:** Allow users to register and send or receive notifications.
3. **Mininet:** Creates the virtual network topology.
4. **Open vSwitch (OVS):** Forwards packets between network hosts.
5. **Ryu Controller:** Installs OpenFlow rules and manages traffic classification.
6. **QoS Queues:** Provide different treatment for normal, emergency, and background traffic.

## 3. Network Topology

The Mininet topology contains two Open vSwitches and seven hosts.

| Host | IP Address | Function |
|---|---|---|
| srv | 10.0.0.1 | Notification server |
| snd | 10.0.0.2 | Notification sender |
| bg1 | 10.0.0.3 | Background traffic source |
| sub1 | 10.0.0.4 | Subscriber 1 |
| sub2 | 10.0.0.5 | Subscriber 2 |
| sub3 | 10.0.0.6 | Subscriber 3 |
| bg2 | 10.0.0.7 | Background traffic destination |

### Switch Connections

- Switch s1 connects to the server, sender, and bg1.
- Switch s2 connects to the three subscribers and bg2.
- s1 and s2 are connected through a 5 Mbps trunk.
- The trunk uses port 4 on s1 and port 5 on s2.
- Both switches use OpenFlow 1.3.
- The Ryu controller runs at `127.0.0.1:6653`.

## 4. Application Layer

### 4.1 UDP Server

The server is implemented in `application/server.py`.

Its responsibilities include:

- Listening for subscriber registration.
- Maintaining the list of registered subscribers.
- Receiving normal and emergency notifications.
- Broadcasting notifications to registered subscribers, excluding the sender.
- Processing delivery acknowledgements for emergency notifications.
- Retransmitting emergency notifications when acknowledgements are not received.

The server uses two UDP ports:

| Port | Purpose |
|---|---|
| 5000 | Normal notifications and registration |
| 5001 | Emergency notifications |

### 4.2 UDP Client

The client is implemented in `application/client.py`.

Its responsibilities include:

- Registering with the server.
- Sending normal notifications.
- Sending emergency notifications.
- Receiving notifications from the server.
- Sending delivery acknowledgements for emergency notifications.

The client selects the destination UDP port according to the notification type.

### 4.3 Notification Communication

**Normal notification:**

1. The sender creates a normal notification.
2. The client sends it through UDP port 5000.
3. The server receives and distributes the notification.
4. Registered subscribers receive the message.
5. Normal notifications do not require subscriber delivery acknowledgements.

**Emergency notification:**

1. The sender creates an emergency notification.
2. The client sends it through UDP port 5001.
3. The packet is marked with DSCP value 46.
4. The server distributes it to registered subscribers.
5. Subscribers send delivery acknowledgements.
6. The server retransmits when an acknowledgement is not received, up to three attempts.

## 5. Traffic Classification

The system identifies traffic using UDP ports and DSCP marking.

| Traffic Type | UDP Port | DSCP Value |
|---|---:|---:|
| Normal | 5000 | 0 |
| Emergency | 5001 | 46 (EF) |

Emergency traffic uses Expedited Forwarding (EF).

The IP TOS value corresponding to DSCP 46 is:

`IP TOS = 46 × 4 = 184`

This marking helps the SDN controller identify emergency packets.

## 6. SDN Controller

The controller is implemented in `sdn/controller.py` using the Ryu framework.

It communicates with Open vSwitch through OpenFlow 1.3.

Its main responsibilities include:

- Managing switch connections.
- Learning source MAC addresses.
- Installing forwarding rules.
- Identifying normal and emergency traffic.
- Assigning traffic to the appropriate QoS queues.
- Monitoring trunk utilization.
- Applying background traffic throttling during congestion conditions.

### Flow Priorities

| Traffic Type | OpenFlow Priority | Queue |
|---|---:|---:|
| Emergency | 100 | Queue 1 |
| Normal | 10 | Queue 0 |

Emergency traffic receives a higher OpenFlow priority than normal application traffic.

Dynamically installed flows have a hard timeout of 5 seconds.

### Congestion Monitoring

The controller monitors the s1 trunk port (port 4) every 2 seconds.

When utilization exceeds the configured 80% threshold, the controller can apply background traffic throttling. The emergency hold period is configured for 10 seconds.

## 7. Quality of Service (QoS)

QoS is configured using Linux HTB queues on the s1 trunk interface `s1-eth4`.

| Queue | Traffic | Minimum Rate | Maximum Rate | Priority |
|---|---|---:|---:|---:|
| Queue 0 | Normal | 500 Kbps | 5 Mbps | 5 |
| Queue 1 | Emergency | 3 Mbps | 5 Mbps | 1 |
| Queue 2 | Background | Not specified | 500 Kbps | 7 |

Queue 1 is configured with the highest scheduling priority.

This configuration is intended to provide preferential treatment to emergency traffic while limiting background traffic when throttling is applied.

## 8. Project Directory Structure

```text
emergency-notification-network/
│
├── application/
│   ├── client.py
│   └── server.py
│
├── docs/
│   └── architecture.md
│
├── results/
│   └── measurements.csv
│
├── sdn/
│   ├── controller.py
│   └── topology.py
│
├── tests/
│   ├── run_evaluation.py
│   └── test_plan.md
│
├── README.md
└── .gitignore
```

## 9. Technologies Used

- Python 3
- UDP Socket Programming
- Mininet
- Open vSwitch
- Ryu SDN Controller
- OpenFlow 1.3
- Linux HTB QoS

## 10. Conclusion

The architecture combines application-level notification delivery with SDN-based traffic management.

Normal and emergency notifications are classified separately. Emergency packets are marked using DSCP EF and assigned a higher-priority OpenFlow rule and QoS queue.

The system provides a platform for testing notification delivery and evaluating traffic prioritization in a software-defined network.
