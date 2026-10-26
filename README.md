# emergency-notification-network
UDP-based emergency notification system using SDN (Ryu) and Mininet.
An SDN controller classifies emergency notifications and forwards them through a
high-priority queue, so urgent messages keep low latency and low loss under congestion.

## Architecture
```
 snd, srv, bg1 --- s1 ==== 5 Mbps trunk ==== s2 --- sub1, sub2, sub3, bg2
```
- `application/server.py` – UDP server: registers subscribers, fans out notifications, retransmits
  EMERGENCY notifications until a `DELIVERY_ACK` arrives.
- `application/client.py` – interactive client (subscriber + sender).
- `application/subscriber.py`, `application/sender.py` – automated versions used by experiments.
- `sdn/topology.py` – Mininet topology + OVS HTB queues (0 best-effort, 1 emergency, 2 throttled).
- `sdn/controller.py` – Ryu OpenFlow 1.3 controller.
- `tests/` – test plan and experiment runner. `results/measurements.csv` – measured results.

## How socket app and SDN interact
1. Emergency notifications are marked DSCP 46 (EF) with `IP_TOS` on the UDP socket.
2. The switch has no matching flow, so the first packet goes to the controller (packet-in).
3. The controller matches `ip_dscp=46`, installs a priority-100 flow with `set_queue:1`,
   and enters "emergency mode" for 10 s.
4. During emergency mode or detected congestion (port-stats polling), non-application
   background UDP flows are moved to the throttled queue 2.
5. Flows expire after 5 s, so classification is continuously re-evaluated.

`MODE=static` is the baseline: plain learning switch, no prioritisation.

## Setup
```
sudo apt install mininet openvswitch-switch iperf python3-pip -y
pip3 install ryu
```
(If Ryu fails on a newer Python, use `pip3 install eventlet==0.30.2 ryu` or a Python 3.9 venv.)

## Run the demo manually
```
# terminal 1
MODE=priority ryu-manager sdn/controller.py
# terminal 2
sudo python3 sdn/topology.py
mininet> xterm srv snd sub1 sub2 sub3 bg1 bg2
# srv:        python3 application/server.py
# sub1..3:    SERVER_HOST=10.0.0.1 python3 application/client.py
# snd:        SERVER_HOST=10.0.0.1 python3 application/client.py
# congestion: bg2: iperf -u -s -p 5001      bg1: iperf -u -c 10.0.0.7 -p 5001 -b 10M -t 30
```
Inspect flows: `sudo ovs-ofctl -O OpenFlow13 dump-flows s1`

## Reproduce the performance results
```
sudo env PATH=$PATH python3 tests/run_experiments.py
```
This runs static vs priority controllers with and without congestion and writes
`results/measurements.csv`. See `tests/test_plan.md` for test cases and metrics.

## Results
Paste the table from `results/measurements.csv` here after running the experiments,
with a short comparison of static vs priority.
