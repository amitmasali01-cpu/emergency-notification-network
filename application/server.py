
import socket
import json
import time
import uuid
import threading

HOST = "0.0.0.0"
PORT = 5000
BUFFER_SIZE = 4096

ACK_TIMEOUT = 2.0
MAX_RETRIES = 3

subscribers = {}
pending = {}
seen_notifications = {}
lock = threading.Lock()


def send_json(server, message, address):
    data = json.dumps(message).encode("utf-8")
    server.sendto(data, address)


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


def process_notification(server, message, address):
    notification_id = str(message.get("id", ""))
    priority = str(message.get("priority", "NORMAL")).upper()
    text = str(message.get("message", "")).strip()
    sender = str(message.get("sender", "Unknown"))

    if not notification_id or not text:
        send_json(server, {
            "type": "ERROR",
            "message": "Notification ID and message are required"
        }, address)
        return

    if priority not in ("NORMAL", "EMERGENCY"):
        send_json(server, {
            "type": "ERROR",
            "message": "Priority must be NORMAL or EMERGENCY"
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
        "server_received_at": now
    }

    with lock:
        if notification_id in seen_notifications:
            duplicate = True
            recipients = []
        else:
            duplicate = False
            seen_notifications[notification_id] = now
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

    for client_address, name in recipients:
        try:
            send_json(server, notification, client_address)

            with lock:
                pending[(notification_id, client_address)] = {
                    "notification": notification,
                    "last_sent": time.monotonic(),
                    "retries": 0,
                    "name": name
                }

        except OSError as error:
            print(f"[SEND ERROR] {name}: {error}")

    print(
        f"[{priority}] ID={notification_id} "
        f"from={sender} recipients={len(recipients)}"
    )

    send_json(server, {
        "type": "ACK",
        "id": notification_id,
        "message": "Notification accepted by server",
        "recipient_count": len(recipients),
        "server_ack_time": time.time()
    }, address)


def process_delivery_ack(message, address):
    notification_id = str(message.get("id", ""))

    with lock:
        item = pending.pop((notification_id, address), None)
        subscriber = subscribers.get(address)

    if item:
        elapsed_ms = (
            time.monotonic() - item["last_sent"]
        ) * 1000

        name = subscriber["name"] if subscriber else str(address)
        print(
            f"[DELIVERY ACK] ID={notification_id} "
            f"from={name} acknowledgement_delay={elapsed_ms:.2f} ms"
        )


def retry_unacknowledged(server):
    while True:
        time.sleep(0.2)
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
                    print(
                        f"[DELIVERY FAILED] ID={notification_id} "
                        f"subscriber={item['name']}"
                    )
                    continue

                item["retries"] += 1
                item["last_sent"] = time.monotonic()
                retry_number = item["retries"]

            try:
                send_json(server, item["notification"], address)
                print(
                    f"[RETRY {retry_number}] ID={notification_id} "
                    f"to={item['name']}"
                )
            except OSError as error:
                print(f"[RETRY ERROR] {item['name']}: {error}")


def process_message(server, data, address):
    try:
        message = json.loads(data.decode("utf-8"))

        if not isinstance(message, dict):
            raise ValueError("Expected a JSON object")

        message_type = message.get("type")

        if message_type == "REGISTER":
            register_subscriber(server, message, address)

        elif message_type == "NOTIFY":
            process_notification(server, message, address)

        elif message_type == "DELIVERY_ACK":
            process_delivery_ack(message, address)

        else:
            send_json(server, {
                "type": "ERROR",
                "message": "Unknown message type"
            }, address)

    except (json.JSONDecodeError, UnicodeDecodeError, ValueError) as error:
        print(f"[INVALID MESSAGE] {address}: {error}")

        try:
            send_json(server, {
                "type": "ERROR",
                "message": "Invalid message format"
            }, address)
        except OSError:
            pass


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        server.bind((HOST, PORT))
        threading.Thread(
            target=retry_unacknowledged,
            args=(server,),
            daemon=True
        ).start()

        print(f"Emergency Notification Server listening on UDP {PORT}")

        while True:
            data, address = server.recvfrom(BUFFER_SIZE)
            process_message(server, data, address)

    except KeyboardInterrupt:
        print("\nServer shutting down.")

    except OSError as error:
        print(f"[SERVER ERROR] {error}")

    finally:
        server.close()


if __name__ == "__main__":
    main()

