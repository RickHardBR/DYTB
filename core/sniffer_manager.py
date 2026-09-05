from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from typing import Callable


class SnifferManager:
    def __init__(self, on_stream_captured: Callable[[str, str], None] | None = None):
        self.on_stream_captured = on_stream_captured
        self.process: subprocess.Popen | None = None
        self._listener_thread: threading.Thread | None = None
        self._is_listening = False
        self.captured_urls: set[str] = set()

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

    def launch(self, initial_url: str = "https://hotmart.com/"):
        browser_bin = self.find_browser_executable()
        if not browser_bin:
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

        if self.process is None or self.process.poll() is not None:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        if not self._is_listening:
            self._is_listening = True
            self._listener_thread = threading.Thread(target=self._cdp_listener_loop, args=(port,), daemon=True)
            self._listener_thread.start()

    def _cdp_listener_loop(self, port: int):
        import asyncio
        try:
            import websockets
        except ImportError:
            return

        async def listen():
            while self._is_listening:
                try:
                    req = urllib.request.Request(f"http://127.0.0.1:{port}/json")
                    with urllib.request.urlopen(req, timeout=2) as resp:
                        tabs = json.loads(resp.read().decode())
                        
                    page_tabs = [t for t in tabs if t.get("type") == "page" and "webSocketDebuggerUrl" in t]
                    if not page_tabs:
                        await asyncio.sleep(1)
                        continue

                    ws_url = page_tabs[0]["webSocketDebuggerUrl"]
                    async with websockets.connect(ws_url) as ws:
                        await ws.send(json.dumps({"id": 1, "method": "Network.enable"}))
                        
                        while self._is_listening:
                            msg_str = await ws.recv()
                            msg = json.loads(msg_str)
                            method = msg.get("method", "")
                            
                            req_url = ""
                            if method == "Network.requestWillBeSent":
                                req_url = msg.get("params", {}).get("request", {}).get("url", "")
                            elif method == "Network.responseReceived":
                                req_url = msg.get("params", {}).get("response", {}).get("url", "")

                            if req_url and self._is_media_stream(req_url):
                                if req_url not in self.captured_urls:
                                    self.captured_urls.add(req_url)
                                    if self.on_stream_captured:
                                        self.on_stream_captured(req_url, "Stream EAD Capturado")

                except Exception:
                    await asyncio.sleep(1)

        try:
            asyncio.run(listen())
        except Exception:
            pass

    def _is_media_stream(self, url: str) -> bool:
        u_lower = url.lower()
        if u_lower.startswith("blob:") or u_lower.startswith("data:"):
            return False
        return (
            ".m3u8" in u_lower
            or ".mpd" in u_lower
            or "content-player.hotmart.com" in u_lower
            or "pandavideo.com" in u_lower
            or ("/stream.m3u8" in u_lower)
            or ("/master.m3u8" in u_lower)
            or (".mp4" in u_lower and not u_lower.endswith(".js"))
        )

    def stop(self):
        self._is_listening = False
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
