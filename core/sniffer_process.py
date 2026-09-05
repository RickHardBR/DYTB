from __future__ import annotations

import json
import os
import sys
import time

SNIFFER_JS = """
(function() {
    if (window.__dytb_sniffer_installed) return;
    window.__dytb_sniffer_installed = true;

    // Injeta HUD flutuante no DOM
    function injectHUD() {
        if (document.getElementById('dytb-sniffer-hud')) return;
        const hud = document.createElement('div');
        hud.id = 'dytb-sniffer-hud';
        hud.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:2147483647;background:linear-gradient(135deg,#0e1621,#131e2e);border:1.5px solid #06b6d4;border-radius:10px;padding:12px 16px;color:#f8fafc;font-family:Segoe UI,Roboto,sans-serif;box-shadow:0 8px 28px rgba(0,0,0,0.75);display:flex;flex-direction:column;gap:8px;min-width:280px;max-width:380px;pointer-events:auto;';
        
        hud.innerHTML = `
            <div style="display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #1e293b;padding-bottom:6px;">
                <span style="font-size:12px;font-weight:bold;color:#38bdf8;display:flex;align-items:center;gap:6px;">
                    <span style="width:8px;height:8px;background:#10b981;border-radius:50%;display:inline-block;animation:pulse 1.5s infinite;"></span>
                    DYTB Sniffer de Mídia EAD
                </span>
            </div>
            <div id="dytb-hud-msg" style="font-size:11px;color:#94a3b8;line-height:1.4;">
                Navegue até a aula e clique em <b>Play</b> no vídeo para capturar o stream...
            </div>
            <div id="dytb-hud-actions" style="display:none;margin-top:4px;">
                <button id="dytb-hud-btn" style="width:100%;background:#0284c7;color:#fff;border:none;border-radius:6px;padding:8px;font-weight:bold;font-size:12px;cursor:pointer;transition:background 0.2s;">
                    ⬇ Enviar para Download no DYTB
                </button>
            </div>
        `;
        document.documentElement.appendChild(hud);
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', injectHUD);
    } else {
        injectHUD();
    }
    setInterval(injectHUD, 2000);

    let lastFoundUrl = null;

    function handleDetectedMedia(url, type) {
        if (!url || typeof url !== 'string') return;
        if (url.startsWith('blob:') || url.startsWith('data:')) return;
        
        const isStream = url.includes('.m3u8') || url.includes('.mpd') || 
                         url.includes('content-player.hotmart.com') || 
                         url.includes('/master.m3u8') || url.includes('/stream.m3u8') ||
                         url.includes('pandavideo.com') || (url.includes('.mp4') && !url.includes('.js'));

        if (isStream && url !== lastFoundUrl) {
            lastFoundUrl = url;
            const hudMsg = document.getElementById('dytb-hud-msg');
            const hudActions = document.getElementById('dytb-hud-actions');
            const hudBtn = document.getElementById('dytb-hud-btn');

            if (hudMsg && hudActions && hudBtn) {
                hudMsg.innerHTML = '🎯 <b style="color:#10b981;">Vídeo Localizado!</b><br><span style="font-size:10px;color:#64748b;word-break:break-all;">' + url.substring(0, 75) + '...</span>';
                hudActions.style.display = 'block';
                hudBtn.onclick = function() {
                    hudBtn.innerText = '✓ Enviado para o DYTB!';
                    hudBtn.style.background = '#10b981';
                    if (window.pywebview && window.pywebview.api && window.pywebview.api.send_to_dytb) {
                        window.pywebview.api.send_to_dytb(url, document.title);
                    }
                };
            }

            try {
                if (window.pywebview && window.pywebview.api && window.pywebview.api.on_stream_found) {
                    window.pywebview.api.on_stream_found(url, document.title);
                }
            } catch(e) {}
        }
    }

    // Intercepta Fetch
    const origFetch = window.fetch;
    window.fetch = function(...args) {
        if (args && args[0]) {
            const reqUrl = typeof args[0] === 'string' ? args[0] : (args[0].url || '');
            handleDetectedMedia(reqUrl, 'fetch');
        }
        return origFetch.apply(this, args);
    };

    // Intercepta XMLHttpRequest
    const origOpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...rest) {
        handleDetectedMedia(url, 'xhr');
        return origOpen.apply(this, [method, url, ...rest]);
    };

    // Observa tags de vídeo e áudio inseridas no DOM
    const observer = new MutationObserver(() => {
        document.querySelectorAll('video, source').forEach(el => {
            if (el.src) handleDetectedMedia(el.src, 'tag');
            if (el.currentSrc) handleDetectedMedia(el.currentSrc, 'tag');
        });
    });
    observer.observe(document.documentElement, { childList: true, subtree: true });
})();
"""


class SnifferAPI:
    def __init__(self, window_holder):
        self.window_holder = window_holder
        self.captured_urls: list[str] = []

    def on_stream_found(self, url: str, title: str):
        if url not in self.captured_urls:
            self.captured_urls.append(url)
            print(f"DYTB_STREAM_DETECTED:{json.dumps({'url': url, 'title': title})}", flush=True)

    def send_to_dytb(self, url: str, title: str):
        print(f"DYTB_SEND_DOWNLOAD:{json.dumps({'url': url, 'title': title})}", flush=True)
        time.sleep(0.4)
        if self.window_holder and self.window_holder[0]:
            try:
                self.window_holder[0].destroy()
            except Exception:
                pass


def run_sniffer(initial_url: str = "https://hotmart.com/"):
    try:
        import webview
    except ImportError:
        print("DYTB_ERROR: pywebview não está instalado.", flush=True)
        return

    window_holder = [None]
    api = SnifferAPI(window_holder)

    # Cria janela do navegador WebView com tema escuro e injeção do sniffer
    window = webview.create_window(
        title="DYTB Downloader - Navegador Sniffer EAD",
        url=initial_url or "https://hotmart.com/",
        js_api=api,
        width=1100,
        height=720,
        resizable=True,
    )
    window_holder[0] = window

    def on_loaded():
        try:
            window.evaluate_js(SNIFFER_JS)
        except Exception:
            pass

    window.events.loaded += on_loaded

    # Inicia o loop de eventos da WebView
    webview.start(private_mode=False)


if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "https://hotmart.com/"
    run_sniffer(target_url)
