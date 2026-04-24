"""
api_server.py - Interfaz web para consulta de mensajes
Taller de Sistemas Distribuidos - UIS 2026-1
"""

from fastapi import FastAPI, Query, Request
from fastapi.responses import HTMLResponse
from messaging_node import (
    con_db,
    send_tcp_message,
    send_udp_message,
)
import threading
import sqlite3
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

templates = Jinja2Templates(directory="templates")
app = FastAPI()

TCP_PORT = 5000
UDP_PORT = 5001
HOST = "0.0.0.0"


@app.get("/mensajes")
def get_mensajes(protocol: str | None = None, sender: str | None = None):
    """
    TODO 5: Implemente el endpoint que retorne los mensajes.
    - Si se proporciona "protocol", filtre por protocolo
    - Si se proporciona "sender", filtre por remitente
    - Retorne la lista (más recientes primero)
    - Use store_lock para acceso seguro
    """
    con, cur = con_db()
    with con:
        condiciones = []
        params = []

        if protocol:
            condiciones.append("protocol = ?")
            params.append(protocol)
        if sender:
            condiciones.append("sender = ?")
            params.append(sender)

        if condiciones:
            cons = "SELECT * FROM mensajes WHERE " + " AND ".join(condiciones)
        else:
            cons = "SELECT * FROM mensajes"

        cur.execute(cons, params)
        result = [dict(row) for row in cur.fetchall()]
    con.close()

    return result


@app.post("/enviar/tcp")
def enviar_tcp(peer_ip: str, peer_port: int, sender_name: str, message: str):
    send_tcp_message(peer_ip, peer_port, sender_name, message)
    return {"status": "Enviado"}


@app.post("/enviar/udp")
def enviar_udp(peer_ip: str, peer_port: int, sender_name: str, message: str):
    send_udp_message(peer_ip, peer_port, sender_name, message)
    return {"status": "enviado"}


import json, os

PEERS_FILE = "peers.json"


def load_peers() -> list:
    if not os.path.exists(PEERS_FILE):
        return []
    with open(PEERS_FILE) as f:
        return json.load(f)


def save_peers(peers: list):
    with open(PEERS_FILE, "w") as f:
        json.dump(peers, f, indent=2)


@app.get("/peers")
def get_peers():
    return load_peers()


@app.post("/peers")
def add_peer(name: str, ip: str, port: int):
    peers = load_peers()
    # Evitar duplicados por nombre
    peers = [p for p in peers if p["name"] != name]
    peers.append({"name": name, "ip": ip, "port": port})
    save_peers(peers)
    return {"status": "registrado", "peer": {"name": name, "ip": ip, "port": port}}


@app.delete("/peers/{name}")
def remove_peer(name: str):
    peers = [p for p in load_peers() if p["name"] != name]
    save_peers(peers)
    return {"status": "eliminado"}


# Endpoint nuevo: enviar por nombre de peer
@app.post("/enviar/tcp/peer")
def enviar_tcp_peer(peer_name: str, sender_name: str, message: str):
    peers = load_peers()
    peer = next((p for p in peers if p["name"] == peer_name), None)
    if not peer:
        return {"error": f"Peer '{peer_name}' no encontrado"}
    send_tcp_message(peer["ip"], peer["port"], sender_name, message)
    return {"status": "Enviado", "to": peer}


@app.post("/enviar/udp/peer")
def enviar_udp_peer(peer_name: str, sender_name: str, message: str):
    peers = load_peers()
    peer = next((p for p in peers if p["name"] == peer_name), None)
    if not peer:
        return {"error": f"Peer '{peer_name}' no encontrado"}
    send_udp_message(peer["ip"], peer["port"], sender_name, message)
    return {"status": "Enviado", "to": peer}


@app.post("/enviar/broadcast")
def broadcast(sender_name: str, message: str, protocol: str = "tcp"):
    # 1. Por cada peer, crea un thread que llame a send_tcp/udp
    # 2. Cada thread debe guardar su resultado en `resultados`
    # 3. Inicia todos los threads
    # 4. Espera que terminen todos con .join()
    # 5. Retorna resultados
    peers = load_peers()
    resultados = []
    threads = []

    def enviar_peer_a_peer(peer):
        """funcion intermedia para enviar
        el mensaje a los peers y retornar
        si fallo o se envio correctamente"""
        try:
            send_tcp_message(
                peer["ip"], peer["port"], sender_name=sender_name, message=message
            )
            resultados.append({"status": "peer respondiendo correctamente"})
        except ConnectionRefusedError:
            resultados.append({"status": "peer no responde", "name": peer["name"]})

    for peer in peers:
        thread = threading.Thread(
            target=enviar_peer_a_peer,
            args=(peer,),
        )
        thread.start()
        threads.append(
            thread
        )  # se adjunta el hilo a la lista para esperar que termine con join
    for thread in threads:
        thread.join()  # espera que terminen todo los hilos de ejecutarse y no cada uno
    return f"<script>alert({resultados})</script>"


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
