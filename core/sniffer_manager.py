from __future__ import annotations

import json
import os
import subprocess
import sys
import threading
from typing import Callable


class SnifferManager:
    def __init__(self, on_stream_captured: Callable[[str, str], None] | None = None):
        self.on_stream_captured = on_stream_captured
        self.process: subprocess.Popen | None = None
        self._reader_thread: threading.Thread | None = None

    def launch(self, initial_url: str = "https://hotmart.com/"):
        if self.process is not None and self.process.poll() is None:
            return

        if getattr(sys, "frozen", False):
            cmd = [sys.executable, "--run-sniffer-url", initial_url]
        else:
            cmd = [sys.executable, "app.py", "--run-sniffer-url", initial_url]

        creationflags = 0
        if os.name == "nt":
            creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

        self.process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            errors="replace",
            shell=False,
            creationflags=creationflags,
        )

        self._reader_thread = threading.Thread(target=self._read_output, daemon=True)
        self._reader_thread.start()

    def _read_output(self):
        if not self.process or not self.process.stdout:
            return

        while True:
            line = self.process.stdout.readline()
            if not line and self.process.poll() is not None:
                break
            line = line.strip()
            if not line:
                continue

            if line.startswith("DYTB_SEND_DOWNLOAD:") or line.startswith("DYTB_STREAM_DETECTED:"):
                payload_str = line.split(":", 1)[1].strip()
                try:
                    data = json.loads(payload_str)
                    captured_url = data.get("url", "")
                    title = data.get("title", "")
                    if captured_url and self.on_stream_captured:
                        self.on_stream_captured(captured_url, title)
                except Exception:
                    pass

    def stop(self):
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
            except Exception:
                pass
            self.process = None
