from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from typing import Callable


JS_SNIFFER_HOOK = """
(function() {
    if (window.__dytb_hook_installed) return;
    window.__dytb_hook_installed = true;

    function reportStream(url, kind) {
        if (!url || typeof url !== 'string') return;
        if (url.startsWith('blob:') || url.startsWith('data:')) return;
        var u = url.toLowerCase();
        if (
            u.includes('.m3u8') ||
            u.includes('.mpd') ||
            u.includes('master.m3u8') ||
            u.includes('playlist.m3u8') ||
            u.includes('chunklist') ||
            u.includes('content-player.hotmart.com') ||
            u.includes('pandavideo.com.br') ||
            u.includes('vimeocdn.com')
        ) {
            try {
                console.debug('[DYTB_STREAM]', JSON.stringify({
                    url: url,
                    title: document.title || 'Vídeo EAD',
                    kind: kind || 'stream'
                }));
            } catch(e) {}
        }
    }

    // Hook fetch
    try {
        var origFetch = window.fetch;
        if (origFetch) {
            window.fetch = function(input, init) {
                try {
                    var u = typeof input === 'string' ? input : (input && input.url ? input.url : '');
                    reportStream(u, 'fetch');
                } catch(e) {}
                return origFetch.apply(this, arguments);
            };
        }
    } catch(e) {}

    // Hook XMLHttpRequest
    try {
        var origOpen = XMLHttpRequest.prototype.open;
        XMLHttpRequest.prototype.open = function(method, url) {
            try {
                reportStream(url, 'xhr');
            } catch(e) {}
            return origOpen.apply(this, arguments);
        };
    } catch(e) {}

    // Monitoramento contínuo de tags video/audio
    setInterval(function() {
        try {
            var mediaElements = document.querySelectorAll('video, audio, source');
            for (var i = 0; i < mediaElements.length; i++) {
                var src = mediaElements[i].src || mediaElements[i].currentSrc;
                if (src) reportStream(src, 'media_tag');
            }
        } catch(e) {}
    }, 1500);
})();
"""


class SnifferManager:
    def __init__(
        self,
        on_stream_captured: Callable[[str, str], None] | None = None,
        on_status_changed: Callable[[bool, str], None] | None = None,
    ):
        self.on_stream_captured = on_stream_captured
        self.on_status_changed = on_status_changed
        self.process: subprocess.Popen | None = None
        self._listener_thread: threading.Thread | None = None
        self._is_listening = False
        self.captured_urls: list[dict] = []
        self._seen_urls: set[str] = set()

    def find_browser_executable(self) -> str | None:
        candidates = [
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            shutil.which("msedge"),
            shutil.which("chrome"),
        ]
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return None

    def is_running(self) -> bool:
        return self.process is not None and self.process.poll() is None

    def launch(self, initial_url: str = "https://hotmart.com/"):
        browser_bin = self.find_browser_executable()
        if not browser_bin:
            if self.on_status_changed:
                self.on_status_changed(False, "Nenhum navegador suportado (Edge/Chrome) encontrado.")
            import webbrowser
            webbrowser.open(initial_url or "https://hotmart.com/")
            return

        user_data_dir = os.path.join(
            os.environ.get("APPDATA", os.path.expanduser("~")),
            "DYTB",
            "sniffer_browser_data",
        )
        os.makedirs(user_data_dir, exist_ok=True)

        port = 9222
        cmd = [
            browser_bin,
            f"--remote-debugging-port={port}",
            f"--user-data-dir={user_data_dir}",
            "--no-first-run",
            "--no-default-browser-check",
            initial_url or "https://hotmart.com/",
        ]

        if not self.is_running():
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        if not self._is_listening:
            self._is_listening = True
            self._listener_thread = threading.Thread(target=self._cdp_listener_loop, args=(port,), daemon=True)
            self._listener_thread.start()

    def _notify_status(self, connected: bool, message: str):
        if self.on_status_changed:
            self.on_status_changed(connected, message)

    def _cdp_listener_loop(self, port: int):
        try:
            import websockets
        except ImportError:
            self._notify_status(False, "Dependência websockets ausente.")
            return

        async def listen():
            while self._is_listening:
                try:
                    # 1. Tenta obter o WebSocketDebuggerUrl do browser
                    browser_ws_url = None
                    try:
                        req = urllib.request.Request(f"http://127.0.0.1:{port}/json/version")
                        with urllib.request.urlopen(req, timeout=2) as resp:
                            ver_data = json.loads(resp.read().decode())
                            browser_ws_url = ver_data.get("webSocketDebuggerUrl")
                    except Exception:
                        pass

                    if not browser_ws_url:
                        # Fallback para abas individuais
                        try:
                            req = urllib.request.Request(f"http://127.0.0.1:{port}/json")
                            with urllib.request.urlopen(req, timeout=2) as resp:
                                tabs = json.loads(resp.read().decode())
                            page_tabs = [t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t]
                            if page_tabs:
                                browser_ws_url = page_tabs[0]["webSocketDebuggerUrl"]
                        except Exception:
                            pass

                    if not browser_ws_url:
                        self._notify_status(False, "Aguardando inicialização do navegador...")
                        await asyncio.sleep(1.5)
                        continue

                    self._notify_status(True, "Navegador conectado. Monitorando transmissões de vídeo...")

                    async with websockets.connect(browser_ws_url, ping_interval=10, ping_timeout=10, max_size=10_000_000) as ws:
                        msg_id = 1
                        
                        # Ativa anexo automático para todos os alvos, abas e iframes (modo flatten)
                        await ws.send(json.dumps({
                            "id": msg_id,
                            "method": "Target.setAutoAttach",
                            "params": {
                                "autoAttach": True,
                                "waitForDebuggerOnStart": False,
                                "flatten": True
                            }
                        }))
                        msg_id += 1

                        # Ativa domínios na sessão principal
                        await ws.send(json.dumps({"id": msg_id, "method": "Network.enable"}))
                        msg_id += 1
                        await ws.send(json.dumps({"id": msg_id, "method": "Runtime.enable"}))
                        msg_id += 1

                        while self._is_listening:
                            msg_str = await ws.recv()
                            msg = json.loads(msg_str)
                            method = msg.get("method", "")
                            session_id = msg.get("sessionId")

                            # Quando um novo alvo / iframe é anexado
                            if method == "Target.attachedToTarget":
                                if session_id:
                                    # Ativa Network, Runtime e injeta Hook JS no novo iframe/alvo
                                    await ws.send(json.dumps({
                                        "id": msg_id,
                                        "sessionId": session_id,
                                        "method": "Network.enable"
                                    }))
                                    msg_id += 1
                                    await ws.send(json.dumps({
                                        "id": msg_id,
                                        "sessionId": session_id,
                                        "method": "Runtime.enable"
                                    }))
                                    msg_id += 1
                                    await ws.send(json.dumps({
                                        "id": msg_id,
                                        "sessionId": session_id,
                                        "method": "Page.enable"
                                    }))
                                    msg_id += 1
                                    await ws.send(json.dumps({
                                        "id": msg_id,
                                        "sessionId": session_id,
                                        "method": "Page.addScriptToEvaluateOnNewDocument",
                                        "params": {"source": JS_SNIFFER_HOOK}
                                    }))
                                    msg_id += 1

                            # Intercepta eventos de rede
                            req_url = ""
                            if method == "Network.requestWillBeSent":
                                req_url = msg.get("params", {}).get("request", {}).get("url", "")
                            elif method == "Network.responseReceived":
                                req_url = msg.get("params", {}).get("response", {}).get("url", "")

                            # Intercepta chamadas do Hook JS no console
                            if method == "Runtime.consoleAPICalled":
                                params = msg.get("params", {})
                                if params.get("type") == "debug":
                                    args = params.get("args", [])
                                    if args and args[0].get("value") == "[DYTB_STREAM]" and len(args) > 1:
                                        try:
                                            payload = json.loads(args[1].get("value", "{}"))
                                            c_url = payload.get("url", "")
                                            c_title = payload.get("title", "Vídeo EAD Capturado")
                                            if c_url:
                                                self._handle_captured_candidate(c_url, c_title)
                                        except Exception:
                                            pass

                            if req_url:
                                self._handle_network_url(req_url)

                except Exception:
                    self._notify_status(False, "Conexão com navegador interrompida. Tentando reconectar...")
                    await asyncio.sleep(2)

        try:
            asyncio.run(listen())
        except Exception:
            self._notify_status(False, "Monitoramento finalizado.")

    def _handle_network_url(self, url: str):
        if not self._is_media_stream(url):
            return
        self._handle_captured_candidate(url, "Stream de Vídeo EAD")

    def _handle_captured_candidate(self, url: str, title: str):
        # Normalização e filtros finos
        if not url or url in self._seen_urls:
            return
        
        # Ignora segmentos individuais se houver manifesto
        u_lower = url.lower()
        if (u_lower.endswith(".ts") or u_lower.endswith(".m4s")) and not any(k in u_lower for k in ["master", "playlist", "chunklist"]):
            return

        self._seen_urls.add(url)
        item = {
            "url": url,
            "title": title or "Vídeo EAD Capturado",
            "time": time.strftime("%H:%M:%S"),
        }
        self.captured_urls.append(item)

        if self.on_stream_captured:
            self.on_stream_captured(url, title)

    def _is_media_stream(self, url: str) -> bool:
        u_lower = url.lower()
        if u_lower.startswith("blob:") or u_lower.startswith("data:"):
            return False
        
        # Ignora arquivos estáticos comuns
        if any(u_lower.endswith(ext) for ext in [".js", ".css", ".png", ".jpg", ".jpeg", ".svg", ".woff", ".woff2", ".ico"]):
            return False

        return (
            ".m3u8" in u_lower
            or ".mpd" in u_lower
            or "content-player.hotmart.com" in u_lower
            or "pandavideo.com.br" in u_lower
            or "stream.hotmart.com" in u_lower
            or "player.hotmart.com" in u_lower
            or "/master.m3u8" in u_lower
            or "/playlist.m3u8" in u_lower
            or "/stream.m3u8" in u_lower
            or (".mp4" in u_lower and "?" in u_lower and ("token=" in u_lower or "signature=" in u_lower or "expires=" in u_lower))
        )

    def stop(self):
        self._is_listening = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
        self._notify_status(False, "Navegador finalizado.")
