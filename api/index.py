from http.server import BaseHTTPRequestHandler
import json
from urllib.parse import parse_qs, urlparse

# BASE DE DATOS VIRTUAL
# Estado inicial para desconocidos: "LOCKED" (Bloqueado hasta que tú lo apruebes)
NODOS_DB = {
    "NODO_MAESTRO": {"name": "Neo", "expiry": "2099-12-31", "status": "OK"},
}

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed_path = urlparse(self.path)
        
        # 1. ENDPOINT PARA LOS NODOS (Handshake del EXE)
        if parsed_path.path == '/api/status':
            query_params = parse_qs(parsed_path.query)
            node_id = query_params.get('id', [None])[0]
            
            if not node_id:
                response = {"status": "ERROR", "message": "No ID provided"}
            else:
                # REGISTRO AUTOMÁTICO: Si no existe, lo creamos como LOCKED
                if node_id not in NODOS_DB:
                    NODOS_DB[node_id] = {
                        "name": f"Desconocido ({node_id[:6]})", 
                        "expiry": "PENDIENTE", 
                        "status": "LOCKED"
                    }
                
                response = NODOS_DB.get(node_id)
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        # 2. PANEL DE CONTROL (Tu interfaz para móvil/PC)
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            # Generar filas de la tabla dinámicamente
            rows = ""
            for node_id, data in NODOS_DB.items():
                status_color = {
                    "OK": "text-green-500",
                    "WARNING": "text-yellow-500",
                    "LOCKED": "text-blue-400",
                    "PURGE": "text-red-500"
                }.get(data['status'], "text-white")

                rows += f"""
                <tr class="border-b border-zinc-800 hover:bg-zinc-800/50">
                    <td class="p-4 text-xs font-mono text-zinc-500">{node_id}</td>
                    <td class="p-4 text-white font-bold">{data['name']}</td>
                    <td class="p-4">{data['expiry']}</td>
                    <td class="p-4 font-bold {status_color}">{data['status']}</td>
                    <td class="p-4 flex gap-2">
                        <button class="bg-zinc-700 px-2 py-1 rounded text-xs">EDITAR</button>
                        <button class="bg-red-900/50 text-red-200 px-2 py-1 rounded text-xs border border-red-700">PURGAR</button>
                    </td>
                </tr>
                """

            html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AETERNUM | HQ</title>
                <script src="https://cdn.tailwindcss.com"></script>
                <style>
                    body {{ background: #050505; color: #D4AF37; font-family: 'Courier New', monospace; }}
                    .matrix-border {{ border: 1px solid #D4AF37; box-shadow: 0 0 20px rgba(212, 175, 55, 0.2); }}
                </style>
            </head>
            <body class="p-4 md:p-10">
                <div class="max-w-5xl mx-auto">
                    <header class="flex justify-between items-center mb-10 border-b border-zinc-800 pb-5">
                        <div>
                            <h1 class="text-2xl font-bold tracking-[0.2em]">AETERNUM COMMAND</h1>
                            <p class="text-zinc-500 text-xs">CENTRAL DE LICENCIAMIENTO SOBERANO</p>
                        </div>
                        <div class="text-right text-xs">
                            <p>STATUS: <span class="text-green-500">EN LINEA</span></p>
                            <p>ENCRIPTACIÓN: AES-256</p>
                        </div>
                    </header>

                    <div class="matrix-border bg-zinc-900/50 rounded-xl overflow-hidden">
                        <div class="bg-zinc-800/50 p-4 border-b border-zinc-700">
                            <h2 class="font-bold uppercase tracking-widest text-sm text-zinc-300 italic">Nodos Detectados en la Red</h2>
                        </div>
                        <div class="overflow-x-auto">
                            <table class="w-full text-left border-collapse">
                                <thead>
                                    <tr class="bg-zinc-800/30 text-zinc-400 text-xs uppercase">
                                        <th class="p-4">HWID</th>
                                        <th class="p-4">USUARIO</th>
                                        <th class="p-4">CADUCIDAD</th>
                                        <th class="p-4">SITUACIÓN</th>
                                        <th class="p-4">ACCIONES</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {rows}
                                </tbody>
                            </table>
                        </div>
                    </div>
                    
                    <footer class="mt-10 flex justify-between items-center text-[10px] text-zinc-600 uppercase">
                        <p>Access Level: NEO_ROOT</p>
                        <p>2026 © Aeternum Infrastructure</p>
                    </footer>
                </div>
            </body>
            </html>
            """
            self.wfile.write(html.encode())