"""
messaging_node.py - Nodo de mensajería punto a punto
Taller de Sistemas Distribuidos - UIS 2026-1
"""

import socket, time
import threading
import json
from datetime import datetime
import sqlite3

lclock = 0
lclock_lock = threading.Lock()


def tick():
    """Evento local — incrementa el reloj"""
    global lclock
    with lclock_lock:
        lclock += 1
        return lclock


def update(received_clock):
    """Evento de recepción — aplica regla de Lamport"""
    global lclock
    with lclock_lock:
        lclock = max(lclock, received_clock) + 1
        return lclock


def con_db():
    con = sqlite3.connect("mensajeria.db", check_same_thread=False)
    con.row_factory = sqlite3.Row
    cur = con.cursor()
    return con, cur


def init_db():
    con, cur = con_db()
    cur.execute(
        "CREATE TABLE if not exists mensajes(timestamp, sender, content, protocol, lclock)"
    )
    con.close()


def save_message(sender: str, content: str, protocol: str, lclock: int):
    """Almacena un mensaje recibido con metadatos."""
    con, cur = con_db()
    with con:
        cur.execute(
            f"""INSERT INTO mensajes VALUES(?,?,?,?,?)""",
            (datetime.now().isoformat(), sender, content, protocol, lclock),
        )
    con.close()


def tcp_listener(host: str, port: int):
    """
    Servidor TCP, crea una conexion TCP se queda escuchando puertos
    y crea un hilo por cada conexion
    """
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conexion.bind((host, port))
    conexion.listen()
    while True:
        conn, addr = conexion.accept()
        thread = threading.Thread(target=manejar_cliente, args=(conn, addr))
        thread.start()


def manejar_cliente(conn, addr):
    """Recibe el mensaje de maximo 4096 bytes y envia un ack de confirmacion"""
    global lclock
    datos = conn.recv(4096)
    mensaje = json.loads(datos)

    lclock = update(mensaje["lclock"])

    save_message(addr[0], mensaje["content"], "TCP", lclock)
    ack = json.dumps({"status": "ok"})
    conn.sendall(ack.encode())
    conn.close()


def send_tcp_message(peer_ip: str, peer_port: int, sender_name: str, message: str):
    """
    Envío de mensajes TCP:
    - Crea un socket TCP y se conecta a (peer_ip, peer_port)
    - Construye un dict con "sender", "content" y "lclock"
    - Serializa a JSON y envía los bytes
    - Recibe y muestra el ACK
    - Maneja excepciones (ConnectionRefusedError, timeout)
    """
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        conexion.connect((peer_ip, peer_port))
        clock = tick()  # incrementa el reloj antes de enviar
        msg = json.dumps({"sender": sender_name, "content": message, "lclock": clock})
        conexion.sendall(msg.encode())
        ack = conexion.recv(4096)
        print(json.loads(ack))
    except ConnectionRefusedError:
        print("No se pudo conectar al servidor")
    except socket.timeout:
        print("El servidor ha tomado demasiado en responder")
    finally:
        conexion.close()  # cerrar la conexion en cualquiera de los casos


def udp_listener(host: str, port: int):
    global lclock
    conexion = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conexion.bind((host, port))
    while True:
        try:
            data, addr = conexion.recvfrom(4096)
            mensaje = json.loads(data)
            with lclock_lock:
                lclock = max(lclock, mensaje["lclock"]) + 1
            save_message(addr[0], mensaje["content"], "UDP", lclock)
            print(f"[UDP] Mensaje recibido de {addr[0]}: {mensaje['content']}")
        except KeyError as e:
            print(f"[UDP] Error - clave faltante en mensaje: {e}")
        except Exception as e:
            print(f"[UDP] Error inesperado: {e}")


def send_udp_message(peer_ip: str, peer_port: int, sender_name: str, message: str):
    """
    Envío de mensajes UDP:
    - No necesita connect(), usa sendto() directamente con la IP y puerto destino
    - No espera ACK porque UDP es sin conexión
    - Si el destinatario no está disponible, el datagrama se pierde sin error
    """
    conexion = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        clock = tick()  # ← FIX: guardar el valor retornado por tick() en "clock"
        msg = json.dumps({"sender": sender_name, "content": message, "lclock": clock})
        # ← FIX: antes usaba "lclock" (global sin actualizar), ahora usa "clock" (valor local correcto)
        conexion.sendto(msg.encode(), (peer_ip, peer_port))
    finally:
        conexion.close()


"""heartbeat_sender.py — Nodo que emite heartbeats periódicos vía UDP."""

MONITOR_HOST = "127.0.0.1"
MONITOR_PORT = 5000
INTERVAL = 2.0  # Δ = 2 segundos
NODE_ID = "nodo-alpha"


def run_sender():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    seq = 0
    print(
        f"[{NODE_ID}] Enviando heartbeats cada {INTERVAL}s a {MONITOR_HOST}:{MONITOR_PORT}"
    )
    while True:
        msg = json.dumps({"node_id": NODE_ID, "seq": seq, "ts": time.time()})
        sock.sendto(msg.encode(), (MONITOR_HOST, MONITOR_PORT))
        print(f" → HB seq={seq}")
        seq += 1
        time.sleep(INTERVAL)
