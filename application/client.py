
import socket
import json
import time
import uuid
import threading
import os

SERVER_HOST = os.environ.get("SERVER_HOST", "127.0.0.1")
SERVER_PORT = 5000
BUFFER_SIZE = 4096
ACK_TIMEOUT = 2.0
MAX_RETRIES = 3

client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
client.settimeout(0.5)

running = True
name = "Anonymous"
seen_notifications = set()
pending_sends = {}
lock = threading.Lock()


def send_json(message):
    data = json.dumps(message).encode("utf-8")
    client.sendto(data, (SERVER_HOST, SERVER_PORT))


def send_notification(priority, text):
    notification_id = str(uuid.uuid4())

    message = {
        "type": "NOTIFY",
        "id": notification_id,
        "priority": priority,
        "message": text,
        "sender": name,
        "sent_at": time.time()
    }

    with lock:
        pending_sends[notification_id] = {
            "message": message,
            "last_sent": time.monotonic(),
            "retries": 0
        }

    try:
        send_json(message)
        print(f"[SENT] {priority} notification ID={notification_id}")
    except OSError as error:
        print(f"[SEND ERROR] {error}")


def retry_unacknowledged():
    while running:
        time.sleep(0.2)
        now = time.monotonic()

        with lock:
            expired = [
                (notification_id, item)
                for notification_id, item in pending_sends.items()
                if now - item["last_sent"] >= ACK_TIMEOUT
            ]

        for notification_id, item in expired:
            with lock:
                current = pending_sends.get(notification_id)

                if current is not item:
                    continue

                if item["retries"] >= MAX_RETRIES:
                    pending_sends.pop(notification_id, None)
                    print(
                        f"[ACK TIMEOUT] No server acknowledgement for "
                        f"{notification_id}"
                    )
                    continue

                item["retries"] += 1
                item["last_sent"] = time.monotonic()
                retry_number = item["retries"]

            try:
                send_json(item["message"])
                print(
                    f"[RETRY {retry_number}] Notification "
                    f"{notification_id}"
                )
            except OSError as error:
                print(f"[RETRY ERROR] {error}")


def receive_messages():
    global running

    while running:
        try:
            data, address = client.recvfrom(BUFFER_SIZE)
            response = json.loads(data.decode("utf-8"))

            if not isinstance(response, dict):
                continue

            message_type = response.get("type")

            if message_type == "REGISTER_ACK":
                print("[SUCCESS] Subscriber registered.")

            elif message_type == "NOTIFICATION":
                notification_id = str(response.get("id", ""))
                received_at = time.time()

                with lock:
                    is_duplicate = notification_id in seen_notifications
                    seen_notifications.add(notification_id)

                if not is_duplicate:
                    print("\n========== NOTIFICATION ==========")
                    print("Priority:", response.get("priority"))
                    print("From:", response.get("sender"))
                    print("Message:", response.get("message"))
                    print("ID:", notification_id)

                    sent_at = response.get("sent_at")

                    if isinstance(sent_at, (int, float)):
                        latency_ms = (received_at - sent_at) * 1000
                        print(
                            f"Approximate end-to-end latency: "
                            f"{latency_ms:.2f} ms"
                        )

                    print("==================================")
                else:
                    print(f"[DUPLICATE] ID={notification_id} ignored.")

                try:
                    send_json({
                        "type": "DELIVERY_ACK",
                        "id": notification_id,
                        "received_at": received_at
                    })
                except OSError as error:
                    print(f"[ACK SEND ERROR] {error}")

            elif message_type == "ACK":
                notification_id = str(response.get("id", ""))

                with lock:
                    pending_sends.pop(notification_id, None)

                print(
                    f"[SERVER ACK] {response.get('message')} "
                    f"(recipients: {response.get('recipient_count', 0)})"
                )

            elif message_type == "ERROR":
                print("[SERVER ERROR]", response.get("message"))

        except socket.timeout:
            continue

        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
            if running:
                print(f"[RECEIVE ERROR] {error}")
            break


def main():
    global running, name

    name = input("Enter your subscriber name: ").strip() or "Anonymous"

    threading.Thread(target=receive_messages, daemon=True).start()
    threading.Thread(target=retry_unacknowledged, daemon=True).start()

    try:
        send_json({
            "type": "REGISTER",
            "name": name
        })

        while True:
            print("\n========== EMERGENCY NOTIFICATION CLIENT ==========")
            print("1. Send normal notification")
            print("2. Send emergency notification")
            print("3. Exit")

            choice = input("Choose an option: ").strip()

            if choice == "3":
                break

            if choice not in ("1", "2"):
                print("Choose 1, 2, or 3.")
                continue

            text = input("Enter notification message: ").strip()

            if not text:
                print("Message cannot be empty.")
                continue

            priority = "EMERGENCY" if choice == "2" else "NORMAL"
            send_notification(priority, text)

    except (KeyboardInterrupt, OSError):
        print("\nClient interrupted or network unavailable.")

    finally:
        running = False
        client.close()
        print("Client closed.")


if __name__ == "__main__":
    main()

