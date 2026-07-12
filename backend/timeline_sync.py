import asyncio
import base64
import json
import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import numpy as np
import websockets


# -----------------------------
# Audio utils (PCM16 mono)
# -----------------------------
def decode_s16le_mono(pcm_b64: str) -> np.ndarray:
    if not pcm_b64:
        return np.zeros((0,), dtype=np.int16)
    raw = base64.b64decode(pcm_b64)
    return np.frombuffer(raw, dtype=np.int16)


def rms(x: np.ndarray) -> float:
    if x.size == 0:
        return 0.0
    y = x.astype(np.float32) / 32768.0
    return float(np.sqrt(np.mean(y * y) + 1e-12))


def zcr(x: np.ndarray) -> float:
    if x.size < 2:
        return 0.0
    y = x.astype(np.float32)
    s = np.sign(y)
    return float(np.mean(s[1:] != s[:-1]))


def slice_parts(samples: np.ndarray, steps: int) -> List[np.ndarray]:
    if samples.size == 0:
        return [samples]
    steps = max(1, int(steps))
    n = samples.size
    k = max(1, n // steps)
    out = []
    for i in range(steps):
        a = i * k
        b = (i + 1) * k if i < steps - 1 else n
        out.append(samples[a:b])
    return out


# -----------------------------
# Jaw + proxy visemes
# -----------------------------
def amp_to_jaw(a: float) -> float:
    # мягкая нелинейность, чтобы не забивалось в 1.0
    # a ~ [0..0.35] обычно
    x = max(0.0, min(1.0, a * 3.2))
    x = math.pow(x, 0.8)
    return float(max(0.0, min(1.0, x)))


def proxy_viseme(a: float, zz: float) -> str:
    # 3-4 грубые формы: REST, A, O, F/V (условно)
    if a < 0.02:
        return "REST"
    # больше zcr -> более “шумные/согласные”
    if zz > 0.25 and a > 0.04:
        return "F"
    # округление vs раскрытие
    if a > 0.18:
        return "A"
    return "O"


# -----------------------------
# Emotion layer (slow)
# -----------------------------
@dataclass
class EmotionState:
    current: str = "neutral"
    target: str = "neutral"
    attack_ms: int = 220
    release_ms: int = 380
    _t_last: float = 0.0

    def set(self, emo: str, attack_ms: Optional[int] = None, release_ms: Optional[int] = None):
        self.target = emo or "neutral"
        if attack_ms is not None:
            self.attack_ms = int(attack_ms)
        if release_ms is not None:
            self.release_ms = int(release_ms)

    def step(self) -> str:
        # Для canvas-команд нам не нужен “процент”, но нужен стабильный “current”
        # Здесь делаем простую логику: переключаем current на target с задержкой.
        # В клиенте будет сглаживание по emotionMeta.
        now = asyncio.get_event_loop().time()
        if self._t_last == 0.0:
            self._t_last = now
            self.current = self.target
            return self.current

        dt_ms = (now - self._t_last) * 1000.0
        self._t_last = now

        if self.current != self.target:
            # Вход в эмоцию быстрее (attack), выход медленнее (release)
            thr = self.attack_ms if self.target != "neutral" else self.release_ms
            if dt_ms >= thr:
                self.current = self.target
        return self.current

    def meta(self) -> dict:
        return {"attack_ms": int(self.attack_ms), "release_ms": int(self.release_ms)}


@dataclass
class ClientState:
    playback_delay_s_smooth: Optional[float] = 0.30
    last_seq: int = 0
    emotion: EmotionState = field(default_factory=EmotionState)
    queued_audio_s: float = 0.0
    last_tag_ts: float = 0.0
    action: Optional[str] = None
    action_until_ts: float = 0.0
    gaze_x: float = 0.0
    gaze_y: float = 0.0
    gaze_blink: bool = False
    gaze_ts: float = 0.0


class TimelineSync:
    def __init__(self):
        self.clients: Dict[str, ClientState] = {}

    def get(self, client_id: str) -> ClientState:
        if client_id not in self.clients:
            self.clients[client_id] = ClientState()
        return self.clients[client_id]

    def update_heartbeat(self, client_id: str, playback_delay_s: float):
        st = self.get(client_id)
        v = float(max(0.0, min(1.5, playback_delay_s)))
        # EMA сглаживание чтобы не дёргалось
        if st.playback_delay_s_smooth is None:
            st.playback_delay_s_smooth = v
        else:
            st.playback_delay_s_smooth = 0.80 * st.playback_delay_s_smooth + 0.20 * v

    def set_emotion(self, client_id: str, emotion: str, attack_ms: Optional[int] = None, release_ms: Optional[int] = None):
        st = self.get(client_id)
        st.emotion.set(emotion, attack_ms=attack_ms, release_ms=release_ms)
        st.last_tag_ts = asyncio.get_event_loop().time()

    def set_action(self, client_id: str, action: str, duration_ms: int = 1400):
        st = self.get(client_id)
        st.action = action
        st.action_until_ts = asyncio.get_event_loop().time() + (duration_ms / 1000.0)

    def set_gaze(self, client_id: str, gaze_x: float, gaze_y: float, blink: bool = False):
        st = self.get(client_id)
        st.gaze_x = float(max(-1.0, min(1.0, gaze_x)))
        st.gaze_y = float(max(-1.0, min(1.0, gaze_y)))
        st.gaze_blink = bool(blink)
        st.gaze_ts = asyncio.get_event_loop().time()

    def build_render_packet(self, client_id: str, seq: int, pcm_b64: str, duration_s: float, t0_hint: float) -> dict:
        st = self.get(client_id)
        samples = decode_s16le_mono(pcm_b64)

        jaw_step_ms = 16
        vis_step_ms = 50
        jaw_steps = max(1, int(round((duration_s * 1000.0) / jaw_step_ms)))
        vis_steps = max(1, int(round((duration_s * 1000.0) / vis_step_ms)))
        jaw_segs = slice_parts(samples, jaw_steps)
        vis_segs = slice_parts(samples, vis_steps)

        jaw_env: List[float] = []
        rms_vals: List[float] = []
        zcr_vals: List[float] = []
        prox: List[str] = []
        ema = None
        alpha = 0.55  # light smoothing to soften rapid jaw changes
        for seg in jaw_segs:
            a = rms(seg)
            zz = zcr(seg)
            rms_vals.append(a)
            zcr_vals.append(zz)
            j = amp_to_jaw(a)
            ema = j if ema is None else (alpha * j + (1.0 - alpha) * ema)
            jaw_env.append(float(ema))
        for seg in vis_segs:
            a = rms(seg)
            zz = zcr(seg)
            prox.append(proxy_viseme(a, zz))

        # Timeline position for this chunk (relative to stream start)
        start_s = float(st.queued_audio_s)
        st.queued_audio_s += float(duration_s)

        def prosody_emotion() -> str:
            if not rms_vals:
                return "neutral"
            avg_rms = float(np.mean(rms_vals))
            std_rms = float(np.std(rms_vals))
            avg_zcr = float(np.mean(zcr_vals)) if zcr_vals else 0.0
            # Tempo proxy: count energy rises per second.
            peaks = 0
            for i in range(1, len(rms_vals)):
                if rms_vals[i] > 0.04 and rms_vals[i] > rms_vals[i - 1]:
                    peaks += 1
            tempo_hz = peaks / max(0.001, duration_s)
            arousal = min(1.0, (avg_rms * 3.0) + (std_rms * 2.0) + (avg_zcr * 0.5) + (tempo_hz * 0.02))
            if arousal < 0.18:
                return "calm"
            if arousal < 0.45:
                return "neutral"
            return "excited"

        tag_recent = (asyncio.get_event_loop().time() - st.last_tag_ts) <= 1.5
        prosody = prosody_emotion()
        emo = st.emotion.step()
        # Use tag-driven emotion briefly; fall back to prosody for real-time feel.
        if tag_recent and st.emotion.target != "neutral":
            emo_value = emo
        else:
            emo_value = prosody
        st.last_seq = seq

        action_value = None
        now_ts = asyncio.get_event_loop().time()
        if st.action:
            if now_ts > st.action_until_ts:
                st.action = None
            else:
                action_value = st.action
                # Extend action while audio is flowing for "mode" actions.
                if action_value in {"sing", "laugh", "whisper", "shout"}:
                    st.action_until_ts = max(
                        st.action_until_ts,
                        now_ts + float(duration_s) + 0.12,
                    )

        packet = {
            "cmd": "audio_sync",
            "duration_s": float(duration_s),
            "start_s": float(start_s),
            "jaw": {"step_ms": jaw_step_ms, "values": jaw_env},
            "viseme_proxy": {"step_ms": vis_step_ms, "values": prox},
            "emotion": {
                "value": emo_value,
                "attack_ms": st.emotion.meta().get("attack_ms", 180),
                "release_ms": st.emotion.meta().get("release_ms", 300),
            },
            "action": action_value or "none",
            "speaking": True,
        }

        # Attach gaze if it's fresh (last ~1.5s)
        if st.gaze_ts and (now_ts - st.gaze_ts) <= 1.5:
            packet["gaze"] = {
                "x": st.gaze_x,
                "y": st.gaze_y,
                "blink": st.gaze_blink,
            }
        return packet

    @staticmethod
    def render_packet_to_avatar(packet: dict) -> dict:
        return packet


SYNC = TimelineSync()
CLIENTS = set()


async def broadcast(payload: dict) -> None:
    dead = []
    msg = json.dumps(payload)
    for c in list(CLIENTS):
        try:
            await c.send(msg)
        except Exception:
            dead.append(c)
    for d in dead:
        CLIENTS.discard(d)


async def ws_handler(ws):
    CLIENTS.add(ws)
    try:
        async for msg in ws:
            try:
                data = json.loads(msg)
            except Exception:
                continue

            t = data.get("type")

            if t == "heartbeat":
                cid = data.get("client_id", "default")
                SYNC.update_heartbeat(cid, float(data.get("playback_delay_s", 0.30)))
                st = SYNC.get(cid)
                await ws.send(json.dumps({
                    "type": "state",
                    "client_id": cid,
                    "t0_estimate_s": st.playback_delay_s_smooth,
                    "emotion": st.emotion.current,
                    "seq": st.last_seq,
                }))
                continue

            if t == "emotion":
                cid = data.get("client_id", "default")
                emo = str(data.get("emotion", "neutral"))
                attack_ms = data.get("attack_ms", None)
                release_ms = data.get("release_ms", None)
                SYNC.set_emotion(cid, emo, attack_ms=attack_ms, release_ms=release_ms)
                st = SYNC.get(cid)
                await ws.send(json.dumps({
                    "type": "state",
                    "client_id": cid,
                    "t0_estimate_s": st.playback_delay_s_smooth,
                    "emotion": st.emotion.current,
                    "seq": st.last_seq,
                }))
                continue

            if t == "action":
                cid = data.get("client_id", "default")
                action = str(data.get("action", "none"))
                dur_ms = int(data.get("duration_ms", 1400))
                if action != "none":
                    print(f"[timeline-sync] action={action} dur_ms={dur_ms}", flush=True)
                    SYNC.set_action(cid, action, duration_ms=dur_ms)
                    # Emit an immediate render packet so the client can trigger a gesture
                    await broadcast({
                        "type": "render_packet",
                        "client_id": cid,
                        "seq": SYNC.get(cid).last_seq,
                        "packet": {
                            "cmd": "action",
                            "action": action,
                            "duration_ms": dur_ms,
                        },
                    })
                await ws.send(json.dumps({
                    "type": "state",
                    "client_id": cid,
                    "t0_estimate_s": SYNC.get(cid).playback_delay_s_smooth,
                    "emotion": SYNC.get(cid).emotion.current,
                    "seq": SYNC.get(cid).last_seq,
                }))
                continue

            if t == "gaze":
                cid = data.get("client_id", "default")
                gaze = data.get("gaze", {}) or {}
                try:
                    gx = float(gaze.get("x", 0.0))
                    gy = float(gaze.get("y", 0.0))
                except Exception:
                    gx, gy = 0.0, 0.0
                blink = bool(gaze.get("blink", False))
                SYNC.set_gaze(cid, gx, gy, blink=blink)
                await broadcast({
                    "type": "render_packet",
                    "client_id": cid,
                    "seq": SYNC.get(cid).last_seq,
                    "packet": {
                        "cmd": "gaze",
                        "gaze": {"x": gx, "y": gy, "blink": blink},
                    },
                })
                continue

            if t == "reset_audio":
                cid = data.get("client_id", "default")
                st = SYNC.get(cid)
                st.queued_audio_s = 0.0
                st.last_seq = 0
                print(f"[timeline-sync] reset_audio client_id={cid}", flush=True)
                await ws.send(json.dumps({
                    "type": "state",
                    "client_id": cid,
                    "t0_estimate_s": st.playback_delay_s_smooth,
                    "emotion": st.emotion.current,
                    "seq": st.last_seq,
                }))
                continue

            if t == "audio_chunk":
                cid = data.get("client_id", "default")
                seq = int(data.get("seq", 0))
                pcm_b64 = data.get("pcm_b64") or ""
                duration_s = float(data.get("duration", 0.30))
                t0_hint = float(data.get("t0_hint", 0.30))
                print(
                    f"[timeline-sync] audio_chunk seq={seq} pcm_b64={len(pcm_b64)} dur={duration_s:.3f} t0={t0_hint:.3f}",
                    flush=True,
                )

                st = SYNC.get(cid)
                if seq <= st.last_seq:
                    print(f"[timeline-sync] drop audio_chunk seq={seq} last_seq={st.last_seq}", flush=True)
                    continue

                packet = SYNC.build_render_packet(cid, seq, pcm_b64, duration_s, t0_hint)
                avatar = SYNC.render_packet_to_avatar(packet)

                await broadcast({
                    "type": "render_packet",
                    "client_id": cid,
                    "seq": seq,
                    "packet": avatar,
                })
                print(
                    f"[timeline-sync] render_packet seq={seq} jaw_len={len(avatar.get('jaw', {}).get('values', []))}",
                    flush=True,
                )
                continue
    finally:
        CLIENTS.discard(ws)


async def main():
    host = "127.0.0.1"
    port = 8767
    print(f"[timeline-sync] listening on ws://{host}:{port}")
    async with websockets.serve(
        ws_handler,
        host,
        port,
        ping_interval=20,
        ping_timeout=20,
        max_size=16 * 1024 * 1024
    ):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
