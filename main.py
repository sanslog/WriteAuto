import sys
import threading

import uvicorn
import webview

from backend.config import API_HOST, API_PORT, DATA_DIR, NOVELS_DIR


def start_api():
    uvicorn.run(
        "backend.server:create_app",
        host=API_HOST,
        port=API_PORT,
        factory=True,
        log_level="info",
    )


def main(dev: bool = False):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    NOVELS_DIR.mkdir(parents=True, exist_ok=True)

    if dev:
        start_api()
        return

    api_thread = threading.Thread(target=start_api, daemon=True)
    api_thread.start()

    from backend.bridge import Bridge

    bridge = Bridge()
    window = webview.create_window(
        title="WriteAuto",
        url=f"http://{API_HOST}:{API_PORT}/",
        js_api=bridge,
        width=1400,
        height=900,
    )
    webview.start()


if __name__ == "__main__":
    dev_mode = "--dev" in sys.argv
    main(dev=dev_mode)
