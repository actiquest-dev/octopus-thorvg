# Timeline Sync

`timeline_sync.py` is a lightweight websocket service that synchronises Gemini’s realtime audio/gaze feed with the frontend avatar renderer. It sits alongside `app.py` in `backend/` and exposes a single websocket endpoint on `127.0.0.1:8767`. The core idea is to convert incoming audio chunks, client tags and gaze updates into `render_packet` messages that can be broadcast to every connected browser.

## Components

- **`ClientState`** keeps per-client measurements: smoothed playback delay, emotion/action/gaze targets, timestamps, queue length, etc. It exposes helpers such as `set_emotion`, `set_action`, `set_gaze` and `update_heartbeat`.
- **`TimelineSync`** wraps a `Dict[client_id, ClientState]`. The important method is `build_render_packet`, which:
  - decodes the incoming PCM16 base64 chunk (`decode_s16le_mono`)
  - slices it into jaw and viseme windows, computes RMS/ZCR, and derives jaw, viseme, voice energy and a rough prosody-based emotion
  - applies any tagged emotion/action that was previously set
  - attaches fresh gaze info from `_handle_gaze_frame` while it is still recent
  - packages everything into an `{"cmd": "audio_sync", ...}` render packet.
- **`broadcast`** iterates over all connected websocket clients and forwards JSON payloads; unusable connections are pruned.

## Websocket message flow

`ws_handler` drives the protocol. Every message must be JSON with a `type` field. The supported types are:

1. **`heartbeat`**  
   - Sent from the browser to keep the sync service aware of the playback delay.  
   - Calls `update_heartbeat`, then replies with the current state: `t0_estimate_s`, current emotion, and last audio `seq`.

2. **`emotion`**  
   - Usually emitted when the backend sees an emotion tag.  
   - Updates the target emotion stored in `ClientState`.  
   - Responds with the current state so the frontend knows the new emotion immediately.

3. **`action`**  
   - Drives full-body gestures (`wave`, `point`, etc.).  
   - Calls `set_action`, broadcasts a `render_packet` right away (so the avatar can react instantly), and replies with the refreshed state.

4. **`gaze`**  
   - Carries normalized `(x, y, blink)` from the frontend’s gaze worker.  
   - Updates `ClientState` and broadcasts the gaze packet so all browsers can reposition eyes/head.

5. **`reset_audio`**  
   - Sent when a new turn begins (from `app.py` when `client_content` arrives).  
   - Resets the per-client queues and replies with `seq=0` so the renderer knows the timeline restarted.

6. **`audio_chunk`**  
   - The most important message. It contains base64 PCM, sequence number, duration, and a `t0_hint`.  
   - If `seq` is newer than the stored `last_seq`, `build_render_packet` builds jaw/viseme/emotion/action/gaze data.  
   - The resulting packet is broadcast as a `render_packet` so every browser receives a unified avatar command.

## Integration with `app.py`

- `app.py` maintains `_timeline_ws` and the helper `timeline_send(payload)` – a best-effort forwarder to the sync service that quietly drops messages when the connection is missing.  
- `app.py` calls `timeline_send` for:
  - vehicle resets (`type: "reset_audio"`),
  - timeline-tagged emotions and actions,
  - processed viseme/audio data (`type: "audio_chunk"`), typically after `AudioBuffer.pop_buffer()` yields a chunk.
- `_timeline_client_loop()` in `app.py` connects back to the sync service, receives `render_packet` responses, and echoes them to every connected browser (`BROWSER_CLIENTS`). That loop keeps `app.py` and the frontend in sync even if multiple tabs are open.

## Running the service

1. `python backend/timeline_sync.py` (standalone)  
2. Or start `backend/run.py` – it will spawn `timeline_sync.py`, the gaze worker, and `app.py`.

The service logs connection lifecycle events (lines like `[timeline-sync] listening…`, `[timeline-sync] action=…`, and `[timeline-sync] render_packet seq=…`), which are good indicators when debugging stuttering or dropped audio.

## Troubleshooting notes

- Look at `[timeline-sync] audio_chunk` logs to ensure `seq` strictly increases; stale chunks are dropped.  
- Emotion/action/gaze commands are echoed immediately so the frontend can react without waiting for audio packets.  
- If gaze or viseme updates lag, verify that the browser actually sends enough `gaze` frames (see `sendGazeFrame` throttling in `frontend/index.html`) and that `build_render_packet` still sees `st.gaze_ts` inside its 1.5 s freshness window.  
- When restarting services, keep in mind `timeline_sync.py` binds to 8767; ensure there isn’t another listener occupying that port before launching `run.py`.  
