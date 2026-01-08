from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
import os

# --- CONEXIÓN A UPSTASH REDIS ---
try:
    from upstash_redis import Redis
    # Priorizamos las variables de entorno configuradas en el panel de Vercel
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

    if url and token:
        redis = Redis(url=url, token=token)
        HAS_DB = True
    else:
        # Intento de respaldo automático
        redis = Redis.from_env()
        HAS_DB = True
except Exception as e:
    print(f"Error de conexión Redis: {e}")
    HAS_DB = False

# Datos de respaldo por si la DB está offline
NODOS_DB_FALLBACK = {"NODO_MAESTRO": {"name": "Neo (Modo Offline)", "expiry": "2099-12-31", "status": "OK"}}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        # --- 1. ACCIONES (ACTIVAR / PURGAR) ---
        if parsed_path.path == '/api/action':
            node_id = params.get('id', [None])[0]
            new_status = params.get('status', [None])[0]
            if HAS_DB and node_id and new_status:
                try:
                    data = redis.get(f"node:{node_id}")
                    if data:
                        data['status'] = new_status
                        redis.set(f"node:{node_id}", data)
                except Exception:
                    pass
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # --- 2. HANDSHAKE (PARA EL EXE LOCAL) ---
        if parsed_path.path == '/api/status':
            node_id = params.get('id', [None])[0]
            res = {"status": "LOCKED"} # Por defecto

            if not node_id:
                res = {"status": "ERROR"}
            elif HAS_DB:
                try:
                    data = redis.get(f"node:{node_id}")
                    if not data:
                        # Auto-registro al detectar nueva PC
                        data = {"name": f"PC_{node_id[:5]}", "expiry": "PENDIENTE", "status": "LOCKED"}
                        redis.set(f"node:{node_id}", data)
                    res = data
                except Exception:
                    res = {"status": "DB_ERROR"}
            else:
                res = NODOS_DB_FALLBACK.get(node_id, {"status": "LOCKED"})

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode('utf-8'))
            return

        # --- 3. DASHBOARD (INTERFAZ VISUAL) ---
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        nodes = {}
        if HAS_DB:
            try:
                keys = redis.keys("node:*")
                if keys:
                    for k in keys:
                        # Limpiamos el prefijo de la key para mostrar el ID
                        clean_id = k.replace("node:", "")
                        nodes[clean_id] = redis.get(k)
            except Exception as e:
                print(f"Error recuperando nodos: {e}")

        # Si no hay conexión o no hay datos, usamos el fallback
        if not nodes:
            nodes = NODOS_DB_FALLBACK

        rows = ""
        for nid, d in nodes.items():
            status = d.get('status', 'LOCKED')
            s_col = {"OK":"text-green-500","LOCKED":"text-blue-400","PURGE":"text-red-500"}.get(status, "text-white")
            
            rows += f"""
            <tr class="border-b border-zinc-800 hover:bg-zinc-800/30 transition">
                <td class="p-4 text-xs font-mono text-zinc-500">{nid}</td>
                <td class="p-4 text-white font-bold">{d.get('name', '---')}</td>
                <td class="p-4">{d.get('expiry', '---')}</td>
                <td class="p-4 font-bold {s_col}">{status}</td>
                <td class="p-4 flex gap-2 justify-center">
                    <a href="/api/action?id={nid}&status=OK" class="bg-green-900/30 text-green-400 px-2 py-1 rounded text-[10px] border border-green-800 font-bold hover:bg-green-500 hover:text-white">ACTIVAR</a>
                    <a href="/api/action?id={nid}&status=PURGE" class="bg-red-900/30 text-red-400 px-2 py-1 rounded text-[10px] border border-red-800 font-bold hover:bg-red-500 hover:text-white">PURGAR</a>
                </td>
            </tr>"""

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
                        <p>ESTADO DEL NÚCLEO: <span class="text-white font-bold">ACTIVO</span></p>
                        <p>DB: <span class="{'text-green-500' if HAS_DB else 'text-red-500'} font-bold">{'ONLINE' if HAS_DB else 'OFFLINE'}</span></p>
                    </div>
                </header>
                <div class="matrix-border bg-zinc-900/50 rounded-xl overflow-hidden">
                    <table class="w-full text-left">
                        <thead class="bg-zinc-800/30 text-zinc-400 text-[10px] uppercase">
                            <tr>
                                <th class="p-4">HWID</th>
                                <th class="p-4">USUARIO</th>
                                <th class="p-4">CADUCIDAD</th>
                                <th class="p-4">SITUACIÓN</th>
                                <th class="p-4 text-center">GESTIÓN</th>
                            </tr>
                        </thead>
                        <tbody class="text-sm">{rows}</tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>"""
        
        self.wfile.write(html.encode('utf-8'))