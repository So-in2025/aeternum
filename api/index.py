from http.server import BaseHTTPRequestHandler
import json
import os

# BASE DE DATOS VIRTUAL (En una versión Pro usarías Vercel Postgres)
# Aquí registras a tus amigos: ID, Clave, Fecha de Vencimiento y Estado
NODOS_DB = {
    "CLIENTE_001": {"name": "Papa", "expiry": "2026-12-31", "status": "OK"},
    "CLIENTE_002": {"name": "Amigo_Juan", "expiry": "2025-02-15", "status": "WARNING"},
    "CLIENTE_003": {"name": "Amigo_Rata", "expiry": "2025-01-01", "status": "PURGE"},
}

PASSWORD_MAESTRA = "NEO_2026" # Cambia esto por tu contraseña

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        # 1. ENDPOINT PARA LOS NODOS (Handshake)
        if self.path.startswith('/api/status'):
            query = self.path.split('?')[-1]
            node_id = query.split('=')[-1] if '=' in query else ""
            
            node_data = NODOS_DB.get(node_id, {"status": "PURGE"}) # Si no existe, se borra
            
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(json.dumps(node_data).encode())

        # 2. PANEL DE CONTROL (Tu interfaz)
        else:
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html lang="es">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>AETERNUM | DASHBOARD</title>
                <script src="https://cdn.tailwindcss.com"></script>
                <style>
                    body {{ background: #000; color: #D4AF37; font-family: monospace; }}
                    .matrix-bg {{ border: 1px solid #D4AF37; box-shadow: 0 0 15px #D4AF3755; }}
                </style>
            </head>
            <body class="p-8">
                <h1 class="text-3xl font-bold mb-8 text-center tracking-widest">CENTRO DE COMANDO OMEGA</h1>
                <div class="max-w-4xl mx-auto matrix-bg p-6 rounded-lg bg-zinc-900">
                    <table class="w-full text-left">
                        <thead>
                            <tr class="border-b border-zinc-700">
                                <th class="p-4">ID NODO</th>
                                <th class="p-4">USUARIO</th>
                                <th class="p-4">VENCIMIENTO</th>
                                <th class="p-4">ESTADO</th>
                                <th class="p-4">ACCION</th>
                            </tr>
                        </thead>
                        <tbody>
                            {"".join([f'''
                            <tr class="border-b border-zinc-800 hover:bg-zinc-800/50">
                                <td class="p-4">{id}</td>
                                <td class="p-4 text-white">{data['name']}</td>
                                <td class="p-4">{data['expiry']}</td>
                                <td class="p-4 font-bold {'text-green-500' if data['status'] == 'OK' else 'text-yellow-500' if data['status'] == 'WARNING' else 'text-red-500'}">{data['status']}</td>
                                <td class="p-4">
                                    <button class="bg-red-900 text-white px-3 py-1 text-xs rounded hover:bg-red-600 transition">PURGAR</button>
                                </td>
                            </tr>
                            ''' for id, data in NODOS_DB.items()])}
                        </tbody>
                    </table>
                </div>
                <p class="text-center mt-8 text-zinc-500 text-xs">SISTEMA DE SOBERANÍA DIGITAL V1.0</p>
            </body>
            </html>
            """
            self.wfile.write(html.encode())