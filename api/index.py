from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
import os

# --- CONEXIÓN ROBUSTA A UPSTASH ---
try:
    from upstash_redis import Redis
    
    # Intentamos leer manualmente las variables para evitar fallos de entorno
    up_url = os.environ.get("UPSTASH_REDIS_REST_URL")
    up_token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

    if up_url and up_token:
        # Forzamos la conexión con parámetros explícitos
        redis = Redis(url=up_url, token=up_token)
        HAS_DB = True
    else:
        # Intento de respaldo por si están configuradas pero no leídas
        redis = Redis.from_env()
        HAS_DB = True
except Exception as e:
    print(f"CRITICAL: Error conectando a Redis: {e}")
    HAS_DB = False

# Fallback por si la DB está caída o mal configurada
NODOS_DB_FALLBACK = {"NODO_MAESTRO": {"name": "Neo", "expiry": "2099-12-31", "status": "OK"}}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        # --- 1. ACCIONES (BOTONES ACTIVAR/PURGAR) ---
        if parsed_path.path == '/api/action':
            node_id = params.get('id', [None])[0]
            new_status = params.get('status', [None])[0]
            if HAS_DB and node_id and new_status:
                try:
                    data = redis.get(f"node:{node_id}")
                    if data:
                        data['status'] = new_status
                        redis.set(f"node:{node_id}", data)
                except:
                    pass
            
            # Redirigir de vuelta al dashboard tras la acción
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # --- 2. HANDSHAKE (PARA EL EXE LOCAL) ---
        if parsed_path.path == '/api/status':
            node_id = params.get('id', [None])[0]
            res = {"status": "LOCKED"} # Estado por defecto por seguridad

            if not node_id:
                res = {"status": "ERROR"}
            elif HAS_DB:
                try:
                    data = redis.get(f"node:{node_id}")
                    if not data:
                        # Auto-registro de nueva PC que abre el EXE
                        data = {"name": f"PC_{node_id[:5]}", "expiry": "PENDIENTE", "status": "LOCKED"}
                        redis.set(f"node:{node_id}", data)
                    res = data
                except:
                    res = {"status": "DB_ERROR"}
            else:
                res = NODOS_DB_FALLBACK.get(node_id, {"status": "LOCKED"})

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
            return

        # --- 3. DASHBOARD (INTERFAZ VISUAL) ---
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        nodes = {}
        if HAS_DB:
            try:
                keys = redis.keys("node:*")
                for k in keys:
                    val = redis.get(k)
                    # Limpiamos el nombre de la key para el ID
                    nodes[k.replace("node:", "")] = val
            except Exception as e:
                print(f"Error recuperando nodos: {e}")

        # Si la DB está vacía u offline, mostrar el fallback
        if not nodes:
            nodes = NODOS_DB_FALLBACK

        rows = ""
        for nid, d in nodes.items():
            # Colores según situación
            s_col = {
                "OK": "text-green-500",
                "LOCKED": "text-blue-400",
                "PURGE": "text-red-500"
            }.get(d.get('status'), "text-white")

            rows += f"""
            <tr class="border-b border-zinc-800 hover:bg-zinc-800/30">
                <td class="p-4 text-xs font-mono text-zinc-500">{nid}</td>
                <td class="p-4 text-white font-bold">{d.get('name', 'N/A')}</td>
                <td class="p-4">{d.get('expiry', '---')}</td>
                <td class="p-4 font-bold {s_col}">{d.get('status', '???')}</td>
                <td class="p-4 flex gap-2 justify-center">
                    <a href="/api/action?id={nid}&status=OK" class="bg-green-900/30 text-green-400 px-2 py-1 rounded text-[10px] border border-green-800 font-bold hover:bg-green-600 hover:text-white transition">ACTIVAR</a>
                    <a href="/api/action?id={nid}&status=PURGE" class="bg-red-900/30 text-red-400 px-2 py-1 rounded text-[10px] border border-red-800 font-bold hover:bg-red-600 hover:text-white transition">PURGAR</a>
                </td>
            </tr>"""

        db_status_color = "text-green-500" if HAS_DB else "text-red-500"
        db_status_text = "ONLINE" if HAS_DB else "OFFLINE"

        html = f"""<!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AETERNUM | HQ</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body {{ background: #050505; color: #D4AF37; font-family: monospace; }}
                .matrix-border {{ border: 1px solid #D4AF37; box-shadow: 0 0 20px rgba(212,175,55,0.2); }}
            </style>
        </head>
        <body class="p-4 md:p-10">
            <div class="max-w-5xl mx-auto">
                <header class="flex justify-between items-center mb-10 border-b border-zinc-800 pb-5">
                    <div>
                        <h1 class="text-2xl font-bold tracking-[0.2em]">AETERNUM COMMAND</h1>
                        <p class="text-zinc-500 text-[10px] uppercase">Central de Licenciamiento</p>
                    </div>
                    <div class="text-right text-xs">
                        <p>SISTEMA: <span class="text-white font-bold">ACTIVO</span></p>
                        <p>DB: <span class="{db_status_color} font-bold">{db_status_text}</span></p>
                    </div>
                </header>
                <div class="matrix-border bg-zinc-900/50 rounded-xl overflow-hidden">
                    <table class="w-full text-left">
                        <thead class="bg-zinc-800/30 text-zinc-400 text-[10px] uppercase">
                            <tr>
                                <th class="p-4">HWID (Identificador Único)</th>
                                <th class="p-4">USUARIO</th>
                                <th class="p-4">CADUCIDAD</th>
                                <th class="p-4">SITUACIÓN</th>
                                <th class="p-4 text-center">GESTIÓN</th>
                            </tr>
                        </thead>
                        <tbody class="text-sm">{rows}</tbody>
                    </table>
                </div>
                <footer class="mt-10 text-center text-zinc-600 text-[10px]">
                    SISTEMA DE CONTROL PROPIETARIO - AETERNUM OMEGA v2.0
                </footer>
            </div>
        </body>
        </html>"""
        
        self.wfile.write(html.encode('utf-8'))