import os
import time
from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import (CONFIG_DISPATCHER, MAIN_DISPATCHER,
                                    DEAD_DISPATCHER, set_ev_cls)
from ryu.lib import hub
from ryu.lib.packet import packet, ethernet, ipv4, udp, ether_types
from ryu.ofproto import ofproto_v1_3
MODE = os.environ.get("MODE", "priority")
APP_PORT = 5000  
EF_DSCP = 46 
Q_BEST, Q_EMERGENCY, Q_THROTTLE = 0, 1, 2

PRIO_EMERGENCY = 100
PRIO_NORMAL = 10
FLOW_HARD_TIMEOUT = 5  
EMERGENCY_HOLD = 10      

QOS_DPID = 1            
TRUNK_PORT = 4        
TRUNK_CAPACITY_BPS = 5_000_000
CONGESTION_THRESHOLD = 0.8
POLL_INTERVAL = 2


class EmergencyController(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mac_to_port = {}
        self.datapaths = {}
        self.emergency_until = 0.0
        self.congested = False
        self.last_tx = None
        self.logger.info("Controller started in MODE=%s", MODE)
        hub.spawn(self._monitor)
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features(self, ev):
        dp = ev.msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        match = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofp.OFPP_CONTROLLER,
                                          ofp.OFPCML_NO_BUFFER)]
        self._add_flow(dp, 0, match, actions)

    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change(self, ev):
        dp = ev.datapath
        if ev.state == MAIN_DISPATCHER:
            self.datapaths[dp.id] = dp
        else:
            self.datapaths.pop(dp.id, None)

    def _add_flow(self, dp, priority, match, actions, hard_timeout=0):
        ofp, parser = dp.ofproto, dp.ofproto_parser
        inst = [parser.OFPInstructionActions(ofp.OFPIT_APPLY_ACTIONS, actions)]
        dp.send_msg(parser.OFPFlowMod(datapath=dp, priority=priority,
                                      match=match, instructions=inst,
                                      hard_timeout=hard_timeout))

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp, parser = dp.ofproto, dp.ofproto_parser
        in_port = msg.match["in_port"]

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocol(ethernet.ethernet)
        if eth is None or eth.ethertype == ether_types.ETH_TYPE_LLDP:
            return

        self.mac_to_port.setdefault(dp.id, {})[eth.src] = in_port
        out_port = self.mac_to_port[dp.id].get(eth.dst, ofp.OFPP_FLOOD)

        actions = []
        ip = pkt.get_protocol(ipv4.ipv4)
        u = pkt.get_protocol(udp.udp)

        if ip and u and out_port != ofp.OFPP_FLOOD:
            queue, priority = self._classify(dp.id, ip, u)
            match = parser.OFPMatch(
                in_port=in_port, eth_type=ether_types.ETH_TYPE_IP,
                ipv4_src=ip.src, ipv4_dst=ip.dst, ip_proto=17,
                ip_dscp=ip.tos >> 2, udp_src=u.src_port, udp_dst=u.dst_port)
            if queue is not None:
                actions.append(parser.OFPActionSetQueue(queue))
            actions.append(parser.OFPActionOutput(out_port))
            self._add_flow(dp, priority, match, actions, FLOW_HARD_TIMEOUT)
        else:
            actions.append(parser.OFPActionOutput(out_port))

        data = msg.data if msg.buffer_id == ofp.OFP_NO_BUFFER else None
        dp.send_msg(parser.OFPPacketOut(
            datapath=dp, buffer_id=msg.buffer_id, in_port=in_port,
            actions=actions, data=data))

    def _classify(self, dpid, ip, u):
        """Return (queue_id or None, flow priority)."""
        if MODE != "priority" or dpid != QOS_DPID:
            return None, PRIO_NORMAL

        now = time.time()
        if (ip.tos >> 2) == EF_DSCP:
            self.emergency_until = now + EMERGENCY_HOLD
            self.logger.info("EMERGENCY flow %s -> %s : high-priority queue",
                             ip.src, ip.dst)
            return Q_EMERGENCY, PRIO_EMERGENCY

        is_app = APP_PORT in (u.src_port, u.dst_port)
        if not is_app and (now < self.emergency_until or self.congested):
            self.logger.info("Throttling background flow %s -> %s",
                             ip.src, ip.dst)
            return Q_THROTTLE, PRIO_NORMAL
        return Q_BEST, PRIO_NORMAL

    # ------------------------------------------------------------------
    # Monitoring: poll trunk port utilisation
    # ------------------------------------------------------------------
    def _monitor(self):
        while True:
            dp = self.datapaths.get(QOS_DPID)
            if dp:
                req = dp.ofproto_parser.OFPPortStatsRequest(dp, 0, TRUNK_PORT)
                dp.send_msg(req)
            hub.sleep(POLL_INTERVAL)

    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply(self, ev):
        now = time.time()
        for s in ev.msg.body:
            if s.port_no != TRUNK_PORT:
                continue
            if self.last_tx is not None:
                old_bytes, old_time = self.last_tx
                bps = (s.tx_bytes - old_bytes) * 8 / max(now - old_time, 1e-6)
                util = bps / TRUNK_CAPACITY_BPS
                was = self.congested
                self.congested = util >= CONGESTION_THRESHOLD
                if self.congested != was:
                    self.logger.info("Trunk utilisation %.0f%% -> congestion %s",
                                     util * 100,
                                     "DETECTED" if self.congested else "cleared")
            self.last_tx = (s.tx_bytes, now)
