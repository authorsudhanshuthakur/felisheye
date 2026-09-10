import os
import sys
import webbrowser
import threading
import time
import uvicorn
from app.core.config import settings

def open_browser():
    time.sleep(1.2)
    url = f"http://{settings.HOST}:{settings.PORT}"
    print(f"\n[FelisEye] Launching web browser at: {url}\n")
    try:
        webbrowser.open(url)
    except Exception:
        pass

if __name__ == "__main__":
    print("================================================================")
    print(f"      FelisEye — Private AI Face Recognition (v{settings.APP_VERSION})")
    print("      100% Offline • Zero Paid Cloud APIs • Encrypted Biometrics")
    print("================================================================")

    # Launch browser automatically in separate thread
    threading.Thread(target=open_browser, daemon=True).start()

    # Run FastAPI app
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False,
        log_level="info"
    )
