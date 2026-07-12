import asyncio
import json
import os
import time

import websockets

GAZE_WS_PORT = int(os.environ.get("OCTO_GAZE_WS_PORT", "8082"))
TIMELINE_SYNC_URL = os.environ.get("TIMELINE_SYNC_URL", "ws://127.0.0.1:8767")

GAZE_WORKER_WS = None
GAZE_CLIENTS = set()
_timeline_ws = None

_gaze_frame_count = 0
_gaze_frame_last_log = 0.0
_gaze_last_ts_ms = None
_gaze_last_lag_ms = None
_gaze_drop_count = 0
_gaze_drop_last_log = 0.0
_gaze_recv_count = 0
_gaze_recv_last_log = 0.0


async def timeline_send(payload: dict) -> None:
    global _timeline_ws
    ws = _timeline_ws
    if ws is None:
        return
    try:
        await ws.send(json.dumps(payload))
    except Exception:
        _timeline_ws = None


async def _timeline_client_loop() -> None:
    global _timeline_ws
    while True:
        try:
            async with websockets.connect(
                TIMELINE_SYNC_URL,
                ping_interval=20,
                ping_timeout=20,
                close_timeout=1,
            ) as ws:
                _timeline_ws = ws
                print(f"✅ gaze-ws connected to timeline-sync: {TIMELINE_SYNC_URL}", flush=True)
                async for raw in ws:
                    try:
                        data = json.loads(raw)
                    except Exception:
                        continue
                    
                    if data.get("type") == "render_packet":
                        # CRITICAL: ONLY forward 'gaze' packets to the browser gaze socket.
                        # Forwarding everything causes double lip-sync (interference).
                        packet = data.get("packet") or {}
                        if packet.get("cmd") == "gaze":
                            msg = json.dumps(data)
                            dead = []
                            for client in list(GAZE_CLIENTS):
                                try:
                                    await client.send(msg)
                                except Exception:
                                    dead.append(client)
                            for d in dead:
                                GAZE_CLIENTS.discard(d)
        except Exception as e:
            if _timeline_ws is not None:
                _timeline_ws = None
            print(f"⚠️ gaze-ws timeline-sync error: {e}", flush=True)
            await asyncio.sleep(1.0)


async def _gaze_worker_loop(worker_ws):
    global GAZE_WORKER_WS
    GAZE_WORKER_WS = worker_ws
    print("👁️ gaze worker connected", flush=True)
    try:
        async for raw in worker_ws:
            try:
                data = json.loads(raw)
            except Exception:
                continue
            if data.get("type") != "gaze":
                continue
            gaze = data.get("gaze") or {}
            try:
                gx = float(gaze.get("x", 0.0))
                gy = float(gaze.get("y", 0.0))
            except Exception:
                gx, gy = 0.0, 0.0
            blink = bool(gaze.get("blink", False))
            global _gaze_recv_count, _gaze_recv_last_log
            _gaze_recv_count += 1
            now_ts = time.time()
            if now_ts - _gaze_recv_last_log >= 1.0:
                _gaze_recv_last_log = now_ts
                print(
                    f"👁️ gaze recv fps~{_gaze_recv_count} x={gx:.2f} y={gy:.2f} blink={blink}",
                    flush=True,
                )
                _gaze_recv_count = 0
            await timeline_send({
                "type": "gaze",
                "client_id": data.get("client_id", "default"),
                "gaze": {"x": gx, "y": gy, "blink": blink},
                "ts": time.time(),
            })
    except Exception as e:
        print(f"⚠️ gaze worker disconnected: {e}", flush=True)
    finally:
        if GAZE_WORKER_WS is worker_ws:
            GAZE_WORKER_WS = None


async def _handle_gaze_frame(frame: dict) -> None:
    ts_ms = frame.get("ts_ms")
    if ts_ms is not None:
        try:
            lag_ms = (time.time() * 1000.0) - float(ts_ms)
            global _gaze_last_ts_ms, _gaze_last_lag_ms
            _gaze_last_ts_ms = float(ts_ms)
            _gaze_last_lag_ms = float(lag_ms)
            if lag_ms > 800: # Slightly relaxed lag threshold
                global _gaze_drop_count, _gaze_drop_last_log
                _gaze_drop_count += 1
                now_ts = time.time()
                if now_ts - _gaze_drop_last_log >= 1.0:
                    _gaze_drop_last_log = now_ts
                    print(f"👁️ gaze_frame dropped~{_gaze_drop_count}", flush=True)
                    _gaze_drop_count = 0
                return
        except Exception:
            pass
    global _gaze_frame_count, _gaze_frame_last_log
    _gaze_frame_count += 1
    now_ts = time.time()
    if now_ts - _gaze_frame_last_log >= 1.0:
        if _gaze_last_ts_ms is not None and _gaze_last_lag_ms is not None:
            print(
                f"👁️ gaze_frame fps~{_gaze_frame_count} ts_ms={_gaze_last_ts_ms:.0f} lag_ms={_gaze_last_lag_ms:.0f}",
                flush=True,
            )
        else:
            print(f"👁️ gaze_frame fps~{_gaze_frame_count}", flush=True)
        _gaze_frame_last_log = now_ts
        _gaze_frame_count = 0
    worker_ws = GAZE_WORKER_WS
    if worker_ws is None:
        return
    try:
        await worker_ws.send(json.dumps({
            "type": "gaze_frame",
            "image_b64": frame.get("image_b64") or "",
            "mime": frame.get("mime") or "image/jpeg",
            "w": int(frame.get("w") or 0),
            "h": int(frame.get("h") or 0),
            "ts_ms": frame.get("ts_ms"),
        }))
    except Exception as e:
        print(f"⚠️ gaze forward failed: {e}", flush=True)


async def _gaze_client_loop(client_ws):
    global GAZE_CLIENTS
    GAZE_CLIENTS.add(client_ws)
    print(f"👁️ gaze client connected (total={len(GAZE_CLIENTS)})", flush=True)
    try:
        async for msg in client_ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue
            if not isinstance(data, dict) or "gaze_frame" not in data:
                continue
            await _handle_gaze_frame(data.get("gaze_frame") or {})
    except Exception as e:
        print(f"⚠️ gaze client error: {e}", flush=True)
    finally:
        GAZE_CLIENTS.discard(client_ws)


async def ws_handler(ws):
    path = ws.request.path if hasattr(ws, "request") else getattr(ws, "path", "")
    if not path:
        path = ""
    if path.startswith("/gaze-worker"):
        await _gaze_worker_loop(ws)
        return
    if path.startswith("/gaze-client"):
        await _gaze_client_loop(ws)
        return
    await ws.close()


async def _maybe_start_worker() -> None:
    gaze_bin = os.environ.get(
        "OCTO_GAZE_WORKER_BIN",
        "/Users/miguelaprossine/octopus-thorvg/gaze_capture_macos",
    )
    if not os.path.exists(gaze_bin):
        legacy = "/Users/miguelaprossine/octopuzzler/code/tools/gaze_capture_macos"
        if os.path.exists(legacy):
            gaze_bin = legacy

    gaze_ws = os.environ.get(
        "OCTO_GAZE_INPUT_WS",
        f"ws://localhost:{GAZE_WS_PORT}/gaze-worker",
    )
    if gaze_bin and os.path.exists(gaze_bin):
        env = os.environ.copy()
        env["OCTO_GAZE_INPUT_WS"] = gaze_ws
        models_dir = os.environ.get("OCTO_MODELS_DIR", "/Users/miguelaprossine/octopus-thorvg/models")
        if not os.path.exists(models_dir):
            legacy_models = "/Users/miguelaprossine/octopuzzler/models"
            if os.path.exists(legacy_models):
                models_dir = legacy_models
        env["OCTO_MODELS_DIR"] = models_dir
        try:
            log_path = "/tmp/gaze_worker.log"
            log_fh = open(log_path, "ab", buffering=0)
            proc = await asyncio.create_subprocess_exec(
                gaze_bin,
                env=env,
                stdout=log_fh,
                stderr=log_fh,
            )
            print(f"👁️ gaze worker started: {gaze_bin}", flush=True)
            return proc
        except Exception as e:
            print(f"⚠️ gaze worker start failed: {e}", flush=True)
    else:
        print(f"⚠️ gaze worker binary NOT FOUND at {gaze_bin}", flush=True)
    return None


async def main():
    asyncio.create_task(_timeline_client_loop())

    async with websockets.serve(
        ws_handler,
        "0.0.0.0",
        GAZE_WS_PORT,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=1,
    ):
        print(f"🔌 gaze-ws ws://localhost:{GAZE_WS_PORT}", flush=True)
        await _maybe_start_worker()
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
