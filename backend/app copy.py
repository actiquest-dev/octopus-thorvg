import asyncio
import base64
import json
import time
import os
import random
import numpy as np
import websockets
import aiohttp
from aiohttp import web
from google.oauth2 import service_account
from google.auth.transport.requests import Request

HTTP_PORT = 8081
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
_FRONTEND_DIR = os.path.abspath(os.path.join(_BASE_DIR, "..", "frontend"))
_DEFAULT_CREDENTIALS = os.path.abspath(os.path.join(_BASE_DIR, "..", "credentials.json"))

def _get_credentials_path():
    env_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if env_path:
        return env_path
    local_path = os.path.join(_BASE_DIR, "credentials.json")
    if os.path.exists(local_path):
        return local_path
    if os.path.exists(_DEFAULT_CREDENTIALS):
        return _DEFAULT_CREDENTIALS
    return "credentials.json"
WS_PORT = 8080

# Optional .env loader (no external deps)
def _load_dotenv(path: str) -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for line in fh:
                raw = line.strip()
                if not raw or raw.startswith("#") or "=" not in raw:
                    continue
                key, val = raw.split("=", 1)
                key = key.strip()
                if key and key not in os.environ:
                    os.environ[key] = val.strip().strip('"').strip("'")
    except Exception:
        pass

_load_dotenv(os.path.join(os.getcwd(), ".env"))
_load_dotenv(os.path.join(_BASE_DIR, "..", ".env"))
FREESOUND_API_KEY = os.environ.get("FREESOUND_API_KEY", "")

# Timeline Sync (local service) - stable server-side animation timeline
TIMELINE_SYNC_URL = os.environ.get("TIMELINE_SYNC_URL", "ws://127.0.0.1:8767")
_timeline_ws = None
_timeline_task = None

# Track connected browser WS clients so timeline-sync can broadcast render packets
BROWSER_CLIENTS = set()
GAZE_WORKER_WS = None
_gaze_frame_count = 0
_gaze_frame_last_log = 0.0
_gaze_last_ts_ms = None
_gaze_last_lag_ms = None
_gaze_drop_count = 0
_gaze_drop_last_log = 0.0
_gaze_send_count = 0
_gaze_send_last_log = 0.0
_gaze_recv_count = 0
_gaze_recv_last_log = 0.0
_gaze_proc = None

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
                print(f"👁️ gaze recv fps~{_gaze_recv_count} x={gx:.2f} y={gy:.2f} blink={blink}", flush=True)
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
            if lag_ms > 500:
                global _gaze_drop_count, _gaze_drop_last_log
                _gaze_drop_count += 1
                now_ts = time.time()
                if now_ts - _gaze_drop_last_log >= 1.0:
                    _gaze_drop_last_log = now_ts
                    print(f"👁️ gaze_frame dropped~{_gaze_drop_count}", flush=True)
                    _gaze_drop_count = 0
                return
            global _gaze_last_ts_ms, _gaze_last_lag_ms
            _gaze_last_ts_ms = float(ts_ms)
            _gaze_last_lag_ms = float(lag_ms)
            print(f"👁️ gaze_frame lag_ms={lag_ms:.0f}", flush=True)
        except Exception:
            pass
    global _gaze_frame_count, _gaze_frame_last_log
    _gaze_frame_count += 1
    now_ts = time.time()
    if now_ts - _gaze_frame_last_log >= 1.0:
        _gaze_frame_last_log = now_ts
        if _gaze_last_ts_ms is not None and _gaze_last_lag_ms is not None:
            print(
                f"👁️ gaze_frame fps~{_gaze_frame_count} ts_ms={_gaze_last_ts_ms:.0f} lag_ms={_gaze_last_lag_ms:.0f}",
                flush=True,
            )
        else:
            print(f"👁️ gaze_frame fps~{_gaze_frame_count}", flush=True)
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
    print("👁️ gaze client connected", flush=True)
    async for msg in client_ws:
        try:
            data = json.loads(msg)
        except Exception:
            continue
        if not isinstance(data, dict) or "gaze_frame" not in data:
            continue
        await _handle_gaze_frame(data.get("gaze_frame") or {})

async def timeline_send(payload: dict) -> None:
    """Best-effort send to timeline-sync. Drops silently if not connected."""
    global _timeline_ws
    ws = _timeline_ws
    if ws is None:
        return
    try:
        await ws.send(json.dumps(payload))
    except Exception:
        _timeline_ws = None

async def _timeline_client_loop() -> None:
    """Connects to timeline-sync and forwards render packets to browsers."""
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
                print(f"✅ timeline-sync connected: {TIMELINE_SYNC_URL}")

                async for raw in ws:
                    try:
                        msg = json.loads(raw)
                    except Exception:
                        continue
                    if msg.get("type") != "render_packet":
                        continue

                    render = msg.get("packet") or {}
                    print(f"➡️ timeline render_packet seq={msg.get('seq')} keys={list(render.keys())}", flush=True)
                    out = {"serverContent": {"avatar": render}, "avatar": render}

                    dead = []
                    for c in list(BROWSER_CLIENTS):
                        try:
                            await c.send(json.dumps(out))
                        except Exception:
                            dead.append(c)
                    for d in dead:
                        BROWSER_CLIENTS.discard(d)

        except Exception as e:
            if _timeline_ws is not None:
                _timeline_ws = None
            print(f"⚠️ timeline-sync disconnected: {e}")
            await asyncio.sleep(0.5)

BUFFER_MS = 300
SAMPLE_RATE = 24000

def b64_to_pcm16(base64_audio: str) -> np.ndarray:
    audio_bytes = base64.b64decode(base64_audio)
    pcm16 = np.frombuffer(audio_bytes, dtype=np.int16)
    return pcm16

def compute_amplitudes(pcm16: np.ndarray, window_ms: int = 20) -> list:
    window_size = int((window_ms / 1000) * SAMPLE_RATE)
    if window_size <= 0:
        window_size = 480
    amps = []
    for i in range(0, len(pcm16), window_size):
        window = pcm16[i:i+window_size]
        if len(window) == 0:
            continue
        rms = float(np.sqrt(np.mean(window.astype(np.float32) ** 2)))
        amps.append(rms / 32768.0)
    return amps

def iter_inline_data(node):
    """Yield inlineData dicts from any nested structure."""
    if isinstance(node, dict):
        inline = node.get("inlineData")
        if isinstance(inline, dict):
            yield inline
        for v in node.values():
            yield from iter_inline_data(v)
    elif isinstance(node, list):
        for item in node:
            yield from iter_inline_data(item)

def analyze_emotion(text: str) -> str:
    text_l = (text or "").lower()
    if any(w in text_l for w in ["!", "ура", "класс", "супер", "отлично", "😍", "😊"]):
        return "happy"
    if any(w in text_l for w in ["грусть", "печаль", "плохо", "жаль", "😢"]):
        return "sad"
    if any(w in text_l for w in ["злюсь", "ненавижу", "бесит", "😡"]):
        return "angry"
    return "neutral"

def emotion_meta(emotion: str) -> dict:
    # Можно потом тюнить под стиль персонажа
    if emotion == "happy":
        return {"attack_ms": 140, "release_ms": 260}
    if emotion == "sad":
        return {"attack_ms": 220, "release_ms": 420}
    if emotion == "angry":
        return {"attack_ms": 90, "release_ms": 220}
    return {"attack_ms": 180, "release_ms": 300}

_ALLOWED_EMOTIONS = {
    "happy", "sad", "angry", "neutral", "excited", "calm",
    "curious", "confused", "sarcastic", "proud", "tender", "playful",
}
_EMOTION_SYNONYMS = {
    "joyful": "happy",
    "joy": "happy",
    "cheerful": "happy",
    "delighted": "happy",
    "glad": "happy",
    "relaxed": "calm",
    "serene": "calm",
    "peaceful": "calm",
    "mad": "angry",
    "rage": "angry",
    "furious": "angry",
    "unhappy": "sad",
    "down": "sad",
    "blue": "sad",
    "surprised": "excited",
    "amused": "playful",
    "playful": "playful",
    "teasing": "playful",
    "pride": "proud",
    "tenderness": "tender",
    "sarcasm": "sarcastic",
    "confusion": "confused",
    "curiosity": "curious",
}
_ALLOWED_ACTIONS = {
    "none", "sing", "laugh", "whisper", "shout",
    "heart", "wave", "clap", "point", "hug", "shrug", "wipe",
    "sfx_pop", "sfx_sparkle", "sfx_boop", "sfx_wave", "sfx_spin",
    "sfx_tear", "sfx_sweat", "sfx_heart", "sfx_bubble",
}

def extract_tags(text: str):
    """Extract EMOTION_TAG/ACTION_TAG lines and return (clean_text, emotion, action)."""
    if not text:
        return "", None, None
    emotion = None
    action = None
    kept = []
    for line in text.splitlines():
        t = line.strip()
        if t.startswith("EMOTION_TAG:"):
            val = t.split(":", 1)[1].strip().lower()
            if val in _ALLOWED_EMOTIONS:
                emotion = val
            elif val in _EMOTION_SYNONYMS:
                emotion = _EMOTION_SYNONYMS[val]
            else:
                # Unknown emotion tag defaults to neutral
                emotion = "neutral"
            continue
        if t.startswith("ACTION_TAG:"):
            val = t.split(":", 1)[1].strip()
            if val in _ALLOWED_ACTIONS:
                action = val
            continue
        kept.append(line)
    clean = "\n".join(kept).strip()
    return clean, emotion, action

class AudioBuffer:
    def __init__(self, buffer_ms: int, sample_rate: int):
        self.buffer_ms = buffer_ms
        self.sample_rate = sample_rate
        self.chunks = []
        self.total_samples = 0
        self.min_samples = int((buffer_ms / 1000) * sample_rate)

    def add_chunk(self, base64_audio: str, amplitudes: list):
        pcm16 = b64_to_pcm16(base64_audio)
        samples = len(pcm16)
        self.chunks.append({
            "audio_b64": base64_audio,
            "samples": samples,
            "amps": amplitudes,
        })
        self.total_samples += samples
        return self.total_samples >= self.min_samples

    def pop_buffer(self, force: bool = False):
        if self.total_samples < self.min_samples and not force:
            return None

        amps = []
        total_samples = 0

        # ВАЖНО: base64 нельзя склеивать строками. Склеиваем bytes.
        raw_bytes_parts = []
        for c in self.chunks:
            try:
                raw_bytes_parts.append(base64.b64decode(c["audio_b64"]))
            except Exception:
                raw_bytes_parts.append(b"")
            amps.extend(c["amps"])
            total_samples += c["samples"]

        combined_bytes = b"".join(raw_bytes_parts)
        combined_b64 = base64.b64encode(combined_bytes).decode("ascii")

        duration_s = total_samples / self.sample_rate

        self.chunks = []
        self.total_samples = 0
        return combined_b64, amps, duration_s

async def websocket_handler(client_ws):
    path = ""
    try:
        path = getattr(client_ws, "path", "") or ""
        if not path:
            req = getattr(client_ws, "request", None)
            path = getattr(req, "path", "") or ""
    except Exception:
        path = ""
    ua = ""
    try:
        ua = str(client_ws.request_headers.get("User-Agent", ""))
    except Exception:
        ua = ""
    print(f"🔗 ws path={path}", flush=True)
    hdrs = {}
    try:
        hdrs = client_ws.request_headers or {}
    except Exception:
        hdrs = {}
    if (
        hdrs.get("X-Gaze-Worker") == "1"
        or "role=gaze-worker" in path
        or path.startswith("/gaze-worker")
        or ("CFNetwork" in ua or "NSURLSession" in ua)
    ):
        if ua:
            print(f"👁️ gaze worker ua={ua}", flush=True)
        await _gaze_worker_loop(client_ws)
        return
    if (
        hdrs.get("X-Gaze-Client") == "1"
        or "role=gaze-client" in path
        or path.startswith("/gaze-client")
    ):
        print("👁️ gaze client connected", flush=True)
        await _gaze_client_loop(client_ws)
        return

    print("🔌 Браузер подключился", flush=True)
    BROWSER_CLIENTS.add(client_ws)

    google_ws = None
    google_ready = asyncio.Event()
    google_to_browser_task = None
    google_connect_lock = asyncio.Lock()
    last_service_url = None

    audio_buffer = AudioBuffer(BUFFER_MS, SAMPLE_RATE)
    audio_seq = 0
    output_buffer = ""
    audio_debug_count = 0
    end_sent = False

    async def connect_google(service_url: str):
        nonlocal google_ws
        nonlocal last_service_url
        creds_path = _get_credentials_path()
        creds = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/cloud-platform"],
        )
        creds.refresh(Request())
        token = creds.token
        google_ws = await websockets.connect(
            service_url,
            extra_headers={"Authorization": f"Bearer {token}"},
            ping_interval=20,
            ping_timeout=20,
            close_timeout=1,
        )
        print("✅ Google подключен")
        last_service_url = service_url

    async def ensure_google_connection(service_url=None):
        nonlocal google_ws, google_ready, google_to_browser_task, last_service_url
        if service_url:
            last_service_url = service_url
        target_url = last_service_url
        if not target_url:
            return False
        async with google_connect_lock:
            if google_ws and not getattr(google_ws, "closed", True):
                if not google_ready.is_set():
                    google_ready.set()
                return True
            google_ready.clear()
            if google_to_browser_task:
                google_to_browser_task.cancel()
                try:
                    await google_to_browser_task
                except asyncio.CancelledError:
                    pass
                google_to_browser_task = None
            if google_ws is not None:
                try:
                    await google_ws.close()
                except Exception:
                    pass
                google_ws = None
            try:
                await connect_google(target_url)
            except Exception as exc:
                print(f"⚠️ Google reconnect failed: {exc}", flush=True)
                return False
            google_ready.set()
            google_to_browser_task = asyncio.create_task(google_to_browser())
            return True

    async def browser_to_google():
        nonlocal google_to_browser_task, google_ws

        async for msg in client_ws:
            # parse json (only for routing, forward original msg)
            try:
                data = json.loads(msg)
            except Exception:
                data = None

            # Gaze worker handshake fallback (in case path/UA routing failed)
            if isinstance(data, dict) and data.get("type") == "gaze_hello":
                print("👁️ gaze_hello received; reclassifying connection", flush=True)
                if client_ws in BROWSER_CLIENTS:
                    BROWSER_CLIENTS.discard(client_ws)
                await _gaze_worker_loop(client_ws)
                return

            # HEARTBEAT / client_event -> do not forward to Google
            if isinstance(data, dict) and "client_event" in data:
                ce = data.get("client_event") or {}
                if ce.get("type") == "heartbeat":
                    try:
                        await timeline_send({
                            "type": "heartbeat",
                            "playback_delay_s": float(ce.get("playback_delay_s") or 0.0),
                            "client_id": "default",
                            "ts": time.time(),
                        })
                    except Exception:
                        pass
                continue

            # gaze_frame fallback (in case gaze-client routing failed)
            if isinstance(data, dict) and "gaze_frame" in data:
                await _handle_gaze_frame(data.get("gaze_frame") or {})
                continue

            if isinstance(data, dict):
                print("➡️ browser keys=", list(data.keys()), flush=True)
            else:
                print("➡️ browser non-json", flush=True)

            # service_url -> connect Google, do not forward
            if isinstance(data, dict) and "service_url" in data:
                if await ensure_google_connection(data["service_url"]):
                    continue
                else:
                    print("⚠️ Failed to establish Google connection", flush=True)
                    continue

            # client_content -> reset timeline for new turn
            if isinstance(data, dict) and "client_content" in data:
                # DEBUG: покажем текст сообщения
                turns = data.get("client_content", {}).get("turns", [])
                if turns:
                    text_parts = [p.get("text", "?") for p in turns[0].get("parts", []) if "text" in p]
                    print(f"📤 client_content text={text_parts[:1]}", flush=True)
                if _timeline_ws is not None:
                    print("➡️ timeline_send reset_audio (client_content)", flush=True)
                    await timeline_send({
                        "type": "reset_audio",
                        "client_id": "default",
                        "ts": time.time(),
                    })
                audio_buffer = AudioBuffer(BUFFER_MS, SAMPLE_RATE)
                audio_seq = 0

            # client_tag -> do not forward; drive timeline directly
            if isinstance(data, dict) and "client_tag" in data:
                ct = data.get("client_tag") or {}
                emo_raw = (ct.get("emotion") or "").strip().lower()
                act_raw = (ct.get("action") or "").strip().lower()
                print(
                    "🏷️ client_tag emotion=%r action=%r duration_ms=%r"
                    % (emo_raw, act_raw, ct.get("duration_ms")),
                    flush=True,
                )
                emo = None
                if emo_raw:
                    if emo_raw in _ALLOWED_EMOTIONS:
                        emo = emo_raw
                    elif emo_raw in _EMOTION_SYNONYMS:
                        emo = _EMOTION_SYNONYMS[emo_raw]
                    else:
                        emo = "neutral"
                if emo:
                    await timeline_send({
                        "type": "emotion",
                        "emotion": emo,
                        "attack_ms": emotion_meta(emo).get("attack_ms", 180),
                        "release_ms": emotion_meta(emo).get("release_ms", 300),
                        "client_id": "default",
                        "ts": time.time(),
                        "text": "",
                    })
                if act_raw and act_raw in _ALLOWED_ACTIONS and act_raw != "none":
                    await timeline_send({
                        "type": "action",
                        "action": act_raw,
                        "duration_ms": int(ct.get("duration_ms") or 1400),
                        "client_id": "default",
                        "ts": time.time(),
                    })
                continue

            await google_ready.wait()
            if google_ws is None:
                continue
            send_attempts = 0
            while send_attempts < 2:
                try:
                    if isinstance(data, dict) and "realtime_input" in data:
                        chunks = (data.get("realtime_input") or {}).get("media_chunks") or []
                        if chunks and isinstance(chunks, list):
                            c0 = chunks[0] or {}
                            b64 = c0.get("data") or ""
                            size = len(b64)
                            mime = c0.get("mime_type")
                            rms_val = None
                            if b64:
                                try:
                                    pcm = b64_to_pcm16(b64)
                                    rms_val = float(np.sqrt(np.mean(pcm.astype(np.float32) ** 2)) / 32768.0)
                                except Exception:
                                    rms_val = None
                            if rms_val is None:
                                print(f"➡️ to_google realtime_input mime={mime} b64={size}", flush=True)
                            else:
                                print(f"➡️ to_google realtime_input mime={mime} b64={size} rms={rms_val:.4f}", flush=True)
                        else:
                            print("➡️ to_google realtime_input empty", flush=True)
                    else:
                        print("➡️ to_google", (list(data.keys()) if isinstance(data, dict) else "non-json"), flush=True)
                    await google_ws.send(msg)
                    break
                except websockets.exceptions.ConnectionClosed as exc:
                    send_attempts += 1
                    print("🔥 google_ws.send failed, reconnecting:", exc, flush=True)
                    import traceback; traceback.print_exc()
                    if not await ensure_google_connection():
                        return
                    await google_ready.wait()
                except Exception as e:
                    print("🔥 google_ws.send failed:", repr(e), flush=True)
                    import traceback; traceback.print_exc()
                    return

    _model_turn_count = 0

    async def google_to_browser():
        print("➡️ google_to_browser: enter")
        nonlocal audio_seq, output_buffer, audio_debug_count, end_sent, _model_turn_count
        print("➡️ google_to_browser loop start")

        try:
            async for message in google_ws:

                print("⬅️ google->browser msg prefix:", (message[:120] if isinstance(message,str) else type(message)))
                # Always proxy to browser; ensure text frames so frontend can JSON.parse.
                if isinstance(message, (bytes, bytearray)):
                    message = message.decode("utf-8", "ignore")
                await client_ws.send(message)

                try:
                    data = json.loads(message)
                except Exception:
                    continue
                if data.get("serverContent", {}).get("modelTurn"):
                    _model_turn_count += 1
                    parts = data["serverContent"]["modelTurn"].get("parts", [])
                    inline_flags = []
                    for part in parts:
                        inline = part.get("inlineData") or part.get("inline") or part.get("audioInline")
                        inline_flags.append("Y" if inline else "n")
                    print(f"🧪 modelTurn #{_model_turn_count} parts={len(parts)} inline={'/'.join(inline_flags)}", flush=True)
                if isinstance(message, str) and "inputTranscription" in message:
                    print("📝 inputTranscription raw:", message, flush=True)

                if data.get("error"):
                    print("❗️ google error:", data.get("error"), flush=True)
                if data.get("responseError"):
                    print("❗️ google responseError:", data.get("responseError"), flush=True)

                server_content = data.get("serverContent", {})
                if server_content and audio_debug_count < 10:
                    print("🧩 serverContent keys=", list(server_content.keys()), flush=True)
                    # Debug: покажем полную структуру modelTurn если есть
                    if server_content.get("modelTurn"):
                        mt = server_content["modelTurn"]
                        print(f"🧪 modelTurn keys={list(mt.keys()) if isinstance(mt, dict) else 'not-dict'}", flush=True)
                        if isinstance(mt, dict) and mt.get("parts"):
                            for i, part in enumerate(mt["parts"][:3]):  # первые 3 части
                                print(f"🧪 part[{i}] keys={list(part.keys()) if isinstance(part, dict) else type(part)}", flush=True)
                    audio_debug_count += 1
                if server_content.get("inputTranscription"):
                    print("📝 inputTranscription:", server_content.get("inputTranscription"), flush=True)

                # --- AUDIO (Gemini stream) ---
                model_turn = server_content.get("modelTurn", {})
                parts = model_turn.get("parts", [])
                if parts:
                    end_sent = False
                for p in parts:
                    text_part = p.get("text")
                    if text_part and ("EMOTION_TAG:" in text_part or "ACTION_TAG:" in text_part):
                        print(f"📝 model text part={text_part!r}", flush=True)
                        _, tagged_emotion, tagged_action = extract_tags(text_part)
                        if tagged_emotion:
                            await timeline_send({
                                "type": "emotion",
                                "emotion": tagged_emotion,
                                "attack_ms": emotion_meta(tagged_emotion).get("attack_ms", 180),
                                "release_ms": emotion_meta(tagged_emotion).get("release_ms", 300),
                                "client_id": "default",
                                "ts": time.time(),
                                "text": "",
                            })
                        if tagged_action and tagged_action != "none":
                            print(f"🎬 tagged_action={tagged_action}", flush=True)
                            await timeline_send({
                                "type": "action",
                                "action": tagged_action,
                                "client_id": "default",
                                "ts": time.time(),
                            })
                audio_source = model_turn or server_content
                # --- OUTPUT TRANSCRIPTION -> EMOTION / PHRASE END ---
                out_trans = server_content.get("outputTranscription")
                if out_trans and isinstance(out_trans, dict):
                    txt = out_trans.get("text") or ""
                    finished = bool(out_trans.get("finished"))

                    if txt or finished:
                        print(f"📝 outputTranscription text={txt!r} finished={finished}", flush=True)

                    if txt:
                        output_buffer += txt
                        end_sent = False

                    if finished and output_buffer.strip():
                        output_text = output_buffer.strip()
                        output_buffer = ""

                        clean_text, tagged_emotion, tagged_action = extract_tags(output_text)
                        output_text = clean_text
                        if not output_text and not tagged_emotion and not tagged_action:
                            pass
                        else:
                            emotion = tagged_emotion or analyze_emotion(output_text)
                            meta = emotion_meta(emotion)

                            await timeline_send({
                                "type": "emotion",
                                "emotion": emotion,
                                "attack_ms": meta["attack_ms"],
                                "release_ms": meta["release_ms"],
                                "client_id": "default",
                                "ts": time.time(),
                                "text": output_text,
                            })

                            if tagged_action and tagged_action != "none":
                                print(f"🎬 tagged_action={tagged_action}", flush=True)
                                await timeline_send({
                                    "type": "action",
                                    "action": tagged_action,
                                    "client_id": "default",
                                    "ts": time.time(),
                                })

                            await timeline_send({
                                "type": "phrase_end",
                                "text": output_text,
                                "client_id": "default",
                                "ts": time.time(),
                            })

                            end_payload = {
                                "cmd": "sync",
                                "text": output_text,
                                "emotion": emotion,
                                "visemes": [],
                                "emotion_meta": meta,
                                "action": tagged_action or "none",
                            }
                            try:
                                await client_ws.send(json.dumps({
                                    "serverContent": {"avatar": end_payload},
                                    "avatar": end_payload,
                                }))
                            except Exception:
                                pass
                for inline in iter_inline_data(audio_source):
                    mime_type = (inline.get("mimeType") or inline.get("mime_type") or "").lower()
                    if not mime_type.startswith("audio/"):
                        continue
                    if audio_debug_count <= 3:
                        print("🎛️ inline mimeType=", inline.get("mimeType"), flush=True)
                    if not (mime_type.startswith("audio/pcm") or mime_type.startswith("audio/l16")):
                        if audio_debug_count <= 3:
                            print(f"⚠️ unsupported audio mimeType={mime_type}", flush=True)
                        continue

                    b64_audio = inline.get("data")
                    if not b64_audio:
                        continue
                    print(f"🎧 audio inlineData b64={len(b64_audio)}", flush=True)

                    pcm16 = b64_to_pcm16(b64_audio)
                    amps = compute_amplitudes(pcm16)

                    ready = audio_buffer.add_chunk(b64_audio, amps)
                    if not ready:
                        continue

                    popped = audio_buffer.pop_buffer()
                    if not popped:
                        continue

                    combined_b64, amplitudes, duration_sec = popped

                    # В timeline-sync шлём чанки — там строится timeline (t0 учитывается heartbeat-ом)
                    if _timeline_ws is not None:
                        audio_seq += 1
                        print(f"➡️ timeline_send audio_chunk seq={audio_seq} dur={duration_sec:.3f}", flush=True)
                        await timeline_send({
                            "type": "audio_chunk",
                            "pcm_b64": combined_b64,
                            "duration": duration_sec,
                            "t0_hint": BUFFER_MS / 1000.0,
                            "seq": audio_seq,
                            "client_id": "default",
                            "ts": time.time(),
                        })
                    else:
                        sync_payload = {
                            "cmd": "audio_sync",
                            "t0": None,
                            "duration": duration_sec,
                            "duration_s": duration_sec,
                            "amplitudes": amplitudes,
                            "speaking": True,
                            "buffer_ms": BUFFER_MS,
                            "audio": combined_b64,
                        }
                        await client_ws.send(json.dumps({
                            "serverContent": {"avatar": sync_payload},
                            "avatar": sync_payload,
                        }))
                if server_content.get("generationComplete") or server_content.get("turnComplete"):
                    if _timeline_ws is not None and audio_buffer.total_samples > 0:
                        audio_seq += 1
                        popped = audio_buffer.pop_buffer(force=True)
                        if popped:
                            combined_b64, amplitudes, duration_sec = popped
                            print(f"➡️ timeline_send audio_chunk (flush) seq={audio_seq} dur={duration_sec:.3f}", flush=True)
                            await timeline_send({
                                "type": "audio_chunk",
                                "pcm_b64": combined_b64,
                                "duration": duration_sec,
                                "t0_hint": BUFFER_MS / 1000.0,
                                "seq": audio_seq,
                                "client_id": "default",
                                "ts": time.time(),
                            })
        except websockets.exceptions.ConnectionClosed as exc:
            print("⚠️ google_to_browser disconnected:", exc, flush=True)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            print("⚠️ google_to_browser crashed:", exc, flush=True)
        finally:
            pass



    try:
        # Стартуем browser_to_google (google_to_browser стартанёт после service_url)
        await browser_to_google()

    except websockets.exceptions.ConnectionClosed as e:
        print("🔌 Closed: code=%s reason=%s" % (getattr(e,"code",None), getattr(e,"reason","")), flush=True)
    except Exception as e:
        print("🔥 handler crashed:", repr(e), flush=True)
        import traceback; traceback.print_exc()
    finally:
        BROWSER_CLIENTS.discard(client_ws)

        try:
            if google_to_browser_task is not None:
                google_to_browser_task.cancel()
        except Exception:
            pass
        try:
            if google_ws is not None:
                await google_ws.close()
        except Exception:
            pass


async def index_handler(request):
    return web.FileResponse(os.path.join(_FRONTEND_DIR, "index.html"))

async def static_handler(request):
    rel_path = request.match_info.get("path", "")
    file_path = os.path.join(_FRONTEND_DIR, rel_path)
    if os.path.isdir(file_path):
        file_path = os.path.join(file_path, "index.html")
    if not os.path.exists(file_path):
        return web.Response(status=404, text="Not found")
    return web.FileResponse(file_path)

async def ws_proxy_handler(request):
    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)

    backend_url = f"ws://127.0.0.1:{WS_PORT}/ws"
    async with aiohttp.ClientSession() as session:
        try:
            backend_ws = await session.ws_connect(backend_url)
        except Exception:
            await client_ws.close()
            return client_ws

        async def client_to_backend():
            async for msg in client_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await backend_ws.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await backend_ws.send_bytes(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    await backend_ws.close()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

        async def backend_to_client():
            async for msg in backend_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await client_ws.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await client_ws.send_bytes(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    await client_ws.close()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

        tasks = [
            asyncio.create_task(client_to_backend()),
            asyncio.create_task(backend_to_client()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await backend_ws.close()
        await client_ws.close()
        return client_ws

async def gaze_proxy_handler(request):
    client_ws = web.WebSocketResponse()
    await client_ws.prepare(request)
    print("👁️ gaze proxy connected", flush=True)

    backend_url = "ws://127.0.0.1:8082/gaze-client"
    async with aiohttp.ClientSession() as session:
        try:
            backend_ws = await session.ws_connect(
                backend_url,
                headers={"X-Gaze-Client": "1"},
            )
            print(f"👁️ gaze proxy backend ws={backend_url}", flush=True)
        except Exception:
            print("⚠️ gaze proxy backend connect failed", flush=True)
            await client_ws.close()
            return client_ws

        async def client_to_backend():
            async for msg in client_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await backend_ws.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await backend_ws.send_bytes(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    await backend_ws.close()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

        async def backend_to_client():
            async for msg in backend_ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await client_ws.send_str(msg.data)
                elif msg.type == aiohttp.WSMsgType.BINARY:
                    await client_ws.send_bytes(msg.data)
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    await client_ws.close()
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

        tasks = [
            asyncio.create_task(client_to_backend()),
            asyncio.create_task(backend_to_client()),
        ]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
        for task in pending:
            task.cancel()
        await backend_ws.close()
        await client_ws.close()
        return client_ws

# -----------------------------
# Freesound proxy (preview-only)
# -----------------------------
_SFX_QUERY = {
    "sfx_pop": "cartoon pop",
    "sfx_sparkle": "magic sparkle",
    "sfx_boop": "button click boop",
    "sfx_wave": "water whoosh wave",
    "sfx_spin": "swirl whoosh",
    "sfx_tear": "water drop",
    "sfx_sweat": "sweat drip",
    "sfx_heart": "magic chime",
    "sfx_bubble": "bubble pop",
    "wipe": "swish wipe",
}
_SFX_CACHE = {}
_SFX_TTL_S = 60 * 60 * 12

async def sfx_search_handler(request):
    if not FREESOUND_API_KEY:
        return web.json_response({"error": "missing FREESOUND_API_KEY"}, status=500)
    action = (request.query.get("action") or "").strip().lower()
    q = (request.query.get("q") or "").strip()
    if action and action in _SFX_QUERY:
        q = _SFX_QUERY[action]
    if not q:
        return web.json_response({"error": "missing query"}, status=400)

    now = time.time()
    cache_key = f"{action}:{q}"
    cached = _SFX_CACHE.get(cache_key)
    if cached and (now - cached["ts"]) < _SFX_TTL_S:
        if "items" in cached:
            pick = random.choice(cached["items"])
            return web.json_response({"url": pick["url"], "name": pick["name"], "id": pick["id"]})
        return web.json_response({"url": cached["url"], "name": cached["name"], "id": cached["id"]})

    min_duration = request.query.get("min_duration")
    max_duration = request.query.get("max_duration")
    filter_parts = ['license:"Creative Commons 0"']
    if min_duration or max_duration:
        try:
            min_d = float(min_duration) if min_duration is not None else 0.0
            max_d = float(max_duration) if max_duration is not None else 0.0
            if min_duration and max_duration:
                filter_parts.append(f"duration:[{min_d} TO {max_d}]")
            elif min_duration:
                filter_parts.append(f"duration:[{min_d} TO 999]")
            elif max_duration:
                filter_parts.append(f"duration:[0 TO {max_d}]")
        except ValueError:
            pass

    params = {
        "query": q,
        "fields": "id,name,previews,license",
        "filter": " ".join(filter_parts),
        "page_size": 6,
    }
    headers = {"Authorization": f"Token {FREESOUND_API_KEY}"}
    url = "https://freesound.org/apiv2/search/text/"
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params, headers=headers, timeout=10) as resp:
            if resp.status != 200:
                return web.json_response({"error": "freesound_error", "status": resp.status}, status=502)
            data = await resp.json()

    results = data.get("results") or []
    if not results:
        return web.json_response({"error": "no_results"}, status=404)

    items = []
    for item in results:
        previews = item.get("previews") or {}
        preview_url = (
            previews.get("preview-hq-ogg")
            or previews.get("preview-hq-mp3")
            or previews.get("preview-lq-ogg")
            or previews.get("preview-lq-mp3")
        )
        if not preview_url:
            continue
        items.append({
            "url": preview_url,
            "name": item.get("name"),
            "id": item.get("id"),
        })

    if not items:
        return web.json_response({"error": "no_preview"}, status=404)

    _SFX_CACHE[cache_key] = {"ts": now, "items": items}
    pick = random.choice(items)
    return web.json_response({"url": pick["url"], "name": pick["name"], "id": pick["id"]})

async def main():
    global _gaze_proc
    app = web.Application()
    app.router.add_get("/", index_handler)
    app.router.add_get("/ws", ws_proxy_handler)
    app.router.add_get("/gaze-client", gaze_proxy_handler)
    app.router.add_get("/sfx/search", sfx_search_handler)
    app.router.add_get("/{path:.*}", static_handler)

    http_runner = web.AppRunner(app)
    await http_runner.setup()
    await web.TCPSite(http_runner, "0.0.0.0", HTTP_PORT).start()

    # Start timeline-sync client (optional)
    global _timeline_task
    _timeline_task = asyncio.create_task(_timeline_client_loop())

    # Auto-start gaze worker (optional)
    if os.environ.get("OCTO_GAZE_WORKER_DISABLED") == "1":
        print("👁️ gaze worker disabled in app.py", flush=True)
    else:
        gaze_bin = os.environ.get(
            "OCTO_GAZE_WORKER_BIN",
            "/Users/miguelaprossine/octopuzzler/code/tools/gaze_capture_macos"
        )
        gaze_ws = os.environ.get("OCTO_GAZE_INPUT_WS", f"ws://localhost:{WS_PORT}/gaze-worker")
        if gaze_ws.startswith("http://"):
            gaze_ws = "ws://" + gaze_ws[len("http://"):]
        elif gaze_ws.startswith("https://"):
            gaze_ws = "wss://" + gaze_ws[len("https://"):]
        if gaze_bin and os.path.exists(gaze_bin):
            env = os.environ.copy()
            env["OCTO_GAZE_INPUT_WS"] = gaze_ws
            if "OCTO_MODELS_DIR" not in env:
                default_models = "/Users/miguelaprossine/octopuzzler/models"
                if os.path.exists(default_models):
                    env["OCTO_MODELS_DIR"] = default_models
            try:
                log_path = "/tmp/gaze_worker.log"
                log_fh = open(log_path, "ab", buffering=0)
                _gaze_proc = await asyncio.create_subprocess_exec(
                    gaze_bin,
                    env=env,
                    stdout=log_fh,
                    stderr=log_fh,
                )
                print(f"👁️ gaze worker started: {gaze_bin}", flush=True)
                print(f"👁️ gaze worker log: {log_path}", flush=True)
                if env.get("OCTO_MODELS_DIR"):
                    print(f"👁️ gaze worker models: {env.get('OCTO_MODELS_DIR')}", flush=True)
                print(f"👁️ gaze worker ws: {gaze_ws}", flush=True)
            except Exception as e:
                print(f"⚠️ gaze worker start failed: {e}", flush=True)
        else:
            print("⚠️ gaze worker binary not found; set OCTO_GAZE_WORKER_BIN", flush=True)

    print(f"🌐 http://localhost:{HTTP_PORT}")
    print(f"🔌 ws://localhost:{WS_PORT}")

    async with websockets.serve(
        websocket_handler,
        "0.0.0.0",
        WS_PORT,
        ping_interval=20,
        ping_timeout=20,
        close_timeout=1,
    ):
        await asyncio.Future()

if __name__ == "__main__":
    asyncio.run(main())
