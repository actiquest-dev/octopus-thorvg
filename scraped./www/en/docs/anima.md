# ANIMA — Adaptive Neural Interface for Motion & Animation

**Technical Specification v2.4**

**Project:** Real-time generative avatar + vector worlds with neural control and parameter synthesis
**Date:** January 17, 2026
**Status:** Consolidated Architecture Specification (rewrite)

---

## 0. What this is

ANIMA is a real-time animation system where the server generates **a JSON control stream** and the client renders frames locally.

Two product modes share the same architecture:

1. **Avatar Mode** — stylized 2D avatar (face/body/effects) with neural parameter synthesis.
2. **Vector Worlds Mode** — interactive physical 2D worlds rendered on Canvas/WebGL from streamed vector/scene commands.

ANIMA does **not** stream video. It streams **instructions and state deltas**.

---

## 1. Executive Summary

ANIMA **генерирует, синхронизирует и рендерит в реальном времени векторные миры** — интерактивные физические сцены и аватары, описанные потоками векторных команд и параметров, а не видеокадрами.

ANIMA работает как распределённая система:

* сервер **генерирует и оркестрирует** физику, события и векторные инструкции;
* клиент **исполняет и рисует** их локально с гарантированной временной непрерывностью.

ANIMA is a **real-time neural animation system** that synthesizes stylized 2D avatar animation and interactive vector worlds from multimodal inputs (speech, emotion, context, interaction).

**Core Capabilities**

* **JSON control stream** (~0.2–2 KB/frame typical, delta-encoded)
* **Client-side rendering** via ANIMA SDK (WebGL2, optional Canvas2D)
* **Neural parameter synthesis** (flow-based, 1-pass realtime)
* **Procedural + physics runtime** for continuity and deterministic rendering
* **Emotion-aware speech** integration (Hume EVI for MVP)
* **30 FPS perception target**, **50–100ms end-to-end latency target**

**Key Architecture Decisions**

* Server generates *control + parameter deltas*, client renders frames.
* Model generates **parameters and control ops**, not pixels.
* ANIMA SDK is **open-source** and is the primary runtime (no Live2D dependency).
* Worlds are **physics-first**: deterministic simulation + streamed control.

**Economic Advantage (principle)**

* Server does inference and control, not rendering/encoding.
* Bandwidth is tens of KB/s, not Mbps.

---

## 2. System Architecture

### 2.1 Core Principle: JSON, Not Video

```
┌─────────────────────────────────────────────────────────────┐
│                       ANIMA BACKEND                         │
│                                                             │
│  Inputs (voice/emotion, text, interaction)  →  Models        │
│  ┌─────────────┐     ┌──────────────────┐     ┌──────────┐  │
│  │ Audio/Pros. │ --> │ ANIMA Models     │ --> │ JSON      │  │
│  │ Emotion     │     │ (Avatar+World)   │     │ Stream    │  │
│  │ Context     │     └──────────────────┘     └──────────┘  │
│                                                             │
└───────────────────────────────────────────────┬─────────────┘
                                                │
                         WebSocket/WebRTC       │  delta stream
                                                ▼\
┌─────────────────────────────────────────────────────────────┐
│                        CLIENT RUNTIME                        │
│                                                             │
│  ┌─────────────┐     ┌──────────────────┐     ┌──────────┐  │
│  │ JSON decode │ --> │ ANIMA SDK        │ --> │ Canvas/   │  │
│  │ + merge     │     │ (Render+Physics) │     │ Display   │  │
│  └─────────────┘     └──────────────────┘     └──────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 Responsibilities: Server vs Client

| Server (ANIMA Backend)                              | Client (ANIMA SDK)                          |
| --------------------------------------------------- | ------------------------------------------- |
| Receives voice/emotion (MVP: Hume)                  | Receives JSON deltas                        |
| Runs neural inference                               | Maintains local state buffer                |
| Emits control ops + parameter deltas                | Physics simulation (if enabled client-side) |
| Compresses and streams                              | Interpolation / easing                      |
| Optional authoritative physics (server-side worlds) | Rendering (WebGL2/Canvas2D)                 |
| **No video encoding**                               | **Full frame rendering**                    |

### 2.3 Two Execution Topologies (choose per product)

**Topology A — Avatar-first (recommended MVP)**

* Server: neural parameters + events
* Client: render + procedural micro-motion

**Topology B — World-authoritative (vector worlds with physics)**

* Server: authoritative physics + world diffs (deterministic)
* Client: render-only (thin)

Both use the **same JSON control stream contract**.

---

## 3. Inputs

### 3.1 Voice, Emotion, Prosody (MVP: Hume EVI)

**Why Hume for MVP**

* strong voice-emotion signal
* low-latency WebSocket integration
* saves months of audio pipeline work

**Hume → ANIMA payload (conceptual)**

```json
{
  "audio_chunk": "...",
  "transcript": "Hello world",
  "emotions": {"joy": 0.7, "excitement": 0.4},
  "prosody": {"pitch": 1.2, "energy": 0.8, "tempo": 1.0}
}
```

### 3.2 Text and Context

* System prompt / scene intent
* Character identity (avatar ID)
* Environment presets (world templates)

### 3.3 Interaction

* click/touch
* game events
* physics triggers
* dialogue tags (Ink, etc.)

### 3.4 Gaze & Attention (ANIMA-SENSE, on-device)

ANIMA supports **native gaze and attention signals** extracted directly on the client device.

Gaze is treated as a **perception signal**, not a control command. It represents where the user’s attention is directed on the screen, not absolute eye-tracking in 3D space.

**Key properties:**

* computed fully on-device
* no raw video frames sent to server
* bounded, confidence-weighted signal
* integrated through ANIMA-SENSE

**Implementation:**

* Portable **C++ library**
* Built on **TFLite + BlazeFace / FaceMesh**
* Compiled to **WASM (browser)**, **iOS**, **Android**, **desktop**

**Client-side pipeline:**

```
Camera frame (downscaled)
  → Face detection (BlazeFace)
  → Face / eye landmarks
  → Head pose estimation
  → Screen-space gaze projection
  → Confidence estimation
```

**Output example (client → server):**

```json
{
  "t": 41233,
  "gaze": {
    "screen_xy": [0.61, 0.43],
    "confidence": 0.88,
    "blink": 0,
    "head_pose": {"yaw": 0.07, "pitch": -0.04, "roll": 0.01}
  }
}
```

**Rates:**

* Gaze inference: 10–15 Hz (mobile), up to 20–30 Hz (desktop)
* Network emission: 10–20 Hz

Raw camera frames **never leave the device** unless explicitly enabled for debugging.

Gaze is merged server-side via ANIMA-SENSE and influences the world **only through policy**, never directly through physics or rendering.

* click/touch
* game events
* physics triggers
* dialogue tags (Ink, etc.)

---

## 4. ANIMA SDK (Client Runtime)

### 4.1 Why not Live2D as the core runtime

Live2D is useful for asset import compatibility, but it is not the system core.

Key reasons:

* licensing constraints
* limited extensibility for neural blending
* unpredictable performance and closed format coupling

### 4.2 SDK Modules

```
ANIMA SDK
├─ Asset Pipeline
│  ├─ Import: Live2D (.moc3), Spine, PSD/SVG
│  ├─ Convert → .anima (open format)
│  └─ Build: meshes, rigs, materials, hitboxes
├─ Animation Runtime
│  ├─ State store (layered)
│  ├─ JSON merge + validation
│  ├─ Interpolation / easing
│  ├─ Event system
│  └─ Profiler (frame time, budgets)
├─ Deformation
│  ├─ GPU skinning
│  ├─ Blend shapes
│  ├─ IK (optional)
│  └─ Constraint solver hooks
├─ Physics (optional)
│  ├─ Rigid bodies
│  ├─ Soft bodies (rope/cloth)
│  └─ Particles (visual + physical)
└─ Rendering
   ├─ WebGL2 compositor
   ├─ Vector renderer (Canvas2D or WebGL)
   ├─ PostFX (glow, grain)
   └─ Output canvas / render-to-texture
```

### 4.3 Performance Contract (client)

* Render cadence target: **30 FPS perception**
* Budget governor:

  * reduce particles
  * reduce path complexity (LOD)
  * reduce postFX
  * keep motion continuity

---

## 5. Models Overview

ANIMA is not one monolith. It is a set of realtime components with strict budgets.

### 5.1 ANIMA-AVATAR (neural parameter synthesis)

* predicts avatar parameters (face/body/effects) in one pass
* conditioned on audio/emotion/context/history

### 5.2 ANIMA-WORLD (world controller)

* interprets intents and events
* emits world control ops (spawn, forces, fields, constraints)
* mediates gameplay-like interactions

### 5.3 ANIMA-PHYS (authoritative physics)

* server-authoritative deterministic simulation
* produces physics events (contacts, triggers) and authoritative transforms

### 5.4 ANIMA-DRAW (render compiler)

* converts authoritative world state + avatar state into render-layer deltas
* owns level-of-detail (LOD) and render budgets

### 5.5 ANIMA-SYNC (timeline manager)

* the timeline itself: buffering, alignment, ordering, snapshots
* compiles multi-stream inputs into coherent `t_play` state

### 5.6 ANIMA-SENSE (client perception + interaction)

ANIMA-SENSE is a **client-side sensing and interaction layer** (C++/TFLite) that turns device inputs into normalized events.

Key responsibility: **it can trigger world interactions** (like a game), but it does so by emitting **interaction intents** into the timeline, not by mutating the authoritative world state locally.

Examples of ANIMA-SENSE outputs:

* `gaze_ray` (where user looks)
* `gaze_select` (dwells on object → select)
* `pointer_down/up`, `drag`
* `imu_impulse` (shake)
* `tilt_vector`
* `camera_observations` (optional)

These intents flow: **SENSE → SYNC → WORLD → PHYS → DRAW**.

---

## 6. Model Architecture — ANIMA (URSPM Core)

### 6.1 Role

ANIMA is the realtime core that turns inputs into **control + parameter deltas** under a fixed cadence and latency budget.

ANIMA does **not** output pixels. It outputs:

* semantic control ops
* animation parameters
* deltas relative to previous state

### 6.2 Execution Model

Per tick:

1. consume latest audio/emotion/prosody slice + context
2. fuse with short history
3. single forward pass
4. emit JSON delta message

Missing a tick must be recoverable; blocking the runtime is not allowed.

### 6.3 Renderer awareness

ANIMA is aware of the target runtime limits:

* parameter ranges and couplings
* per-layer cost
* masks for skipping inactive layers

---

## 7. Avatar Mode

### 7.1 What “GenAI” means here

ANIMA generates **parameters**, not pixels.

Rules baseline:

* phoneme → mouth open (lookup)

ANIMA:

* (audio + emotion + context + history) → all parameters coherently

### 7.2 Parameter Space (v2.4 baseline)

A compact space for MVP, extendable later.

| Category               | Dim     |
| ---------------------- | ------- |
| Mouth                  | 8       |
| Eyes                   | 10      |
| Brows                  | 8       |
| Emotion blend          | 10      |
| Face misc              | 8       |
| Head transform         | 6       |
| Body                   | 30      |
| Hands (simplified)     | 20      |
| Breathing              | 4       |
| Effects (avatar-local) | 20      |
| Reserved               | 46      |
| **Total**              | **170** |

### 7.3 Flow-based Parameter Generator (1-pass)

**Inputs**

* Z_audio (phonemes/prosody/emotion)
* Z_context (avatar/scene)
* Z_history (EMA of previous parameters)

**Core**

* single-pass flow/velocity network
* predicts next parameters or delta

**Outputs**

* full state or delta in the 170D space

### 7.4 Procedural Layer (client-side)

Some motion must be deterministic and cheap:

* blink
* idle sway
* breathing micro-motion
* simple springs

Neural output sets targets; procedural layer fills microstructure.

---

## 8. Vector Worlds Mode

### 8.1 Goal

Simulate a physical 2D world and render it on Canvas/WebGL with a thin stream.

### 8.2 Two world architectures

**World A — Server authoritative (recommended for real physics)**

* server simulates physics at 60Hz
* server streams transforms + spawn/despawn + style updates
* client renders deterministically

**World B — Client authoritative (lighter infra, less consistent)**

* server streams control ops (forces/events)
* client simulates physics
* needs anti-cheat if multiplayer

Choose A for correctness, B for cost/iteration.

### 8.3 ANIMA-WORLD: World Control Model

ANIMA-WORLD outputs a **World Control Stream**:

* apply_impulse / apply_force
* set_field (wind, gravity)
* set_constraint (rope, spring)
* set_emitter (particles)
* spawn/despawn objects
* camera moves
* style tokens

Per-frame geometry generation is avoided. Geometry changes are event-based.

### WorldOps vs DrawOps (responsibility split)

| Dimension          | **WorldOps (HardOps)**                                                       | **DrawOps (VisualOps)**                                                                  |
| ------------------ | ---------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| Purpose            | Mutate **authoritative simulation** (physics + gameplay state)               | Mutate **vector scene graph / rendering** (paths, styles, layers)                        |
| Ownership          | **Server-authoritative** only                                                | Server-generated, client-rendered (may include client-local overlays)                    |
| Determinism        | **Strict** (replayable from snapshots + deltas)                              | **Strict for shared visuals**; client-local overlays may be non-authoritative            |
| Timing             | Evaluated on **world tick** (e.g., 60Hz)                                     | Applied on **render tick** (e.g., 30Hz) with interpolation                               |
| Allowed changes    | Forces, impulses, constraints, spawn/despawn physics bodies, gameplay events | Create/update/delete vector objects, styles, gradients, layer transforms, camera offsets |
| Forbidden changes  | Any draw/paint commands                                                      | Any physics mutation (collisions, forces, joints, mass)                                  |
| Frequency guidance | Continuous but bounded by budgets                                            | **Geometry event-based**, transforms/params realtime                                     |
| Validation         | Schema + budgets + idempotency + safety guard                                | Schema + complexity caps + layer/domain guard                                            |
| Failure mode       | Snapshot/replay or buffer growth (never drop critical)                       | Drop low-priority visuals; preserve continuity                                           |

---

## 9. Realtime Animation via JSON Control Stream

---

## 9A. Control Loop & Tick Model

### 9A.1 Fundamental clocks

ANIMA operates on **multiple coordinated clocks**, each with a strict responsibility:

* **World Tick** — fixed-step authoritative simulation clock

  * Typical: `60 Hz`
  * Runs physics, collision detection, world state updates
  * Fully deterministic and replayable

* **Render Tick** — perceptual rendering cadence

  * Typical: `30 FPS perception target`
  * Runs interpolation, easing, draw submission
  * Must never block or backpressure World Tick

* **Sense Tick** — sensor ingestion cadence

  * Variable (10–120 Hz depending on sensor)
  * Gaze, IMU, audio features, device signals

---

### 9A.2 Server-side control loop

At each **World Tick (k)**:

1. **Collect inputs**

   * Latest `world_state(k-1)` snapshot
   * Accumulated `events(k-1..k)`
   * `sense_digest_soft(k)` from ANIMA-FUSE

2. **WPOL evaluation**

   * Apply gating and policies
   * Compile WorldOps (Hard) + DrawOps (Visual)
   * Enforce budgets and determinism

3. **Physics step**

   * Apply HardOps
   * Advance physics by fixed `dt`

4. **State commit**

   * Produce `world_state(k)`
   * Emit deltas + optional snapshots

---

### 9A.3 Client-side control loop

On the client:

* **Authoritative stream consumption**

  * Merge incoming WorldOps / DrawOps deltas
  * Maintain buffered state per stream (ANIMA-SYNC)

* **Render loop (requestAnimationFrame)**

  * Sample `T_play_hard` and `T_play_soft`
  * Interpolate transforms and parameters
  * Submit vector draw calls

* **Local perception overlays**

  * Apply client-only pseudo-volume
  * Apply gaze/tilt parallax
  * Never mutate authoritative state

---

### 9A.4 Decoupling guarantees

Key invariants:

* World Tick **never waits** for rendering or network
* Rendering **never blocks** physics
* Sense input **never rewinds** authoritative time
* Missed frames degrade visuals, not correctness

---

### 9A.5 Practical consequence

This loop guarantees:

* Stable physics under jitter
* Continuous motion under packet loss
* Predictable CPU/GPU budgets
* Clean separation between *simulation* and *perception*

---

## 9B. State Model & Snapshots

### 9B.1 State layers

ANIMA maintains **layered state** so multiple streams can update different parts without collisions.

* **Authoritative State (Hard)**

  * World physics state (bodies, joints, constraints)
  * Canonical object transforms
  * Canonical lifecycle (spawn/despawn)
  * Critical events (collisions, triggers)

* **Presentation State (Visual)**

  * Vector scene graph (paths, shapes, text, styles)
  * Layer transforms (pseudo-volume/parallax)
  * Camera offsets
  * VFX emitters and style tokens

* **Perception Overlay (Local)**

  * Device-specific gaze/tilt offsets
  * Accessibility/UI overlays
  * Debug overlays
  * Never mutates authoritative state

---

### 9B.2 Snapshot + Delta contract

Streaming is composed of:

* ``: full checkpoint of a state slice
* ``: incremental updates relative to the latest applied snapshot

Rules:

* Deltas are applied **in-order per stream**.
* Snapshots are **re-anchoring points** and can be applied at any time.
* If a delta cannot be applied safely, the client requests/awaits a snapshot (or server pushes one).

---

### 9B.3 Snapshot cadence (guideline)

* Hard world snapshots: every **0.5–2.0s** (or on large topology changes)
* Visual snapshots: every **2–5s** (or on scene reload)
* Always push a snapshot after:

  * mass spawn/despawn
  * constraint graph changes
  * scene template switch

---

### 9B.4 Re-anchor without visual jumps

When a snapshot arrives late or conflicts with local interpolation:

* **Hard state** is corrected immediately at `T_play_hard`.
* **Visual state** is corrected with a short blend window (e.g., 50–150ms) to avoid popping.
* Client keeps rendering continuously; corrections never stall the render loop.

---

### 9B.5 Integrity and debugging hooks

Each stream carries minimal integrity metadata:

* `stream_id`, `seq`, `t_authoritative`, `t_sent`
* optional `state_hash` for hard snapshots

This enables:

* desync detection
* replay and deterministic debugging
* per-stream health metrics in ANIMA-SYNC

---

## 9C. Determinism Contract

### 9C.1 Why determinism matters

ANIMA operates real-time, multi-stream, and server-authoritative. Determinism is required so that:

* authoritative corrections are rare and small
* replay and debugging are possible
* visual continuity survives network jitter
* neural solvers remain controllable

Determinism is enforced **per layer**, not globally.

---

### 9C.2 What MUST be deterministic

The following components are strictly deterministic on the server:

* World state transitions (ANIMA-PHYS solver)
* Object lifecycle (spawn / despawn)
* Constraint graph updates
* Collision events and triggers
* Time advancement (`dt` stepping)

Rules:

* Fixed-step integration (e.g. 60Hz)
* No hidden randomness
* Any randomness must be explicitly seeded and part of state

---

### 9C.3 What MAY be non-deterministic

The following are allowed to be non-deterministic or approximate:

* Visual interpolation
* Camera smoothing
* Particle rendering order
* Post-processing effects
* Client-only overlays (UI, accessibility)

These never feed back into authoritative state.

---

### 9C.4 Neural solver determinism (ANIMA-PHYS)

ANIMA-PHYS may be neural, but it must obey a strict contract:

* Acts as a **state transition operator**
* Input: `(S_t, controls, dt, seed)`
* Output: `S_{t+1}` or `ΔS`
* Fixed tensor shapes
* No variable-length execution

Randomness:

* Only via explicit `seed`
* Seed is part of the authoritative state

This makes the neural solver replayable on the server.

---

### 9C.5 Client role under determinism

Clients:

* never advance authoritative time
* never simulate physics
* never resolve collisions

Clients:

* interpolate
* extrapolate visually
* correct smoothly when authoritative state arrives

ANIMA-SYNC guarantees that corrections are applied at the correct timeline position.

---

### 9C.6 Failure modes and recovery

If determinism is violated or state diverges:

* server issues a hard snapshot
* ANIMA-SYNC re-anchors timeline
* visual blend masks the correction

The system degrades gracefully:

* continuity over precision
* motion over stalling

---

## 9D. Model Stack & Responsibilities

ANIMA is composed of **specialized models and runtimes**, each operating on a specific layer of the system. No single model owns the entire pipeline.

### 9D.1 Stack Overview

```
[SENSORS / INPUT]
        │
        ▼
ANIMA-SENSE  ──►  ANIMA-SYNC  ──►  ANIMA-PHYS  ──►  ANIMA-WORLD
   (client)        (timeline)        (solver)        (control)
                                           │
                                           ▼
                                     ANIMA-AVATAR
                                           │
                                           ▼
                                     ANIMA-DRAW
                                           │
                                           ▼
                                     CLIENT RENDER
```

---

### 9D.2 ANIMA-SENSE (Client Sensor Runtime)

**Role:** normalize raw peripheral data into semantic signals.

Inputs:

* camera frames (face, gaze)
* IMU (accelerometer, gyroscope)
* touch / pointer events
* microphone (non-audio features only)

Outputs (examples):

* gaze vector (x, y, confidence)
* device motion impulse
* attention focus region

Properties:

* runs locally (C++ core, TFLite / BlazingFace)
* low latency, best-effort
* never authoritative

---

### 9D.3 ANIMA-SYNC (Timeline Manager)

**Role:** align all streams into a coherent temporal experience.

Responsibilities:

* adaptive jitter buffer (150–500ms)
* per-stream ordering and buffering
* mapping `t_authoritative → t_play_hard → t_render`
* snapshot insertion and re-anchor

ANIMA-SYNC never modifies state semantics, only *when* they are applied.

---

### 9D.4 ANIMA-PHYS (Neural Physics Solver)

**Role:** authoritative evolution of the physical world.

Characteristics:

* server-side only
* fixed-step (e.g. 60Hz)
* neural solver acting as state transition operator

Inputs:

* current world state
* control impulses (from ANIMA-WORLD)
* sensor-derived forces (from ANIMA-SENSE via SYNC)

Outputs:

* next world state
* collision and trigger events

Contract:

* deterministic given `(state, controls, seed)`
* replayable

---

### 9D.5 ANIMA-WORLD (World Control Model)

**Role:** decide *what happens* in the world, not *how physics resolves it*.

Responsibilities:

* high-level world logic
* mapping narrative / interaction intent to physical controls
* spawning and despawning entities
* environmental fields (wind, gravity modifiers)

ANIMA-WORLD:

* may be neural or rule-based
* runs slower than PHYS (e.g. 10–30Hz)
* never bypasses the physics solver

---

### 9D.6 ANIMA-AVATAR (Avatar Parameter Model)

**Role:** synthesize avatar motion parameters.

Inputs:

* audio / emotion / prosody
* world context (nearby events)
* short history

Outputs:

* avatar parameter deltas (face/body/effects)

Properties:

* real-time (single-pass)
* no geometry generation
* parameters only

---

### 9D.7 ANIMA-DRAW (Vector & Render Ops Generator)

**Role:** translate authoritative state into draw-level instructions.

Responsibilities:

* layer transforms (parallax, pseudo-volume)
* vector path updates
* style and material changes
* camera composition

ANIMA-DRAW:

* may be partially neural
* respects render budgets
* outputs deterministic draw ops per state

---

### 9D.8 Separation Guarantees

| Layer        | Can mutate world? | Deterministic | Runs where      |
| ------------ | ----------------- | ------------- | --------------- |
| ANIMA-SENSE  | No                | No            | Client          |
| ANIMA-SYNC   | No                | Yes           | Both            |
| ANIMA-PHYS   | Yes               | Yes           | Server          |
| ANIMA-WORLD  | Indirect          | Yes           | Server          |
| ANIMA-AVATAR | No                | Mostly        | Server          |
| ANIMA-DRAW   | No                | Yes           | Server / Client |

This separation is what allows ANIMA to scale without losing control.

---

## 9E. ANIMA-SYNC — Timeline Manager (Concrete Operation)

This section formalizes the **working timeline sync model** already proven in the Octopus project.

### 9E.1 Role

ANIMA-SYNC is a **dedicated timeline service** that aligns all realtime streams (audio, actions, gaze, world events) into a single coherent render timeline.

It does **not** render, simulate physics, or infer semantics.

### 9E.2 Core responsibilities

* Maintain per-client timeline state
* Estimate playback delay via heartbeat
* Apply adaptive jitter buffering (150–500ms)
* Merge multi-stream intents into render packets
* Broadcast coherent packets to all connected render clients

### 9E.3 Per-client state (conceptual)

Each client maintains a temporal state similar to:

* smoothed playback delay
* last processed sequence id
* emotion / action targets
* gaze targets + freshness window
* queue depth and health metrics

This state is **accumulative**, not frame-based.

### 9E.4 Message classes handled by ANIMA-SYNC

* `heartbeat` — playback delay estimation and timeline anchoring
* `emotion` — semantic state update
* `action` — immediate avatar/world reaction
* `gaze` — continuous attention vector (camera-derived)
* `audio_chunk` — timed audio slice with sequence id
* `reset_audio` — timeline re-anchor

### 9E.5 Render packet assembly

ANIMA-SYNC assembles **render packets** by:

* selecting the latest valid audio slice
* applying current emotion/action targets
* attaching fresh gaze data (time-windowed)
* stamping authoritative timeline metadata

Packets express **what should be rendered**, not how.

### 9E.6 Broadcast semantics

* All render packets are broadcast to all active render clients
* Stale or invalid connections are pruned automatically
* Ordering is guaranteed per stream via sequence ids

This model supports multi-tab, multi-device rendering from a single authoritative timeline.

---

## 9F. Event Taxonomy & Timing Rules

ANIMA is event-driven. Every realtime input is normalized into one of a small set of event classes, each with clear timing and buffering rules.

### 9F.1 Event classes

| Class                   | Examples                                              | Rate    | Buffered?      | Authoritative? | Notes                                          |
| ----------------------- | ----------------------------------------------------- | ------- | -------------- | -------------- | ---------------------------------------------- |
| **Continuous Sensor**   | gaze vector, IMU tilt, device shake energy            | 15–60Hz | Yes (adaptive) | No             | From ANIMA-SENSE; time-windowed and smoothed   |
| **Continuous Audio**    | audio chunk, viseme/jaw slice, prosody features       | 10–50Hz | Yes (adaptive) | No             | Sequence-based; primary driver for lip/face    |
| **Discrete Intent**     | action=wave, emotion=happy, mode switches             | 0–10Hz  | Usually No     | No             | Should take effect quickly; may be timestamped |
| **World Control Ops**   | apply_force, set_field(wind), spawn/despawn           | 1–30Hz  | Yes            | Yes (via PHYS) | Goes through ANIMA-WORLD → ANIMA-PHYS          |
| **Physics Events**      | collision, trigger, joint break, contact begin/end    | 1–200Hz | Yes            | Yes            | Produced by ANIMA-PHYS; drives reactions       |
| **Render/Style Events** | camera cut, palette change, layer LOD, postFX toggles | 0–10Hz  | Yes            | Depends        | Often tied to world events or narrative        |
| **System Events**       | reset_audio, resync, snapshot requested, health       | 0–5Hz   | No             | Yes            | Controls the timeline and recovery             |

---

### 9F.2 Timing fields (required)

Each event may carry:

* `t_authoritative` — server time (or simulation time) when the event becomes true
* `t_sent` — server send time
* `seq` — per-stream ordering id (required for continuous streams)
* `ttl_ms` — validity window (especially for gaze)

Client renders against `t_render` while SYNC applies events at `t_play`.

---

### 9F.3 Buffering rules

ANIMA-SYNC maintains **separate buffers per stream** because streams have different jitter and semantic sensitivity.

Rules:

* **Audio**: buffered and sequence-ordered; never reordered; missing chunks degrade gracefully.
* **Gaze**: buffered but **time-windowed** (drop if stale); uses freshness window (e.g. 500–1500ms).
* **IMU**: buffered and downsampled; converted to impulses/fields.
* **Actions/Emotions**: low-latency; can bypass buffer or use minimal buffer (0–50ms).
* **Physics**: authoritative; applied at exact sim tick boundaries.

Buffer target is adaptive:

* baseline ~300ms
* adaptive range 150–500ms using heartbeat jitter estimates

---

### 9F.4 Immediate vs buffered application

Some events must be perceived instantly.

| Event          | Apply                         | Reason                          |
| -------------- | ----------------------------- | ------------------------------- |
| `action`       | Immediate (or minimal buffer) | avatar needs to react instantly |
| `emotion`      | Immediate (or minimal buffer) | emotion switch is perceptual    |
| `gaze`         | Buffered + freshness          | must align with head/eye motion |
| `audio_chunk`  | Buffered                      | lip sync must match audio       |
| physics events | Buffered at sim tick          | preserves determinism           |

---

### 9F.5 Freshness windows (defaults)

* gaze validity: **500–1500ms** (drop if older)
* IMU impulses: **100–300ms** (integrate then decay)
* actions: **until overridden** (stateful)
* emotion: **until overridden** (stateful)

These are tunable per experience.

---

### 9F.6 Conflict resolution (layered state)

When multiple events update overlapping targets, resolution is deterministic.

Priority (highest → lowest):

1. System events (reset/resync)
2. Physics events (authoritative)
3. World control ops (authoritative intent)
4. Discrete intent (action/emotion)
5. Continuous sensors (gaze/IMU)
6. Continuous audio features (jaw/viseme targets)
7. Pure render/style events

Within a layer:

* newest `t_authoritative` wins
* if equal time, higher `seq` wins

---

### 9F.7 Sensor-driven pseudo-volume (layer shift)

Sensors influence world perception without breaking physics.

* **Gaze** shifts camera and layer parallax toward the attention direction.
* **IMU shake** injects impulses into camera and selected layer offsets.
* **Tilt** changes pseudo-depth by scaling parallax coefficients.

Importantly:

* physics remains server-authoritative
* sensors are interpreted as *controls* and/or *presentation modifiers*
* ANIMA-SYNC places these modifications on the correct timeline position

---

### 9F.8 Practical example (single moment)

1. User shakes phone (IMU burst) at `t_authoritative = 12.400s`
2. ANIMA-SENSE sends `imu_impulse(seq=88)`
3. ANIMA-SYNC buffers and aligns it
4. ANIMA-WORLD maps it to `apply_impulse` for world objects
5. ANIMA-PHYS resolves collisions deterministically
6. ANIMA-DRAW emits layer shifts and camera recoil
7. Client renders smoothly with no stalls under the adaptive buffer

---

## 9G. Buffering & Multi-Stream Queues (Per-Layer)

This section defines how ANIMA-SYNC buffers **multiple concurrent streams** so the client can render without stalls while the server remains authoritative.

### 9G.1 Why per-stream (not one global buffer)

Streams have different jitter and different perceptual sensitivity.

* Audio must be ordered and continuous.
* Gaze must be recent (freshness window).
* IMU can be integrated and decayed.
* Physics is tick-aligned and authoritative.

Therefore ANIMA-SYNC maintains **separate queues** and a shared render time `t_play`.

### 9G.2 Queues

For each session/client:

* **Q_audio**: ordered by `seq`, each item has `t_authoritative` and duration
* **Q_gaze**: ordered by `t_authoritative`, time-windowed by `ttl_ms`
* **Q_imu**: ordered by `t_authoritative`, downsampled + integrated
* **Q_intent**: actions/emotions/mode (stateful latest-wins)
* **Q_world_ops**: authoritative ops aligned to physics ticks
* **Q_phys_events**: authoritative events emitted by ANIMA-PHYS
* **Q_style**: camera/parallax/palette/postFX (may be derived)

### 9G.3 Adaptive buffer target

ANIMA-SYNC computes a target buffer `B_target_ms` from heartbeat jitter:

* default: **300ms**
* min: **150ms** (good network)
* max: **500ms** (high jitter)

The service updates `B_target_ms` gradually to avoid oscillation.

### 9G.4 Timebase and playback time

* `t0_estimate` anchors server time to the client playback clock.
* `t_play = now_server - B_target_ms` defines what time the renderer should be showing.

All queues are consumed **up to **``, producing a coherent state for that moment.

### 9G.5 Consumption rules per queue

* **Audio**: consume sequentially until coverage includes `t_play`; if a gap exists, hold last viseme targets and decay energy.
* **Gaze**: pick the newest gaze sample with `t_authoritative <= t_play` and `age <= ttl_ms`; otherwise fallback to neutral.
* **IMU**: integrate impulses over a short window around `t_play` and apply exponential decay.
* **Intent**: apply latest state whose `t_authoritative <= t_play`.
* **World ops**: apply only at physics tick boundaries; ops are forwarded to ANIMA-PHYS.
* **Physics events**: enqueue at emit time; apply at the tick they belong to.
* **Style**: derived from gaze/IMU/world; apply as layer modifiers.

### 9G.6 Layered output state

ANIMA-SYNC produces a layered state snapshot for `t_play`:

* Avatar intent targets (emotion/action)
* Audio-driven targets (jaw/viseme/energy)
* Sensor-driven modifiers (gaze, IMU)
* World control ops (authoritative)
* Style layer modifiers (camera/parallax/postFX)

Then it emits either:

* `delta` (typical)
* `snapshot` (periodic re-anchor)

### 9G.7 Stream health and recovery

Per stream:

* late packets: accepted if within a small reorder window, otherwise dropped
* out-of-order `seq` (audio): dropped
* periodic snapshot: every N seconds or on detected drift
* `reset_audio`: hard re-anchor for the audio timeline

### 9G.8 Buffer per layer (concept)

Because there are multiple render layers, ANIMA-SYNC may maintain **layer-specific smoothing** even when sharing `t_play`:

* face/jaw smoothing window: 30–80ms
* gaze smoothing window: 60–120ms
* camera/parallax smoothing window: 80–180ms
* world transform smoothing window: 0–50ms (mostly tick aligned)

These are *filters*, not separate timelines.

---

## 10. Streaming Protocol (ANIMA Control Stream)

### 10.1 Protocol choice: SceneGraph ops first

We standardize on:

* **SceneGraph ops** as the primary draw format (portable, optimizable, LOD-friendly)
* `` as an optional escape hatch for special layers (rare, gated, budgeted)

This keeps most rendering deterministic, cacheable, and cross-runtime.

---

### 10.2 Transport

Supported transports:

* **WebSocket** (default)
* **WebRTC DataChannel** (ultra-low latency)
* **SSE** (fallback)

---

### 10.3 Timebase & ordering (required fields)

Every message MUST include:

* `v` protocol version
* `sid` session id
* `stream` logical stream name
* `type` message type within the stream
* `seq` monotonically increasing sequence **per stream**
* `t_auth_ms` authoritative time (server sim time) when it becomes true
* `t_sent_ms` send timestamp
* `ttl_ms` validity window (0 if not applicable)

Ordering is guaranteed **per stream**, not globally.

---

### 10.4 Base envelope

```json
{
  "v": "2.4",
  "sid": "S_9f2a",
  "stream": "draw",
  "type": "delta",
  "seq": 1842,
  "t_auth_ms": 41233,
  "t_sent_ms": 41238,
  "ttl_ms": 0,
  "payload": {}
}
```

---

### 10.5 Streams

| Stream  | Producer             | Consumer            | Purpose                                      |
| ------- | -------------------- | ------------------- | -------------------------------------------- |
| `sense` | client (ANIMA-SENSE) | server (SYNC/WORLD) | gaze/imu/pointer/voice intents               |
| `audio` | server (or client)   | SYNC + client       | audio chunks + viseme targets                |
| `sync`  | server (ANIMA-SYNC)  | client              | buffer targets + timeline state              |
| `world` | server (ANIMA-WORLD) | PHYS + client       | WorldOps (HardOps)                           |
| `phys`  | server (ANIMA-PHYS)  | client              | authoritative transforms + physics events    |
| `draw`  | server (ANIMA-DRAW)  | client              | DrawOps (SceneGraph ops, optional cmd_batch) |
| `sys`   | both                 | both                | reset/resync/snapshot                        |

---

### 10.6 Message types

* `delta` — incremental update relative to latest applied snapshot
* `snapshot` — full re-anchor checkpoint
* `event` — discrete marker (dialogue, collision tag, etc.)
* `cmd_batch` — optional draw escape hatch (special layers only)

---

### 10.7 `sense` payloads (client → server)

ANIMA-SENSE can trigger world interactions, but it never mutates authoritative state locally. Chain: **SENSE → SYNC → WORLD → PHYS → DRAW**.

Supported intents (baseline):

* `gaze_ray` (continuous, time-windowed)
* `gaze_select` (dwell/confirm)
* `pointer_down/up`, `pointer_move`
* `drag_start/move/end`
* `imu_impulse`, `tilt_vector`
* `voice_intent` (AI/NLU high-level command)

Example: gaze ray

```json
{
  "v": "2.4",
  "sid": "S_9f2a",
  "stream": "sense",
  "type": "delta",
  "seq": 901,
  "t_auth_ms": 41233,
  "t_sent_ms": 41236,
  "ttl_ms": 900,
  "payload": {
    "intent": "gaze_ray",
    "screen_xy": [0.61, 0.43],
    "confidence": 0.88,
    "blink": 0,
    "head_pose": {"yaw": 0.07, "pitch": -0.04, "roll": 0.01}
  }
}
```

Example: pointer down

```json
{
  "stream": "sense",
  "type": "delta",
  "seq": 1202,
  "t_auth_ms": 42010,
  "t_sent_ms": 42010,
  "ttl_ms": 200,
  "payload": {
    "intent": "pointer_down",
    "pointer_id": 1,
    "screen_xy": [0.32, 0.77],
    "button": 0
  }
}
```

Example: voice intent

```json
{
  "stream": "sense",
  "type": "delta",
  "seq": 77,
  "t_auth_ms": 43000,
  "t_sent_ms": 43010,
  "ttl_ms": 1500,
  "payload": {
    "intent": "voice_intent",
    "name": "open_door",
    "args": {"door_id": 7},
    "confidence": 0.72
  }
}
```

---

### 10.8 `world` payloads (server → phys + client)

WorldOps mutate the authoritative simulation.

```json
{
  "stream": "world",
  "type": "delta",
  "seq": 311,
  "t_auth_ms": 41250,
  "t_sent_ms": 41255,
  "ttl_ms": 0,
  "payload": {
    "ops": [
      {"op": "apply_impulse", "object_id": 42, "impulse": [0.5, -0.2], "at": [0.36, 0.71]},
      {"op": "set_field", "field": "wind", "vec": [0.1, 0.0], "falloff": 0.7}
    ]
  }
}
```

---

### 10.9 `phys` payloads (server → client)

Authoritative transforms + physics events.

```json
{
  "stream": "phys",
  "type": "delta",
  "seq": 9901,
  "t_auth_ms": 41266,
  "t_sent_ms": 41270,
  "ttl_ms": 0,
  "payload": {
    "tick": 9912,
    "dt_ms": 16.666,
    "transforms": [
      {"id": 42, "p": [102.1, 198.4], "r": 0.02, "v": [1.2, -0.4]},
      {"id": 7, "p": [300.0, 400.0], "r": 0.50}
    ],
    "events": [
      {"e": "contact_begin", "a": 42, "b": 7},
      {"e": "trigger", "id": 15, "who": 42}
    ]
  }
}
```

---

### 10.10 `draw` payloads (server → client)

#### 10.10.1 Primary: SceneGraph ops (`type: delta`)

```json
{
  "stream": "draw",
  "type": "delta",
  "seq": 1842,
  "t_auth_ms": 41233,
  "t_sent_ms": 41238,
  "ttl_ms": 0,
  "payload": {
    "layers": [
      {"id": "bg", "tx": [0.0, 0.0], "parallax": 0.1},
      {"id": "mid", "tx": [2.0, -1.0], "parallax": 0.4}
    ],
    "objects": [
      {"id": 9001, "op": "update_transform", "p": [102.1, 198.4], "r": 0.02},
      {"id": 9002, "op": "set_style", "fill": [0.2, 0.6, 0.9, 1.0]}
    ]
  }
}
```

#### 10.10.2 Optional: `cmd_batch` (special layers only)

Allowed only for explicitly whitelisted layers (e.g., debug overlays, experimental FX layers).

```json
{
  "stream": "draw",
  "type": "cmd_batch",
  "seq": 1843,
  "t_auth_ms": 41250,
  "t_sent_ms": 41255,
  "ttl_ms": 0,
  "payload": {
    "layer": "fx_experimental",
    "cmds": [
      ["save"],
      ["translate", 2.0, -1.0],
      ["beginPath"],
      ["moveTo", 10, 10],
      ["bezierCurveTo", 20, 20, 30, 5, 40, 10],
      ["fillStyle", "rgba(51,153,255,1)"],
      ["fill"],
      ["restore"]
    ]
  }
}
```

---

### 10.11 `sync` payloads (server → client)

Timeline state and buffer targets.

```json
{
  "stream": "sync",
  "type": "state",
  "seq": 501,
  "t_auth_ms": 41240,
  "t_sent_ms": 41240,
  "ttl_ms": 0,
  "payload": {
    "t0_estimate_ms": 39800,
    "buffer_target_ms": 320,
    "buffer_min_ms": 150,
    "buffer_max_ms": 500,
    "t_play_ms": 41200,
    "health": {"audio_q": 12, "gaze_age_ms": 83, "late_pct": 0.02}
  }
}
```

---

### 10.12 `sys` messages

* `reset_audio`
* `resync`
* `snapshot_request`

Example: snapshot request

```json
{
  "stream": "sys",
  "type": "snapshot_request",
  "seq": 12,
  "t_auth_ms": 50000,
  "t_sent_ms": 50000,
  "ttl_ms": 0,
  "payload": {"streams": ["phys", "draw"]}
}
```

---

### 10.13 Budget & safety notes (protocol-level)

* `draw.delta` MUST be delta-encoded; full geometry changes should be event-based + snapshots.
* `cmd_batch` MUST be gated by layer allowlist + complexity caps.
* If budgets are exceeded, lowest-priority visuals drop first (particles/postFX), never physics.

---

## 14. SceneGraph, Layers & Pseudo-Volume

### 14.1 Purpose

This section defines how ANIMA represents **space, depth, and volume** in a 2D vector world using a layered SceneGraph, without true 3D rendering.

The goal is to create a **perceptually volumetric, physically coherent world** on Canvas/WebGL that:

* remains deterministic,
* is cheap to render,
* and reacts naturally to physics, gaze, and device motion.

---

### 14.2 SceneGraph as the Primary World Representation

ANIMA uses a **SceneGraph-first model**.

Each scene is a directed acyclic graph composed of layers and objects:

```
World
├─ Layer[background]
│  └─ Objects (static paths, gradients)
├─ Layer[mid]
│  └─ Objects (interactive world geometry)
├─ Layer[actors]
│  └─ Avatar + NPCs
├─ Layer[fx]
│  └─ Particles, light, transient effects
└─ Layer[ui/local]
   └─ Client-only overlays
```

Each layer has:

* transform
* parallax coefficient
* render budget
* authority flag (server / client-local)

---

### 14.3 Pseudo-Volume Model

ANIMA does **not** simulate full 3D geometry for rendering. Instead, it constructs **pseudo-volume** from layered transforms.

Key idea:

> Depth is expressed by **relative motion**, not geometry.

Each layer defines:

* `z_index` (ordering)
* `parallax` coefficient
* optional `depth_bias`

At render time:

```
layer_offset = camera_delta × parallax
```

This creates:

* depth illusion
* camera motion
* volumetric response to interaction

---

### 14.4 Camera as a First-Class Node

The camera is modeled as a SceneGraph node, not a post-effect.

Camera state includes:

* position
* velocity
* impulse accumulator
* smoothing kernel

Camera transforms are influenced by:

* physics impulses (explosions, collisions)
* gaze direction (attention pull)
* IMU shake / tilt
* narrative cues

Camera motion is **authoritative only in presentation**, never in physics.

---

### 14.5 Sensor-Driven Layer Shifts (ANIMA-SENSE)

ANIMA-SENSE can influence perceived volume without mutating the world.

Examples:

* **Gaze** pulls foreground layers toward attention
* **Tilt** shifts parallax baseline
* **Shake** injects damped camera impulses

These effects:

* are time-windowed
* are reversible
* never alter authoritative world state

They live entirely in the **presentation layer**.

---

### 14.6 Physics ↔ SceneGraph Coupling

Physics outputs authoritative transforms for objects.

SceneGraph consumes them as:

* object transforms
* layer-relative offsets

Rules:

* physics never reads from SceneGraph
* SceneGraph never mutates physics

This keeps simulation and presentation decoupled.

---

### 14.7 Lighting & Depth Cues (2.5D)

Depth is reinforced using lightweight cues:

* gradient lighting per layer
* shadow offsets tied to pseudo-depth
* atmospheric fade (distance-based alpha)

These are **style-level effects**, not simulation.

---

### 14.8 Why This Works

This model provides:

* strong spatial perception
* low render cost
* deterministic replay
* compatibility with neural + procedural systems

Without the complexity of:

* true 3D meshes
* z-buffers
* heavy GPU pipelines

---

### 14.9 Constraints

Hard constraints:

* No per-frame path regeneration for depth
* No geometry mutation from sensors
* No feedback from presentation → physics

If violated, determinism and sync break.

---

### 14.10 Outcome

SceneGraph + Pseudo-Volume is the backbone that allows:

* ANIMA-WORLD to feel spatial
* ANIMA-SENSE to feel embodied
* ANIMA-DRAW to remain cheap

This enables **game-like worlds** on pure vector rendering.

---

## 15. Platform-Level Application Use Cases

This section describes **where ANIMA can be applied as a product platform**, beyond isolated technical demos. These use cases are market-facing and designed to validate product–market fit, monetization, and differentiation.

### 15.0 Why ANIMA changes the economics of interactive media

ANIMA’s core shift is **streaming JSON control and scene state** instead of video frames.

| Traditional approach                      | ANIMA                                             |
| ----------------------------------------- | ------------------------------------------------- |
| Server generates video                    | Server generates JSON instructions + state deltas |
| 2–5 Mbps bandwidth                        | ~30–100 KB/s                                      |
| ~5–10 users per GPU (video/avatar render) | ~100–200 users per GPU (control stream)           |
| ~$0.20–0.50 per minute                    | ~$0.002 per minute (target)                       |
| Passive consumption                       | Interaction + physics + attention                 |
| Fixed camera                              | Gaze-driven parallax + pseudo-volume              |

**Mental model:** ANIMA is a *living vector world* — the brain runs on the server, the body runs on the client.

### 15.0.1 Paradigm shifts enabled

| From                       | To                                 |
| -------------------------- | ---------------------------------- |
| Passive video              | Interactive participation          |
| One-size content           | Emotionally responsive content     |
| High bandwidth barrier     | Works on weak networks             |
| Expensive per-minute media | Democratized real-time experiences |
| Screen as window           | Screen as portal                   |

---

---

## 15.1 Interactive Anime (Real‑Time Narrative Series)

### What it is

Anime series where the viewer actively influences the story, and characters respond **in real time**. This is **not** pre-rendered branching (à la Bandersnatch), but live emotional and behavioral reactions.

Characters look at the viewer, react to tone, hesitation, gaze, and explicit choices.

---

### Why it’s WOW

* The character **looks at you** and reacts to *your* decision
* Emotional continuity: characters remember how you treated them
* Infinite replayability — every viewing is different
* Strong social virality: “Look how she reacted to *my* choice”

---

### Format

```
25‑minute episode:
├── ~70% pre-rendered (action, crowds, environments)
├── ~25% ANIMA real-time (dialogue, close-ups, reactions)
└── ~5% decision points (viewer input)

Scene example:
[Pre-rendered: protagonist enters room]
[ANIMA: female character turns, notices him]
[Decision prompt]
  → “I’m sorry” → she cries, approaches
  → “This is your fault” → she gets angry, turns away
  → [Silence 5s] → she looks worried: “Are you okay?”
```

---

### Monetization

| Model                 | Price       | Notes                |
| --------------------- | ----------- | -------------------- |
| Platform subscription | $15 / month | Netflix-style        |
| Per-series purchase   | $5–15       | Premium shows        |
| Relationship DLC      | $3–5        | Unlock romance arcs  |
| Custom episodes       | $20+        | Personalized stories |

---

### Competitive landscape

* Netflix Bandersnatch: pre-rendered branches
* Pocket FM: audio only

**No one currently offers real-time anime characters with live emotional reactions.**

---

### ANIMA advantage

* First real-time anime interaction platform
* Anime style avoids uncanny valley
* Emotion-native reactions (Hume integration)
* Low bandwidth, scalable delivery

---

### MVP

One episode, one main character, three decision points. Goal: demonstrate visceral “WOW”.

---

## 15.2 Adult / NSFW Interactive Content

### What it is

AI-generated adult content with **live, emotionally reactive characters** — from romantic companions to explicit roleplay.

This includes girlfriend/boyfriend simulations, fantasy scenarios, and private interactions.

---

### Why it’s WOW

* Characters respond to *your* words and tone
* Not scripted — dynamic emotional chemistry
* Voice + emotion + animation = deep immersion
* No real people involved → privacy and scalability

---

### Format

```
Content tiers:
├── SFW: romantic companion, flirting, dates
├── Suggestive: intimate dialogue, teasing
└── Explicit: full adult content (separate product)

Interaction:
- Voice chat
- Text + animated responses
- Scenario-based roleplay
- Custom requests via text
```

---

### Monetization

| Model             | Price            | Notes                |
| ----------------- | ---------------- | -------------------- |
| Subscription      | $20–50 / month   | Unlimited chat       |
| Pay-per-minute    | $0.10–0.50 / min | Usage-based          |
| Custom characters | $50–200          | Personalized avatars |
| Private scenarios | $5–20            | Specific fantasies   |

**Unit economics (illustrative):**

* Cost: ~$0.01 / min
* Price: ~$0.20 / min
* Margin: ~95%
* 1M minutes / month ≈ $200K revenue

---

### Competitive landscape

| Competitor   | Offering       | Weakness                   |
| ------------ | -------------- | -------------------------- |
| Character.ai | Text-only      | No voice or animation      |
| Replika      | Basic avatar   | Static, low fidelity       |
| Candy.ai     | AI girlfriend  | Images only                |
| OnlyFans     | Human creators | Expensive, not interactive |

---

### ANIMA advantage

* Real-time emotional response
* Anime aesthetic (bypasses uncanny valley)
* Voice + animation + conversation
* Massive scalability (1 model → millions of users)

---

### Risks

* App store policies
* Payment processor restrictions
* Brand/reputation risk

**Mitigation:** separate brand, web-only, alternative payments.

---

### MVP

Romantic SFW companion → suggestive tier → explicit as separate product.

---

## 15.3 AI Companions (Emotional & Social)

### What it is

A personal AI companion with face, voice, memory, and emotional continuity. Not a chatbot — a relationship.

---

### Why it’s WOW

* Character.ai is text; ANIMA is a person on screen
* Remembers past interactions
* Responds emotionally to user mood
* Always available, non-judgmental

---

### Use cases

* Friendship and emotional support
* Language practice
* Therapy-lite reflection
* Fictional character roleplay
* Productivity/accountability partner

---

### Monetization

| Model              | Price       | Notes                            |
| ------------------ | ----------- | -------------------------------- |
| Free tier          | $0          | Limited daily usage              |
| Pro                | $15 / month | Unlimited chat, memory           |
| Premium            | $30 / month | Multiple companions, voice clone |
| Lifetime character | $100–500    | One-time purchase                |

---

### Market signal

* Character.ai: 20M+ users, ~$150M ARR
* Replika: 10M+ users, ~$50M ARR

**Market growing >50% YoY. Current offerings lack visual presence.**

---

### ANIMA advantage

* Face that looks at you
* Emotionally expressive voice
* Real-time reactions
* Anime style with mass appeal

---

### MVP

Single companion, unlimited chat, basic memory. Compare side-by-side with Character.ai.

---

## 15.4 Creator Tools & Virtual Personas

### What it is

Tools for creators (VTubers, streamers, OnlyFans, TikTok) to create and monetize AI-driven avatars.

---

### Why it’s WOW

* VTubing without expensive hardware
* AI clone streams while you sleep
* Personalized fan messages at scale
* Multilingual output from one creator

---

### Products

```
├── AI VTuber (live streaming)
├── Personalized fan videos
├── Content localization (multi-language)
├── 24/7 avatar presence
└── AI collab tools (avatar + avatar)
```

---

### Creator workflow

1. Record ~10 minutes of voice → voice clone
2. Upload visual references → avatar
3. Write prompt or script
4. AI generates content
5. Review and publish

---

### Monetization

| Model         | Price        | Notes               |
| ------------- | ------------ | ------------------- |
| Starter       | $30 / month  | ~100 minutes        |
| Pro           | $100 / month | ~500 minutes        |
| Agency        | $500 / month | Multi-creator + API |
| Revenue share | 5–10%        | Creator earnings    |

---

### Competitive landscape

| Competitor   | Focus           | Weakness                       |
| ------------ | --------------- | ------------------------------ |
| VTube Studio | Manual VTubing  | No AI                          |
| HeyGen       | AI video        | Photorealistic, not anime      |
| Synthesia    | Corporate video | Expensive, not creator-focused |
| D-ID         | Talking head    | Low visual quality             |

---

### ANIMA advantage

* Anime-native aesthetic
* Real-time (streaming, not pre-rendered)
* Emotion-aware reactions
* Affordable pricing

---

### MVP

“AI VTuber in a box”: upload voice → get avatar → start streaming.

---

## 15.5 Strategic Summary

| Market            | TAM                | Time to MVP | Revenue Potential | Risk          |
| ----------------- | ------------------ | ----------- | ----------------- | ------------- |
| Interactive Anime | $5B+               | 3–4 months  | High              | Content cost  |
| Adult / NSFW      | $15B+              | 2–3 months  | Very high         | Platform risk |
| AI Companions     | $2B+ (fast growth) | 2–3 months  | High              | Competition   |
| Creator Tools     | $1B+               | 3–4 months  | Medium–High       | Sales cycle   |

**Founder take:**

* Fastest revenue: Adult / Companions
* Biggest PR & differentiation: Interactive Anime
* Most defensible long-term: Creator Tools

---

## 15.6 Market size (rough, directional)

| Sector                       | TAM (indicative) | ANIMA opportunity            |
| ---------------------------- | ---------------- | ---------------------------- |
| VTuber / Virtual Influencers | ~$4B (mid-2020s) | tooling + runtime layer      |
| E-learning                   | ~$350B           | interactive tutor segment    |
| Narrative gaming / VN        | ~$10B+           | realtime NPCs + VN platforms |
| Customer support AI          | ~$8B             | avatar upgrade layer         |
| Mental health apps           | ~$6B             | companion/support niche      |
| Interactive advertising      | ~$15B            | engagement premium           |

**Conservative cross-segment opportunity:** ~$5–10B if ANIMA becomes the default runtime for a subset of interactive 2D experiences.

## 15.7 Priority use cases by phase

**Tier 1 — MVP candidates (fast validation)**

1. VTuber / streaming runtime (clear pain, paying users)
2. AI companions (strong differentiation vs text)
3. Visual novels (proven market, especially Asia)

**Tier 2 — Growth phase (repeatable revenue)** 4) Education / training (B2B, recurring) 5) Customer support avatars (measurable ROI) 6) Interactive anime (high content effort, huge upside)

**Tier 3 — Platform phase (network effects / licensing)** 7) Creator SDK licensing (ecosystem) 8) Multi-user synced worlds (social) 9) Enterprise training scenarios (large contracts)

---

## 15.8 “ANIMA-native” expectation

If ANIMA-powered experiences become common, users will start expecting:

* characters that **listen** (gaze + timing)
* worlds that **react** (physics + interaction)
* stories that **remember** (state + continuity)
* content that feels **alive**, without video bandwidth

---

## 14. Audio & Sound Layers (World-Aware Audio)

### 14.1 Role of Audio in ANIMA

In ANIMA, audio is **not a single voice stream**. It is a **first-class, multi-layered system** tightly coupled to the world, physics, avatar state, and timeline.

Audio serves three distinct purposes:

1. **Semantic** — speech, dialogue, narration (voice, TTS)
2. **Physical** — impacts, movement, collisions, environmental response
3. **Atmospheric** — ambience, texture, emotional tone of the scene

All audio layers are **timeline-synchronised** via ANIMA-SYNC and may be either realtime or pre-generated, depending on the layer.

---

### 14.2 Audio Layer Model

ANIMA treats audio as **layered streams**, similar to visual layers.

| Layer          | Examples                       | Source                    | Realtime | Authority       |
| -------------- | ------------------------------ | ------------------------- | -------- | --------------- |
| Voice          | Dialogue, narration            | TTS / user mic            | Yes      | Server          |
| Avatar Foley   | Breath, cloth, subtle movement | Procedural                | Yes      | Client / Server |
| Physics SFX    | Impacts, friction, breakage    | Physics events            | Yes      | Server          |
| World Ambience | Wind, rain, city hum           | Procedural / loops        | Mixed    | Server          |
| Event Stingers | UI cues, story beats           | Pre-authored              | No       | Server          |
| Music          | Score, adaptive music          | Pre-authored / generative | Mixed    | Server          |

Each layer has its own **mix rules, priority, spatialisation and budget**.

---

### 14.3 Timeline Integration (ANIMA-SYNC)

Audio is aligned to the **same authoritative timeline** as physics and visuals.

Key rules:

* every audio event carries `t_authoritative`
* playback is aligned to `t_play`
* late audio is either time-shifted or gracefully dropped
* audio never blocks the render loop

ANIMA-SYNC ensures:

* lip-sync matches visemes
* physics sounds align with impacts
* music and ambience remain continuous under jitter

---

### 14.4 Physics-Driven Audio

ANIMA-PHYS emits **audio-relevant events** as part of simulation:

Examples:

* collision begin/end
* impulse magnitude thresholds
* joint break / constraint stress
* continuous contact (sliding, rolling)

These events are converted into **audio intents**, not raw sounds.

```json
{
  "stream": "phys",
  "type": "event",
  "t_auth_ms": 51230,
  "payload": {
    "e": "collision",
    "a": 42,
    "b": 7,
    "impulse": 1.8,
    "material": "wood"
  }
}
```

ANIMA-AUDIO resolves this into:

* sound selection
* gain and pitch
* spatial position
* decay and layering

This keeps physics deterministic while allowing rich sound variation.

---

### 14.5 Procedural Sound Generators

Many sounds are better generated procedurally than sampled.

Examples:

* wind intensity from vector fields
* rain density from particle systems
* fire crackle from emitter energy
* breathing rate from avatar state

Procedural generators:

* are parameter-driven
* consume world state deltas
* run either server-side (authoritative) or client-side (perceptual)

They are **stateless or explicitly seeded** to preserve replayability.

---

### 14.6 Avatar-Coupled Audio

Avatar audio is tightly coupled to animation parameters:

* breath follows chest expansion
* effort sounds follow exertion
* emotional micro-sounds (sighs, laughs)

These sounds:

* may be non-verbal
* are not TTS
* increase perceived presence

They are driven by **ANIMA-AVATAR outputs**, not by text.

---

### 14.7 Spatialisation & Mixing

ANIMA audio uses a simplified but deterministic spatial model:

* 2D world coordinates
* depth via layer index + parallax
* camera-relative attenuation

Mixing rules:

* voice always remains intelligible
* physics audio ducks under dialogue
* ambience adapts to emotional tone

Final mixing may occur:

* server-side (authoritative stream)
* client-side (WebAudio, preferred for latency)

---

### 14.8 Client vs Server Responsibilities

| Responsibility             | Server   | Client |
| -------------------------- | -------- | ------ |
| Audio intent generation    | ✓        | —      |
| Physics → sound mapping    | ✓        | —      |
| Timeline alignment         | ✓        | ✓      |
| Procedural sound synthesis | Optional | ✓      |
| Spatialisation             | Optional | ✓      |
| Final mix & playback       | —        | ✓      |

Clients may adapt audio quality based on device capabilities, but **never alter semantics**.

---

### 14.9 Why This Matters

Audio in ANIMA:

* reinforces determinism without sacrificing richness
* scales cheaply (no audio streaming per layer)
* increases emotional presence dramatically
* unifies avatar, world and physics into a single perceptual space

Without world-aware audio, ANIMA would feel reactive. With it, the world feels **alive**.
