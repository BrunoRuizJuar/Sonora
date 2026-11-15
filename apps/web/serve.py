#!/usr/bin/env python3
"""SONORA: servidor local para la interfaz, sin dependencias externas."""
from __future__ import annotations

import argparse
import functools
import ipaddress
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import socket
import sys
import threading
from urllib.parse import unquote, urlsplit
import webbrowser

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"


class SonoraHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".svg": "image/svg+xml",
        ".webp": "image/webp",
        ".woff": "font/woff",
        ".js": "text/javascript",
        ".css": "text/css",
    }

    def end_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()

    def list_directory(self, path):
        self.send_error(404, "No hay una pagina en esta carpeta")
        return None

    def send_head(self):
        request_path = unquote(urlsplit(self.path).path)
        parts = request_path.replace("\\", "/").split("/")
        if any(part.startswith(".") for part in parts if part):
            self.send_error(404)
            return None
        translated = Path(self.translate_path(self.path)).resolve()
        if not translated.is_relative_to(PUBLIC.resolve()):
            self.send_error(404)
            return None
        if request_path == "/__sonora_health":
            payload = json.dumps({"status": "ok", "app": "SONORA", "mode": "visual-demo"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            from io import BytesIO
            return BytesIO(payload)
        return super().send_head()


def make_server(host="127.0.0.1", port=8000):
    handler = functools.partial(SonoraHandler, directory=str(PUBLIC))
    return ThreadingHTTPServer((host, port), handler)


def local_addresses():
    try:
        addresses = {row[4][0] for row in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET)}
    except OSError:
        return []
    return sorted(address for address in addresses
                  if ipaddress.ip_address(address).is_private
                  and not ipaddress.ip_address(address).is_loopback
                  and not ipaddress.ip_address(address).is_link_local)


def main():
    parser = argparse.ArgumentParser(description="Ejecuta la interfaz local de SONORA.")
    parser.add_argument("--wifi", action="store_true", help="Permite conexiones desde tu red Wi-Fi.")
    parser.add_argument("--port", type=int, default=8000, help="Puerto del servidor (8000 por defecto).")
    parser.add_argument("--open", action="store_true", help="Abre SONORA en el navegador.")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("El puerto debe estar entre 1 y 65535.")
    if not (PUBLIC / "index.html").is_file():
        print("Falta public/index.html. Extrae el ZIP completo antes de iniciar.", file=sys.stderr)
        return 1
    host = "0.0.0.0" if args.wifi else "127.0.0.1"
    try:
        server = make_server(host, args.port)
    except OSError as exc:
        print(f"No se pudo abrir el puerto {args.port}: {exc}", file=sys.stderr)
        print("Prueba: py -3 serve.py --port 8080 --open", file=sys.stderr)
        return 1
    url = f"http://localhost:{args.port}/"
    print("\nSONORA - servidor de la interfaz")
    print(f"En esta laptop: {url}")
    if args.wifi:
        print("Modo Wi-Fi: otros equipos de la misma red pueden abrir:")
        for address in local_addresses():
            print(f"  http://{address}:{args.port}/")
        print("Si no aparece tu IPv4, ejecuta ipconfig y revisa el adaptador Wi-Fi.")
        print("Al compartir, permite Python en redes privadas si Windows lo solicita.")
    else:
        print("Modo local: solo esta laptop. Para compartir usa COMPARTIR_WIFI.cmd.")
    print("Interfaz con datos de muestra; el recomendador real aun no esta conectado.")
    print("Deja esta ventana abierta. Para detener: Ctrl+C.\n", flush=True)
    if args.open:
        timer = threading.Timer(0.4, lambda: webbrowser.open(url))
        timer.daemon = True
        timer.start()
    try:
        with server:
            server.serve_forever()
    except KeyboardInterrupt:
        print("\nSONORA detenido.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
