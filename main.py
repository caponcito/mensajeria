"""
main.py - Punto de entrada del nodo de mensajería
"""

import threading
import uvicorn
from messaging_node import tcp_listener, udp_listener, init_db, run_sender

MY_HOST = "0.0.0.0"
TCP_PORT = 5001  # Puerto asignado para TCP
UDP_PORT = 5002  # Puerto asignado para UDP
API_PORT = 5003  # Puerto asignado para FastAPI
init_db()
if __name__ == "__main__":
    # Lanzar listeners en hilos daemon
    t_tcp = threading.Thread(target=tcp_listener, args=(MY_HOST, TCP_PORT), daemon=True)
    t_udp = threading.Thread(target=udp_listener, args=(MY_HOST, UDP_PORT), daemon=True)
    hilo_heartbeat = threading.Thread(target=run_sender, daemon=True)
    t_tcp.start()
    t_udp.start()
    hilo_heartbeat.start()
    print(f"[*] TCP listener en puerto {TCP_PORT}")
    print(f"[*] UDP listener en puerto {UDP_PORT}")
    print(f"[*] Iniciando API en puerto {API_PORT}")

    # TODO 7: Inicie el servidor FastAPI con uvicorn.
    uvicorn.run("api_server:app", host=MY_HOST, port=API_PORT, reload=False)
