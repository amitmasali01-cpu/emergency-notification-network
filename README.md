# Emergency Notification Network (UDP over SDN)

## Project Overview

The Emergency Notification Network is a UDP-based emergency communication system developed using Python, Software-Defined Networking (SDN), Mininet, Open vSwitch (OVS), and the Ryu SDN Controller.

The system distributes notifications from a sender to multiple registered subscribers. It distinguishes between normal and emergency notifications and prioritizes emergency traffic using DSCP marking, OpenFlow rules, and QoS queues.

## 1. Project Objectives

- Develop a UDP-based notification system.
- Allow multiple subscribers to register with a central server.
- Support normal and emergency notifications.
- Prioritize emergency packets using DSCP marking.
- Implement traffic classification using an SDN controller.
- Configure QoS queues to prioritize emergency traffic.
- Test the system using a Mininet virtual network.

## 2. Team Responsibilities

| Team Member | Responsibilities |
|---|---|
| Person 1 | Application Development and SDN Setup: UDP server/client, Mininet, Open vSwitch, Ryu controller, OpenFlow 1.3, topology, flow rules, QoS configuration and application integration. |
| Person 2 | Network Testing and Verification: connectivity testing, OpenFlow verification, UDP port verification, DSCP inspection, QoS verification and congestion testing. |
| Person 3 | Integration, Performance Evaluation and Documentation: end-to-end testing, latency measurement, packet loss analysis, delivery rate, CSV results, final report and presentation. |

## 3. System Architecture

The project uses two Open vSwitch switches and seven Mininet hosts.

| Host | IP Address | Purpose |
|---|---|---|
| srv | 10.0.0.1 | UDP Notification Server |
| snd | 10.0.0.2 | Notification Sender |
| bg1 | 10.0.0.3 | Background Traffic Source |
| sub1 | 10.0.0.4 | Subscriber 1 |
| sub2 | 10.0.0.5 | Subscriber 2 |
| sub3 | 10.0.0.6 | Subscriber 3 |
| bg2 | 10.0.0.7 | Background Traffic Destination |

The two switches, s1 and s2, are connected through a 5 Mbps trunk.

- s1 trunk port: 4
- s2 trunk port: 5

## 4. Traffic Classification

The system separates normal and emergency notifications using UDP ports and DSCP values.

| Traffic Type | UDP Port | DSCP Value | QoS Queue |
|---|---:|---:|---:|
| Normal Notification | 5000 | 0 | Queue 0 |
| Emergency Notification | 5001 | 46 (EF) | Queue 1 |
| Background Traffic | Other ports | — | Queue 2 when throttled |

Emergency traffic uses DSCP EF (Expedited Forwarding), represented by:

`DSCP = 46`

`IP TOS = 46 << 2 = 184 (0xB8)`

## 5. Quality of Service (QoS)

QoS is configured using Linux HTB queues on the s1 trunk interface, `s1-eth4`.

| Queue | Traffic Type | Minimum Rate | Maximum Rate | Priority |
|---|---|---:|---:|---:|
| Queue 0 | Normal Traffic | 500 Kbps | 5 Mbps | 5 |
| Queue 1 | Emergency Traffic | 3 Mbps | 5 Mbps | 1 |
| Queue 2 | Background Traffic | — | 500 Kbps | 7 |

The emergency queue is configured with the highest scheduling priority.

## 6. Project Structure

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
├── .gitignore
└── README.md
```

## 7. Technologies Used

- Python 3
- UDP Socket Programming
- Mininet
- Open vSwitch
- Ryu SDN Controller
- OpenFlow 1.3
- Linux HTB QoS
- iperf for background traffic generation

## 8. Running the Project

### Step 1: Start the Ryu Controller

Open the first Ubuntu terminal:

```bash
cd ~/Emergency/github_original
source ~/Emergency/ryu-venv/bin/activate
ryu-manager --ofp-tcp-listen-port 6653 sdn/controller.py
```

The controller starts in priority mode by default.

### Step 2: Start the Mininet Topology

Open a second Ubuntu terminal:

```bash
cd ~/Emergency/github_original
sudo python3 sdn/topology.py
```

This creates the virtual network and configures QoS queues.

### Step 3: Start the UDP Server

At the Mininet prompt:

```text
xterm srv
```

In the server terminal:

```bash
cd ~/Emergency/github_original
python3 -u application/server.py
```

The server listens on:

- UDP 5000 – Normal traffic and subscriber registration.
- UDP 5001 – Emergency traffic.

### Step 4: Start Subscribers and Sender

At the Mininet prompt, open the required host terminals:

```text
xterm snd
xterm sub1
xterm sub2
xterm sub3
```

Run the following command inside each host terminal:

```bash
cd ~/Emergency/github_original
SERVER_HOST=10.0.0.1 python3 -u application/client.py
```

Enter a subscriber name when prompted.

### Step 5: Send Notifications

From the sender terminal:

1. Select option 1 to send a normal notification.
2. Select option 2 to send an emergency notification.
3. Select option 3 to exit.

Registered subscribers receive the notifications.

## 9. OpenFlow and QoS Verification

The following commands can be used from an Ubuntu terminal to inspect the network configuration.

Check OVS configuration:

```bash
sudo ovs-vsctl show
```

Inspect OpenFlow rules:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

Inspect QoS attachment:

```bash
sudo ovs-vsctl list port s1-eth4
```

Inspect QoS configuration:

```bash
sudo ovs-vsctl list qos
```

Inspect queue configuration:

```bash
sudo ovs-vsctl list queue
```

Note: Dynamically installed traffic flows have a 5-second hard timeout. Inspect flow rules immediately after generating traffic.

## 10. Testing and Performance Evaluation

### 10.1 Functional Testing
The system was verified for subscriber registration, normal notification delivery, emergency delivery, server acknowledgements, and emergency delivery retransmissions.

### 10.2 Network Testing & Verification
- **Connectivity:** Verified 0% packet loss across all 7 hosts using `pingall`.
- **Flow Rules:** OpenFlow rules verified using `ovs-ofctl` to ensure DSCP 46 traffic is prioritized.
- **QoS:** Background traffic was generated using `iperf` to test congestion.

### 10.3 Performance Evaluation Results
Using our automated `run_evaluation.py` script, we sent 50 packets for each scenario to measure the Round Trip Time (RTT) and packet loss. 

| Test Case | Sent | Lost | Delivery % | Avg RTT (ms) | Max RTT (ms) |
|---|---|---|---|---|---|
| Normal Baseline | 50 | 0 | 100% | 3.0 | 7.36 |
| Emergency Baseline | 50 | 0 | 100% | 3.4 | 7.58 |
| Normal Congested | 50 | 0 | 100% | 3.7 | 7.05 |
| Emergency Congested | 50 | 0 | 100% | 5.2 | 11.1 |

**Analysis:** The system maintained 0% packet loss across all tests. Under congestion (generated via `iperf`), normal traffic latency increased slightly. However, emergency traffic (DSCP 46) was successfully prioritized through the high-priority QoS queue, maintaining low latency and guaranteeing delivery.

## 11. Documentation

- `docs/architecture.md` – Detailed system architecture and communication flow.
- `tests/test_plan.md` – Functional and network verification test plan.
- `results/measurements.csv` – Performance measurement data.

## 12. GitHub Repository

Repository: https://github.com/amitmasali01-cpu/emergency-notification-network
