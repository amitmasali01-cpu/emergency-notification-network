import os

from mininet.cli import CLI
from mininet.log import setLogLevel
from mininet.net import Mininet
from mininet.node import RemoteController, OVSSwitch
from mininet.topo import Topo

TRUNK_RATE = 5_000_000 


class EmergencyTopo(Topo):
    def build(self):
        s1 = self.addSwitch("s1", protocols="OpenFlow13")
        s2 = self.addSwitch("s2", protocols="OpenFlow13")
        for name, ip in (("srv", "10.0.0.1"), ("snd", "10.0.0.2"),
                         ("bg1", "10.0.0.3")):
            self.addLink(self.addHost(name, ip=ip + "/24"), s1)
        for name, ip in (("sub1", "10.0.0.4"), ("sub2", "10.0.0.5"),
                         ("sub3", "10.0.0.6"), ("bg2", "10.0.0.7")):
            self.addLink(self.addHost(name, ip=ip + "/24"), s2)
        self.addLink(s1, s2, port1=4, port2=5)


def configure_qos(iface="s1-eth4", rate=TRUNK_RATE):
    """OVS HTB queues on the trunk: 0 best-effort, 1 emergency, 2 throttled."""
    os.system(
        f"ovs-vsctl -- set port {iface} qos=@qos "
        f"-- --id=@qos create qos type=linux-htb "
        f"other-config:max-rate={rate} "
        f"queues:0=@q0 queues:1=@q1 queues:2=@q2 "
        f"-- --id=@q0 create queue other-config:min-rate=500000 "
        f"other-config:max-rate={rate} other-config:priority=5 "
        f"-- --id=@q1 create queue other-config:min-rate=3000000 "
        f"other-config:max-rate={rate} other-config:priority=1 "
        f"-- --id=@q2 create queue other-config:max-rate=500000 "
        f"other-config:priority=7 > /dev/null")


def build_network(controller_ip="127.0.0.1", controller_port=6653):
    net = Mininet(topo=EmergencyTopo(), switch=OVSSwitch,
                  controller=None, autoSetMacs=True)
    net.addController("c0", controller=RemoteController,
                      ip=controller_ip, port=controller_port)
    net.start()
    configure_qos()
    return net


if __name__ == "__main__":
    setLogLevel("info")
    network = build_network()
    CLI(network)
    network.stop()
