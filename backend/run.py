import os
import signal
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.abspath(__file__))
APP = os.path.join(ROOT, "app.py")
TL  = os.path.join(ROOT, "timeline_sync.py")
GAZE = os.path.join(ROOT, "gaze_ws.py")

def main():
    env = os.environ.copy()

    print("🚀 Starting timeline-sync...")
    tl = subprocess.Popen([sys.executable, TL], env=env)

    time.sleep(0.3)

    print("🚀 Starting gaze-ws...")
    gaze = subprocess.Popen([sys.executable, GAZE], env=env)

    print("🚀 Starting backend app...")
    app_env = env.copy()
    app = subprocess.Popen([sys.executable, APP], env=app_env)

    print("\n✅ Running:")
    print(f" - timeline-sync: {TL}")
    print(f" - gaze-ws:      {GAZE}")
    print(f" - app:          {APP}\n")

    def shutdown(*_):
        print("\n🛑 Stopping services...")
        for p in (app, gaze, tl):
            if p.poll() is None:
                p.send_signal(signal.SIGTERM)
        for p in (app, gaze, tl):
            try:
                p.wait(timeout=3)
            except Exception:
                pass
        raise SystemExit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # wait for any to exit
    while True:
        if app.poll() is not None or tl.poll() is not None or gaze.poll() is not None:
            shutdown()

        time.sleep(0.2)

if __name__ == "__main__":
    main()
