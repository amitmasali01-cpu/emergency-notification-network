
import socket
import json
import time
import uuid
import threading

HOST = "0.0.0.0"
NORMAL_PORT = 5000
EMERGENCY_PORT = 5001
BUFFER_SIZE = 4096

ACK_TIMEOUT = 0.2
MAX_RETRIES = 3
DSCP_EF = 46 << 2

subscribers = {}
pending = {}
seen_notifications = set()
lock = threading.Lock()


def send_json(sock, message, address):
    data = json.dumps(message).encode("utf-8")
    sock.sendto(data, address)


def register_subscriber(server, message, address):
    name = str(message.get("name", "Anonymous")).strip() or "Anonymous"

    with lock:
        subscribers[address] = {
            "name": name,
            "registered_at": time.time()
        }

    print(f"[REGISTER] {name} from {address}")

    send_json(server, {
        "type": "REGISTER_ACK",
        "message": "Registration successful",
        "server_time": time.time()
    }, address)


def unsubscribe_subscriber(server, address):
    with lock:
        subscriber = subscribers.pop(address, None)

        expired = [
            key for key in pending if key[1] == address
        ]

        for key in expired:
            pending.pop(key, None)

    if subscriber:
        print(f"[UNSUBSCRIBE] {subscriber['name']} disconnected")

        send_json(server, {
            "type": "UNSUBSCRIBE_ACK",
            "message": "Successfully unsubscribed"
        }, address)


def process_notification(server, message, address, priority):
    notification_id = str(message.get("id", ""))
    text = str(message.get("message", "")).strip()
    sender = str(message.get("sender", "Unknown"))
    ack_required = priority == "EMERGENCY"

    if not notification_id or not text:
        send_json(server, {
            "type": "ERROR",
            "message": "Notification ID and message are required"
        }, address)
        return

    with lock:
        if address not in subscribers:
            send_json(server, {
                "type": "ERROR",
                "message": "Register before sending notifications"
            }, address)
            return

        if notification_id in seen_notifications:
            duplicate = True
            recipients = []
        else:
            duplicate = False
            seen_notifications.add(notification_id)

            recipients = [
                (client_address, info["name"])
                for client_address, info in subscribers.items()
                if client_address != address
            ]

    if duplicate:
        send_json(server, {
            "type": "ACK",
            "id": notification_id,
            "message": "Duplicate notification already processed"
        }, address)
        return

    now = time.time()

    notification = {
        "type": "NOTIFICATION",
        "id": notification_id,
        "priority": priority,
        "message": text,
        "sender": sender,
        "sent_at": message.get("sent_at", now),
        "ack_required": ack_required
    }

    delivered = 0

    for client_address, name in recipients:
        if ack_required:
            key = (notification_id, client_address)

            with lock:
                pending[key] = {
                    "notification": notification,
                    "last_sent": time.monotonic(),
                    "retries": 0,
                    "name": name
                }

        try:
            send_json(server, notification, client_address)
            delivered += 1
        except OSError as error:
            print(f"[SEND ERROR] {name}: {error}")

            if ack_required:
                with lock:
                    pending.pop((notification_id, client_address), None)

    print(
        f"[{priority}] ID={notification_id} "
        f"from={sender} recipients={delivered}"
    )

    send_json(server, {
        "type": "ACK",
        "id": notification_id,
        "message": "Notification accepted by server",
        "recipient_count": delivered,
        "server_ack_time": time.time()
    }, address)


def process_delivery_ack(message, address):
    notification_id = str(message.get("id", ""))
    key = (notification_id, address)

    with lock:
        item = pending.pop(key, None)

        subscriber = subscribers.get(address)

    if item:
        elapsed_ms = (
            time.monotonic() - item["last_sent"]
        ) * 1000

        name = subscriber["name"] if subscriber else str(address)

        print(
            f"[DELIVERY ACK] ID={notification_id} "
            f"from={name} delay={elapsed_ms:.2f} ms"
        )


def retry_unacknowledged(emergency_server):
    while True:
        time.sleep(0.02)
        now = time.monotonic()

        with lock:
            expired = [
                (key, value)
                for key, value in pending.items()
                if now - value["last_sent"] >= ACK_TIMEOUT
            ]

        for key, item in expired:
            notification_id, address = key

            with lock:
                current = pending.get(key)

                if current is not item:
                    continue

                if item["retries"] >= MAX_RETRIES:
                    pending.pop(key, None)
                    subscribers.pop(address, None)

                    print(
                        f"[DELIVERY FAILED] ID={notification_id} "
                        f"subscriber={item['name']} removed"
                    )
                    continue

                item["retries"] += 1
                item["last_sent"] = time.monotonic()
                retry_number = item["retries"]

            try:
                send_json(
                    emergency_server,
                    item["notification"],
                    address
                )

                print(
                    f"[RETRY {retry_number}] "
                    f"ID={notification_id} to={item['name']}"
                )

            except OSError as error:
                print(f"[RETRY ERROR] {item['name']}: {error}")


def process_message(server, data, address, port):
    try:
        message = json.loads(data.decode("utf-8"))

        if not isinstance(message, dict):
            raise ValueError("Expected a JSON object")

        message_type = message.get("type")

        if message_type == "REGISTER":
            if port != NORMAL_PORT:
                raise ValueError("Registration must use normal port")
            register_subscriber(server, message, address)

        elif message_type == "UNSUBSCRIBE":
            unsubscribe_subscriber(server, address)

        elif message_type == "NOTIFY":
            priority = str(message.get("priority", "NORMAL")).upper()

            if priority not in ("NORMAL", "EMERGENCY"):
                raise ValueError("Invalid notification priority")

            expected_port = (
                EMERGENCY_PORT
                if priority == "EMERGENCY"
                else NORMAL_PORT
            )

            if port != expected_port:
                raise ValueError("Notification sent to incorrect port")

            process_notification(server, message, address, priority)

        elif message_type == "DELIVERY_ACK":
            process_delivery_ack(message, address)

        else:
            raise ValueError("Unknown message type")

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        print(f"[INVALID MESSAGE] {address}: {error}")

        try:
            send_json(server, {
                "type": "ERROR",
                "message": str(error)
            }, address)
        except OSError:
            pass


def receive_loop(server, port):
    while True:
        try:
            data, address = server.recvfrom(BUFFER_SIZE)
            process_message(server, data, address, port)

        except OSError as error:
            print(f"[RECEIVE ERROR] Port {port}: {error}")
            break


def main():
    normal_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    emergency_server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        normal_server.bind((HOST, NORMAL_PORT))
        emergency_server.bind((HOST, EMERGENCY_PORT))

        emergency_server.setsockopt(
            socket.IPPROTO_IP,
            socket.IP_TOS,
            DSCP_EF
        )

        print("Emergency Notification Server started")
        print(f"Normal traffic: UDP {NORMAL_PORT}")
        print(f"Emergency traffic: UDP {EMERGENCY_PORT}")
        print("Emergency DSCP: 46")

        threading.Thread(
            target=retry_unacknowledged,
            args=(emergency_server,),
            daemon=True
        ).start()

        threading.Thread(
            target=receive_loop,
            args=(normal_server, NORMAL_PORT),
            daemon=True
        ).start()

        threading.Thread(
            target=receive_loop,
            args=(emergency_server, EMERGENCY_PORT),
            daemon=True
        ).start()

        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\nServer shutting down.")

    except OSError as error:
        print(f"[SERVER ERROR] {error}")

    finally:
        normal_server.close()
        emergency_server.close()


if __name__ == "__main__":
    main()
