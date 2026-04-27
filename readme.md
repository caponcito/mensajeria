# MensajeríaSD 📡

Sistema de mensajería punto a punto con arquitectura distribuida, desarrollado como proyecto del curso de **Sistemas Distribuidos — UIS 2026-1**.

## Descripción

Nodo de mensajería P2P que permite la comunicación entre múltiples instancias usando TCP y UDP, con un dashboard web para gestión de peers y visualización del historial de mensajes. Implementa **Relojes de Lamport** para ordenamiento causal de eventos en el sistema distribuido.

## Características

- Comunicación **TCP** (confiable, con ACK) y **UDP** (sin conexión)
- **Registro de peers con dos puertos** — un puerto TCP y uno UDP por peer
- **Selección automática de puerto** según el protocolo elegido en el dashboard
- **Broadcast** concurrente a todos los peers usando threads
- **Relojes de Lamport** para ordenamiento lógico de mensajes
- **Persistencia con SQLite** — el historial sobrevive reinicios
- **Dashboard web** con actualización automática cada 3 segundos
- API REST construida con **FastAPI**

## Estructura del proyecto

```
mensajeria/
├── main.py              # Punto de entrada — inicia listeners y servidor API
├── messaging_node.py    # Lógica de red (TCP/UDP) y base de datos
├── api_server.py        # Endpoints FastAPI y dashboard web
├── heartbeat_monitor.py # Monitor independiente de nodos caídos (UDP)
├── templates/
│   └── index.html       # Dashboard (Tailwind + DaisyUI)
├── peers.json           # Registro persistente de peers
├── mensajeria.db        # Base de datos SQLite (generada automáticamente)
└── requirements.txt
```

## Requisitos

- Python 3.10+
- FastAPI
- Jinja2
- Uvicorn

```bash
pip install -r requirements.txt
```

## Uso

### Iniciar el nodo

```bash
python main.py
```

Esto levanta tres servicios simultáneamente:

| Servicio | Puerto por defecto |
|---|---|
| TCP listener | 5001 |
| UDP listener | 5002 |
| API / Dashboard | 5003 |

Abre el dashboard en: `http://localhost:5003`

### Monitor de heartbeats (opcional)

El monitor detecta nodos caídos si dejan de enviar heartbeats por más de 5 segundos. Se ejecuta como proceso independiente:

```bash
python heartbeat_monitor.py
```

### Configuración de puertos

Edita las constantes en `main.py`:

```python
TCP_PORT = 5001
UDP_PORT = 5002
API_PORT = 5003
```

### Endpoints disponibles

| Método | Endpoint | Descripción |
|---|---|---|
| `GET` | `/` | Dashboard web |
| `GET` | `/mensajes` | Listar mensajes (`?protocol=TCP&sender=nombre`) |
| `GET` | `/peers` | Listar peers registrados |
| `POST` | `/peers` | Registrar peer (`?name=&ip=&tcp_port=&udp_port=`) |
| `DELETE` | `/peers/{name}` | Eliminar peer |
| `POST` | `/enviar/tcp/peer` | Enviar mensaje TCP por nombre de peer |
| `POST` | `/enviar/udp/peer` | Enviar mensaje UDP por nombre de peer |
| `POST` | `/enviar/broadcast` | Enviar a todos los peers (`?protocol=tcp\|udp`) |

La documentación interactiva de la API está disponible en `http://localhost:5003/docs`.

## Comunicación entre nodos

Para que dos nodos se comuniquen deben estar en la misma red. Cada uno registra al otro como peer indicando su IP y **ambos puertos** (TCP y UDP).

```
Nodo A (192.168.1.10)          Nodo B (192.168.1.11)
python main.py                  python main.py

Registra a B como peer:         Registra a A como peer:
  nombre:    nodo-b               nombre:    nodo-a
  ip:        192.168.1.11         ip:        192.168.1.10
  Puerto TCP: 5001                Puerto TCP: 5001
  Puerto UDP: 5002                Puerto UDP: 5002
```

El dashboard muestra el indicador **"Puerto activo"** que cambia automáticamente al seleccionar TCP o UDP antes de enviar.

> ⚠️ Si tienes un `peers.json` de una versión anterior (con un solo campo `port`), elimínalo antes de arrancar. Los peers deben volver a registrarse con el nuevo formato de dos puertos.

## Relojes de Lamport

Cada mensaje incluye un timestamp lógico (`lclock`) que se actualiza siguiendo las reglas de Lamport:

- **Evento local** (envío): `lclock = lclock + 1`
- **Evento de recepción**: `lclock = max(lclock_local, lclock_recibido) + 1`

El valor LC se muestra en el dashboard para cada mensaje.

## Tecnologías

- `socket` — comunicación TCP/UDP de bajo nivel
- `threading` — concurrencia para listeners y broadcast
- `sqlite3` — persistencia del historial de mensajes
- `FastAPI` — API REST y servidor web
- `Tailwind CSS` + `DaisyUI` — interfaz del dashboard

---

Taller de Sistemas Distribuidos · Universidad Industrial de Santander · 2026-1