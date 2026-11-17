# tests/run_evaluation.py
import socket
import time
import csv
import statistics
import os

# --- CONFIGURATION ---
# IMPORTANT: Check Person 1's topology.py to see the exact Server IP!
# It is usually 10.0.0.1 or 10.0.0.2 in Mininet.
SERVER_IP = "10.0.0.1"  
NORMAL_PORT = 5000
EMERGENCY_PORT = 5001
# ---------------------

def measure_rtt(port, is_emergency, count=50):
    rtts = []
    lost = 0
    
    # DSCP 46 (Expedited Forwarding) = TOS byte 184
    tos_val = 184 if is_emergency else 0
    
    for i in range(count):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, tos_val)
        s.settimeout(1.0) # 1 second timeout
        
        msg = f"Test_Message_{i}".encode()
        start_time = time.time()
        
        try:
            s.sendto(msg, (SERVER_IP, port))
            # Wait for ACK from server
            data, _ = s.recvfrom(1024)
            rtt = (time.time() - start_time) * 1000 # Convert to ms
            rtts.append(rtt)
        except socket.timeout:
            lost += 1
        finally:
            s.close()
            
    if len(rtts) == 0:
        return {"avg": 0, "max": 0, "loss": 100, "delivery": 0}
        
    return {
        "avg": round(statistics.mean(rtts), 2),
        "max": round(max(rtts), 2),
        "loss": round((lost/count)*100, 2),
        "delivery": round(100 - (lost/count)*100, 2)
    }

def run_tests():
    print("Starting Real Evaluation (50 packets per case)...")
    results = []
    
    # 1. Normal Baseline
    print("Testing Normal Traffic (No Congestion)...")
    norm_base = measure_rtt(NORMAL_PORT, False)
    results.append(["Normal Baseline", 50, norm_base['loss'], norm_base['delivery'], norm_base['avg'], norm_base['max']])
    
    # 2. Emergency Baseline
    print("Testing Emergency Traffic (No Congestion)...")
    emerg_base = measure_rtt(EMERGENCY_PORT, True)
    results.append(["Emergency Baseline", 50, emerg_base['loss'], emerg_base['delivery'], emerg_base['avg'], emerg_base['max']])
    
    # 3 & 4. Congested Scenarios
    print("\n" + "="*50)
    print("WAITING FOR CONGESTION")
    print("Tell Person 2 to start the iperf background traffic NOW.")
    input("Press ENTER in this terminal when iperf is running...")
    print("="*50 + "\n")
    
    print("Testing Normal Traffic (Under Congestion)...")
    norm_cong = measure_rtt(NORMAL_PORT, False)
    results.append(["Normal Congested", 50, norm_cong['loss'], norm_cong['delivery'], norm_cong['avg'], norm_cong['max']])
    
    print("Testing Emergency Traffic (Under Congestion)...")
    emerg_cong = measure_rtt(EMERGENCY_PORT, True)
    results.append(["Emergency Congested", 50, emerg_cong['loss'], emerg_cong['delivery'], emerg_cong['avg'], emerg_cong['max']])

    # Save to CSV
    os.makedirs("results", exist_ok=True)
    with open("results/measurements.csv", "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Case", "Sent", "Lost", "Delivery %", "Avg RTT (ms)", "Max RTT (ms)"])
        writer.writerows(results)
        
    print("\n--- EVALUATION COMPLETE ---")
    print("Results saved to results/measurements.csv")
    for r in results:
        print(f"{r[0]}: Avg {r[4]}ms, Max {r[5]}ms, Delivery {r[3]}%")

if __name__ == "__main__":
    run_tests()
