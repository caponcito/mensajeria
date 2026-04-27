"""heartbeat_monitor.py — Monitorea heartbeats y detecta nodos caídos."""

import socket
import json
import time
import threading

PORT = 5000
TIMEOUT = 5.0  # T = 5s (≈ 2.5 × Δ)

last_seen: dict[str, float] = {}  # node_id → último timestamp recibido
lock = threading.Lock()


def receiver():
    """Escucha datagramas UDP y actualiza el timestamp de cada nodo."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", PORT))
    print(f"[Monitor] Escuchando heartbeats en puerto {PORT}")
    while True:
        data, addr = sock.recvfrom(1024)
        msg = json.loads(data)
        with lock:
            last_seen[msg["node_id"]] = time.time()
        print(f"  ← HB de {msg['node_id']} seq={msg['seq']}")


def checker():
    """Revisa periódicamente si algún nodo dejó de enviar heartbeats."""
    while True:
        time.sleep(TIMEOUT / 2)
        now = time.time()
        with lock:
            for node_id, ts in list(last_seen.items()):
                if now - ts > TIMEOUT:
                    print(f"⚠️  SOSPECHA: {node_id} sin heartbeat por {now - ts:.1f}s")


if __name__ == "__main__":
    threading.Thread(target=receiver, daemon=True).start()
    checker()
