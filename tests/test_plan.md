# Test Plan – Emergency Notification Network

## 1. Introduction

This document describes the testing procedures for the Emergency Notification Network using UDP communication and Software-Defined Networking (SDN).

The testing verifies application functionality, network connectivity, traffic classification, OpenFlow rules, and Quality of Service (QoS) configuration.

## 2. Testing Objectives

- Verify UDP server and client communication.
- Verify subscriber registration.
- Test normal notification delivery.
- Test emergency notification delivery.
- Verify emergency delivery acknowledgements.
- Verify DSCP-based traffic classification.
- Verify OpenFlow rules and QoS queues.
- Evaluate network performance under different traffic conditions.

## 3. Functional Testing

| Test ID | Test Description | Expected Result |
|---|---|---|
| F01 | Start UDP server | Server starts and listens on ports 5000 and 5001. |
| F02 | Start subscriber clients | Clients connect and register with the server. |
| F03 | Send normal notification | Server distributes the notification to registered subscribers. |
| F04 | Send emergency notification | Server distributes the emergency notification. |
| F05 | Emergency delivery acknowledgement | Subscribers acknowledge emergency notification delivery. |
| F06 | Missing acknowledgement | Server attempts retransmission when an acknowledgement is not received. |
| F07 | Duplicate notification handling | Duplicate notification IDs are handled without repeated processing. |
| F08 | Sender acknowledgement | Sender receives the server acknowledgement. |

## 4. Network Verification

The following tests verify the Mininet network and SDN configuration.

| Test ID | Test Description | Verification |
|---|---|---|
| N01 | Network connectivity | Execute `pingall` in Mininet. |
| N02 | Controller connectivity | Check whether both switches are connected to the Ryu controller. |
| N03 | OpenFlow configuration | Inspect flow entries using `ovs-ofctl`. |
| N04 | UDP port verification | Verify that UDP ports 5000 and 5001 are listening. |
| N05 | DSCP verification | Inspect packet markings for normal and emergency traffic. |
| N06 | QoS configuration | Verify QoS attachment and queue parameters. |
| N07 | Background traffic | Generate background traffic using iperf. |
| N08 | Congestion testing | Observe network behaviour under background traffic load. |
| N09 | Emergency priority | Verify emergency traffic classification and queue assignment during congestion. |

## 5. Useful Verification Commands

### Check Network Connectivity

Run inside the Mininet CLI:

```text
pingall
```

### Check OpenFlow Rules

Run in an Ubuntu terminal:

```bash
sudo ovs-ofctl -O OpenFlow13 dump-flows s1
```

### Check Switch Connections

```bash
sudo ovs-vsctl show
```

### Check UDP Ports

```bash
sudo ss -lunp
```

### Check QoS Configuration

```bash
sudo ovs-vsctl list qos
```

### Check Queue Configuration

```bash
sudo ovs-vsctl list queue
```

### Check QoS Attachment

```bash
sudo ovs-vsctl list port s1-eth4
```

Note: Dynamically installed OpenFlow traffic rules have a 5-second hard timeout. Inspect them immediately after generating the relevant traffic.

## 6. Performance Evaluation

Performance evaluation is carried out by comparing normal and emergency traffic under baseline and congested network conditions.

The evaluation considers the following metrics:

| Metric | Description |
|---|---|
| Average Latency | Average time taken for notification delivery. |
| Packet Loss | Number or percentage of packets not successfully delivered. |
| Delivery Rate | Percentage of notifications successfully delivered. |
| Acknowledgement Time | Time taken to receive an emergency delivery acknowledgement. |

Performance measurements should be collected during actual experiments.

## 7. Team Responsibilities for Testing

### Person 1 – Application Development and SDN Setup

- Develop and test UDP server and client applications.
- Configure Mininet and Open vSwitch.
- Set up the Ryu SDN controller.
- Configure OpenFlow 1.3.
- Create the network topology.
- Implement traffic classification and flow rules.
- Configure QoS queues.
- Integrate the application with Mininet.

### Person 2 – Network Testing and Verification

- Verify network connectivity.
- Inspect OpenFlow rules.
- Verify UDP ports and DSCP markings.
- Verify QoS queue configuration.
- Generate background traffic.
- Test congestion conditions.
- Verify emergency traffic prioritization.

### Person 3 – Integration, Performance Evaluation and Documentation

- Perform complete application integration testing.
- Verify end-to-end notification delivery.
- Measure latency and packet loss.
- Calculate delivery rate and acknowledgement time.
- Generate CSV performance results.
- Prepare project documentation and final presentation.

## 8. Expected Outcome

The testing process is expected to demonstrate:

- Successful subscriber registration.
- Successful normal and emergency notification delivery.
- Emergency delivery acknowledgement and retransmission behaviour.
- Correct emergency and normal traffic classification.
- Correct OpenFlow rule installation.
- Correct QoS queue configuration.
- A basis for evaluating emergency traffic performance under congestion.

Actual performance improvements must be established through measured experimental results.

## 9. Conclusion

This test plan provides a structured approach to verifying the Emergency Notification Network.

It covers application functionality, SDN configuration, network verification, QoS behaviour, and performance evaluation.
