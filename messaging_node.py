"""
messaging_node.py - Nodo de mensajería punto a punto
Taller de Sistemas Distribuidos - UIS 2026-1
"""

import socket
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
    Servidor TCP, crea una conexion TCP se queda escuchando puertos y crea un hilo por cada conexion
    """
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    conexion.bind((host, port))
    conexion.listen()
    while True:
        conn, addr = conexion.accept()
        thread = threading.Thread(target=manejar_cliente, args=(conn, addr))
        thread.start()


def manejar_cliente(conn, addr):
    """recibe el mensaje de maximo 4096 bytes y envia un ack de confirmacion"""
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
    TODO 2: Implemente el envío de mensajes TCP que:
    - Cree un socket TCP y se conecte a (peer_ip, peer_port)
    - Construya un dict con "sender" y "content"
    - Serialice a JSON y envíe los bytes
    - Reciba y muestre el ACK
    - Maneje excepciones (ConnectionRefusedError, timeout)
    """
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        conexion.connect((peer_ip, peer_port))
        lclock = tick()
        msg = json.dumps({"sender": sender_name, "content": message, "lclock": lclock})
        conexion.sendall(msg.encode())
        ack = conexion.recv(4096)  # se envia un ack de 4096 bytes
        print(json.loads(ack))
    except ConnectionRefusedError:
        # el servidor no está corriendo
        print("No se pudo conectar al servidor")
    except socket.timeout:
        # tardó demasiado en responder
        print("El servidor a tomado demasidado en responder")
    finally:
        conexion.close()  # cerrar la conexion en cualquiera de los casos


def udp_listener(host: str, port: int):
    """
    TODO 3: Implemente el servidor UDP que:
    - Cree un socket UDP (socket.AF_INET, socket.SOCK_DGRAM)
    - Haga bind en (host, port)
    - En un bucle infinito reciba datagramas (recvfrom)
    - Decodifique el JSON y llame a save_message()
    - Observe: ¿necesita enviar ACK? ¿Por qué?
    """
    global lclock
    conexion = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    conexion.bind((host, port))
    while True:
        data, addr = conexion.recvfrom(4096)
        mensaje = json.loads(data)

        with lclock_lock:
            lclock = max(lclock, mensaje["lclock"]) + 1

        save_message(addr[0], mensaje["content"], "UDP", lclock)


def send_udp_message(peer_ip: str, peer_port: int, sender_name: str, message: str):
    """
    TODO 4: Implemente el envío de mensajes UDP.
    Compare con send_tcp_message:
    - ¿Necesita connect()? ¿O puede usar sendto()?
    - ¿Qué pasa si el destinatario no está disponible?
    """
    conexion = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        clock = tick()
        msg = json.dumps({"sender": sender_name, "content": message, "lclock": lclock})
        conexion.sendto(msg.encode(), (peer_ip, peer_port))
        # save_message(sender_name, msg, "UDP")
    finally:
        conexion.close()
