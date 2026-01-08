from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
import os

# --- CONEXIÓN A BASE DE DATOS REAL ---
try:
    from upstash_redis import Redis
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    
    if url and token:
        redis = Redis(url=url, token=token)
        HAS_DB = True
    else:
        HAS_DB = False
except Exception:
    HAS_DB = False

# Fallback si la DB no responde
NODOS_DB_FALLBACK = {"NODO_MAESTRO": {"name": "Neo", "expiry": "2099-12-31", "status": "OK"}}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        # 1. ACCIONES (BOTONES ACTIVAR/PURGAR)
        if parsed_path.path == '/api/action':
            node_id = params.get('id', [None])[0]
            new_status = params.get('status', [None])[0]
            if HAS_DB and node_id and new_status:
                data = redis.get(f"node:{node_id}")
                if data:
                    data['status'] = new_status
                    redis.set(f"node:{node_id}", data)
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # 2. ENDPOINT PARA EL EXE (Handshake)
        if parsed_path.path == '/api/status':
            node_id = params.get('id', [None])[0]
            if not node_id:
                res = {"status": "ERROR"}
            elif HAS_DB:
                data = redis.get(f"node:{node_id}")
                if not data:
                    data = {"name": f"PC_{node_id[:6]}", "expiry": "PENDIENTE", "status": "LOCKED"}
                    redis.set(f"node:{node_id}", data)
                res = data
            else:
                res = NODOS_DB_FALLBACK.get(node_id, {"status": "LOCKED"})

            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
            return

        # 3. PANEL DE CONTROL (Interfaz HTML)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        nodes = {}
        if HAS_DB:
            keys = redis.keys("node:*")
            for k in keys:
                nodes[k.replace("node:", "")] = redis.get(k)
        
        if not nodes:
            nodes = NODOS_DB_FALLBACK

        rows = ""
        for nid, d in nodes.items():
            s_col = {"OK":"text-green-500","LOCKED":"text-blue-400","PURGE":"text-red-500"}.get(d['status'], "text-white")
            rows += f"""
            <tr class="border-b border-zinc-800 hover:bg-zinc-800/50">
                <td class="p-4 text-xs font-mono text-zinc-500">{nid}</td>
                <td class="p-4 text-white font-bold">{d['name']}</td>
                <td class="p-4">{d['expiry']}</td>
                <td class="p-4 font-bold {s_col}">{d['status']}</td>
                <td class="p-4 flex gap-2">
                    <a href="/api/action?id={nid}&status=OK" class="bg-green-900/30 text-green-400 px-2 py-1 rounded text-[10px] border border-green-800 font-bold">ACTIVAR</a>
                    <a href="/api/action?id={nid}&status=PURGE" class="bg-red-900/30 text-red-400 px-2 py-1 rounded text-[10px] border border-red-800 font-bold">PURGAR</a>
                </td>
            </tr>"""

        html = f"""
        <!DOCTYPE html>
        <html lang="es">
        <head>
            <meta charset="UTF-8">
            <title>AETERNUM | HQ</title>
            <script src="https://cdn.tailwindcss.com"></script>
            <style>
                body {{ background: #050505; color: #D4AF37; font-family: monospace; }}
                .matrix-border {{ border: 1px solid #D4AF37; box-shadow: 0 0 20px rgba(212, 175, 55, 0.2); }}
            </style>
        </head>
        <body class="p-10">
            <div class="max-w-5xl mx-auto">
                <header class="flex justify-between items-center mb-10 border-b border-zinc-800 pb-5">
                    <div>
                        <h1 class="text-2xl font-bold tracking-[0.2em]">AETERNUM COMMAND</h1>
                        <p class="text-zinc-500 text-xs">DB: <span class="{'text-green-500' if HAS_DB else 'text-red-500'}">{'ONLINE' if HAS_DB else 'OFFLINE'}</span></p>
                    </div>
                </header>
                <div class="matrix-border bg-zinc-900/50 rounded-xl overflow-hidden">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="bg-zinc-800/30 text-zinc-400 text-xs uppercase">
                                <th class="p-4">HWID</th><th class="p-4">USUARIO</th><th class="p-4">CADUCIDAD</th><th class="p-4">SITUACIÓN</th><th class="p-4">ACCIONES</th>
                            </tr>
                        </thead>
                        <tbody>{rows}</tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>"""
        self.wfile.write(html.encode('utf-8'))