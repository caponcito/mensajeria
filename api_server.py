"""
api_server.py - Interfaz web para consulta de mensajes
Taller de Sistemas Distribuidos - UIS 2026-1
"""

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from messaging_node import con_db, send_tcp_message, send_udp_message
import threading
import json, os
from fastapi.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")
app = FastAPI()


@app.get("/mensajes")
def get_mensajes(protocol: str | None = None, sender: str | None = None):
    """Retorna mensajes filtrados por protocolo y/o sender."""
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

        cons = "SELECT * FROM mensajes"
        if condiciones:
            cons += " WHERE " + " AND ".join(condiciones)

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


# ── Peers ────────────────────────────────────────────────────────────────────

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
def add_peer(name: str, ip: str, tcp_port: int, udp_port: int):
    """
    Registra un peer con dos puertos: uno para TCP y otro para UDP.
    Si ya existe un peer con ese nombre, lo reemplaza.
    """
    peers = load_peers()
    peers = [p for p in peers if p["name"] != name]  # evitar duplicados por nombre
    peers.append(
        {
            "name": name,
            "ip": ip,
            "tcp_port": tcp_port,  # puerto para mensajes TCP
            "udp_port": udp_port,  # puerto para mensajes UDP
        }
    )
    save_peers(peers)
    return {
        "status": "registrado",
        "peer": {"name": name, "ip": ip, "tcp_port": tcp_port, "udp_port": udp_port},
    }


@app.delete("/peers/{name}")
def remove_peer(name: str):
    peers = [p for p in load_peers() if p["name"] != name]
    save_peers(peers)
    return {"status": "eliminado"}


# ── Enviar por nombre de peer ─────────────────────────────────────────────────


@app.post("/enviar/tcp/peer")
def enviar_tcp_peer(peer_name: str, sender_name: str, message: str):
    peers = load_peers()
    peer = next((p for p in peers if p["name"] == peer_name), None)
    if not peer:
        return {"error": f"Peer '{peer_name}' no encontrado"}
    # usar tcp_port del peer registrado
    send_tcp_message(peer["ip"], peer["tcp_port"], sender_name, message)
    return {"status": "Enviado", "to": peer}


@app.post("/enviar/udp/peer")
def enviar_udp_peer(peer_name: str, sender_name: str, message: str):
    peers = load_peers()
    peer = next((p for p in peers if p["name"] == peer_name), None)
    if not peer:
        return {"error": f"Peer '{peer_name}' no encontrado"}
    # usar udp_port del peer registrado
    send_udp_message(peer["ip"], peer["udp_port"], sender_name, message)
    return {"status": "Enviado", "to": peer}


# ── Broadcast ────────────────────────────────────────────────────────────────


@app.post("/enviar/broadcast")
def broadcast(sender_name: str, message: str, protocol: str = "tcp"):
    peers = load_peers()
    resultados = []
    threads = []

    def enviar_a_peer(peer):
        """Elige el puerto correcto según el protocolo y envía."""
        try:
            if protocol == "udp":
                send_udp_message(peer["ip"], peer["udp_port"], sender_name, message)
            else:
                send_tcp_message(peer["ip"], peer["tcp_port"], sender_name, message)
            resultados.append({"peer": peer["name"], "status": "ok"})
        except ConnectionRefusedError:
            resultados.append({"peer": peer["name"], "status": "no responde"})

    for peer in peers:
        thread = threading.Thread(target=enviar_a_peer, args=(peer,))
        thread.start()
        threads.append(thread)

    for thread in threads:
        thread.join()  # esperar que terminen todos antes de retornar

    return resultados


# ── Dashboard ─────────────────────────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")
