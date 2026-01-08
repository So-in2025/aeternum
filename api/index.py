from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse
import os

# --- CONEXIÓN ---
try:
    from upstash_redis import Redis
    url = os.environ.get("UPSTASH_REDIS_REST_URL")
    token = os.environ.get("UPSTASH_REDIS_REST_TOKEN")
    redis = Redis(url=url, token=token) if url and token else None
    HAS_DB = True if redis else False
except Exception:
    HAS_DB = False
    redis = None

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        params = parse_qs(parsed_path.query)

        # 1. ACCIONES
        if parsed_path.path == '/api/action':
            node_id = params.get('id', [None])[0]
            new_status = params.get('status', [None])[0]
            if HAS_DB and node_id and new_status:
                try:
                    raw_data = redis.get(f"node:{node_id}")
                    # Si los datos vienen como string, los convertimos
                    data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                    if data:
                        data['status'] = new_status
                        redis.set(f"node:{node_id}", json.dumps(data))
                except: pass
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
            return

        # 2. HANDSHAKE PARA EL EXE
        if parsed_path.path == '/api/status':
            node_id = params.get('id', [None])[0]
            res = {"status": "LOCKED"}
            if HAS_DB and node_id:
                try:
                    raw_data = redis.get(f"node:{node_id}")
                    data = json.loads(raw_data) if isinstance(raw_data, str) else raw_data
                    if not data:
                        data = {"name": f"PC_{node_id[:6]}", "expiry": "PENDIENTE", "status": "LOCKED"}
                        redis.set(f"node:{node_id}", json.dumps(data))
                    res = data
                except: res = {"status": "ERROR_DB"}
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(res).encode())
            return

        # 3. DASHBOARD (SOLUCIÓN PANTALLA BLANCA)
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        rows = ""
        if HAS_DB:
            try:
                keys = redis.keys("node:*")
                for k in keys:
                    nid = k.replace("node:", "")
                    raw_val = redis.get(k)
                    # ESTA LÍNEA ES LA CLAVE: Maneja strings o dicts sin romperse
                    d = json.loads(raw_val) if isinstance(raw_val, str) else raw_val
                    
                    status = d.get('status', 'LOCKED')
                    s_col = {"OK":"text-green-500","LOCKED":"text-blue-400"}.get(status, "text-red-500")
                    
                    rows += f"""
                    <tr class="border-b border-zinc-800">
                        <td class="p-4 text-xs font-mono text-zinc-500">{nid[:15]}...</td>
                        <td class="p-4 text-white font-bold">{d.get('name', '???')}</td>
                        <td class="p-4">{d.get('expiry', '---')}</td>
                        <td class="p-4 font-bold {s_col}">{status}</td>
                        <td class="p-4 flex gap-2">
                            <a href="/api/action?id={nid}&status=OK" class="bg-green-900/20 text-green-400 px-2 py-1 rounded border border-green-800 text-xs">ACTIVAR</a>
                            <a href="/api/action?id={nid}&status=PURGE" class="bg-red-900/20 text-red-400 px-2 py-1 rounded border border-red-800 text-xs">PURGAR</a>
                        </td>
                    </tr>"""
            except Exception as e:
                rows = f"<tr><td colspan='5' class='p-4 text-red-500'>Error de lectura: {str(e)}</td></tr>"

        html = f"""<!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8"><title>AETERNUM | HQ</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-[#050505] text-[#D4AF37] p-10 font- some-mono">
            <div class="max-w-5xl mx-auto">
                <header class="flex justify-between items-center mb-10 border-b border-zinc-800 pb-5">
                    <h1 class="text-2xl font-bold tracking-widest">AETERNUM COMMAND</h1>
                    <div class="text-xs">DB: <span class="text-green-500">ONLINE</span></div>
                </header>
                <div class="border border-[#D4AF37]/30 bg-zinc-900/50 rounded-xl overflow-hidden">
                    <table class="w-full text-left">
                        <thead class="bg-zinc-800/50 text-zinc-400 text-xs uppercase">
                            <tr><th class="p-4">HWID</th><th class="p-4">USUARIO</th><th class="p-4">EXP</th><th class="p-4">ESTADO</th><th class="p-4">ACCION</th></tr>
                        </thead>
                        <tbody>{rows if rows else '<tr><td colspan="5" class="p-4 text-center">Esperando conexión de nodos...</td></tr>'}</tbody>
                    </table>
                </div>
            </div>
        </body>
        </html>"""
        self.wfile.write(html.encode('utf-8'))