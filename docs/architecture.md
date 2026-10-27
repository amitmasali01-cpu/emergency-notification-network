# System Architecture: Emergency Notification Network

## 1. Problem Understanding
The goal is to build a UDP-based emergency notification system that distributes urgent messages to multiple clients. The system uses an SDN controller to identify emergency traffic and prioritize it over normal traffic, ensuring low latency and low packet loss even under congested network conditions.

## 2. Components
- **Application Layer (Person 1):** UDP Server and Client. The server registers clients, classifies messages (normal/emergency), and sends them. Clients send acknowledgments.
- **Network Layer (Person 2):** Mininet topology with 1 Open vSwitch (OVS) and 4 hosts. Ryu SDN controller classifies traffic using QoS queues.
- **Integration & Testing (Person 3):** Connecting the app to the SDN, generating traffic, and measuring performance (latency/loss).

## 3. Communication & Integration Flow
1. Clients register with the UDP server.
2. The server tags emergency packets using DSCP (Differentiated Services Code Point).
   - **Emergency:** DSCP EF (Expedited Forwarding) -> `ip_tos=0xb8`
   - **Normal:** DSCP AF11 -> `ip_tos=0x28`
3. The OVS switch and Ryu controller detect these tags.
4. Emergency packets are routed to a high-priority QoS queue (Queue 1).
5. Normal packets are routed to a default, lower-priority queue (Queue 0).
