# ANIMA — Adaptive Neural Interface for Motion & Animation

**Technical Specification v3.0**

**Project:** Real-time generative avatar animation with neural parameter synthesis  
**Date:** January 17, 2026  
**Status:** Final Architecture — Flow Matching + Own Audio Stack  

---

## 1. Executive Summary

ANIMA is a **real-time neural animation system** that synthesizes stylized 2D avatar animations from multimodal inputs (speech, emotion, motion). ANIMA generates **JSON canvas instructions**, not video — all rendering happens on the client.

**Core Capabilities:**
- Neural parameter synthesis (flow-based generation of animation parameters)
- JSON instruction streaming (~1KB/frame, not video)
- Client-side rendering via ANIMA SDK (WebGL2)
- Custom open-source Animation SDK (no Live2D dependency)
- Hume EVI integration for emotion-aware speech
- 30 FPS target, 50–100ms end-to-end latency

**Key Architecture Decisions:**
- Server generates parameters, client renders frames
- Flow-based neural network for parameter prediction
- Own SDK with WebGL2 backend (Live2D-compatible import)
- Hume EVI for MVP voice + emotion, own TTS for scale

**Economic Advantage:**
- 100–200 concurrent users per GPU (vs 5–10 for video streaming)
- Cost: ~$0.002/min (vs $0.20–0.50 for competitors)
- Bandwidth: ~30 KB/s (vs 2–5 Mbps for video)

---

## 2. System Architecture

### 2.1 Core Principle: JSON, Not Video

```
┌─────────────────────────────────────────────────────────────┐
│                      ANIMA BACKEND                          │
│                                                             │
│   Input (Hume EVI)      Neural Inference      Output        │
│   ┌─────────────┐      ┌─────────────┐      ┌──────────┐   │
│   │ Audio       │      │ Flow-based  │      │ JSON     │   │
│   │ Emotion     │ ──►  │ Parameter   │ ──►  │ Canvas   │   │
│   │ Prosody     │      │ Generator   │      │ Instruct │   │
│   └─────────────┘      └─────────────┘      └──────────┘   │
│                                                    │        │
└────────────────────────────────────────────────────┼────────┘
                                                     │
                              WebSocket (~1KB/frame) │
                                                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      CLIENT BROWSER                         │
│                                                             │
│   ┌─────────────┐      ┌─────────────┐      ┌──────────┐   │
│   │ JSON Parse  │      │ ANIMA SDK   │      │ Canvas/  │   │
│   │ + Interp    │ ──►  │ WebGL2      │ ──►  │ Display  │   │
│   └─────────────┘      │ Renderer    │      └──────────┘   │
│                        └─────────────┘                      │
│                                                             │
│   Client GPU does ALL rendering. Server only thinks.        │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 What Server Does vs What Client Does

| Server (ANIMA Backend) | Client (ANIMA SDK) |
|------------------------|-------------------|
| Receives audio/emotion from Hume | Receives JSON parameters |
| Neural inference (30ms) | Frame interpolation |
| Generates parameter deltas | Mesh deformation |
| Compresses JSON | Texture compositing |
| Streams via WebSocket | WebGL rendering |
| **No video encoding** | **Full frame rendering** |

### 2.3 End-to-End Data Flow

```
VOICE & EMOTION (Hume EVI)
├─ User speech input
├─ Hume processes: ASR + emotion detection + TTS
└─ Output: audio stream + emotion vector + prosody

        ↓ [WebSocket from Hume]

ANIMA CORE (Server)
├─ Audio encoder (CTC phonemes + Hume emotion)
├─ Context encoder (avatar identity, scene)
├─ Fusion → Z (1024D latent)
├─ Flow-based parameter generator
└─ Output: JSON canvas instructions

        ↓ [WebSocket ~1KB/frame]

ANIMA SDK (Client)
├─ Parse JSON parameters
├─ Interpolate between frames
├─ Apply to mesh/skeleton
├─ Render all layers (background → body → face → effects)
├─ Post-processing (glow, particles)
└─ Output to canvas @ 30 FPS
```

---

## 3. Audio Engine (Own Stack)

### 3.1 Why Own Stack (Not Hume)

| Aspect | Hume EVI | Own Stack |
|--------|----------|-----------|
| Cost/min | $0.05–0.10 | $0.002–0.005 |
| Control | Limited | Full |
| Latency | +50ms (API) | Local |
| Multilingual | Yes | Yes |
| Voice clone | No | Yes |
| **For content generation** | ❌ Expensive | ✅ |
| **For real-time chat** | ✅ Easy | ⚠️ More work |

**Hume makes sense for:** MVP of real-time chat (AI companions)
**Own stack for:** Interactive Anime, Adult content, Creator tools

### 3.2 Multilayer Audio Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    ANIMA AUDIO ENGINE                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Layer 1: VOICE (TTS / Voice Clone)                         │
│  ├─ XTTS v2 / StyleTTS2 / Fish Speech                       │
│  ├─ Voice cloning (5 sec reference)                         │
│  └─ Multilingual (JP, EN, RU, KO, ZH)                       │
│                                                              │
│  Layer 2: EMOTION (from text or prosody)                    │
│  ├─ Text → emotion classifier (fine-tuned BERT, 10ms)       │
│  ├─ Prosody extraction → animation params                   │
│  └─ Phoneme alignment (CTC) → lip sync timing               │
│                                                              │
│  Layer 3: SFX                                               │
│  ├─ Script triggers (#sfx: door_open)                       │
│  ├─ Procedural (footsteps, cloth, movement)                 │
│  └─ Library + neural foley                                  │
│                                                              │
│  Layer 4: AMBIENCE                                          │
│  ├─ Scene-based (forest, city, room)                        │
│  └─ Dynamic (weather, time of day)                          │
│                                                              │
│  Layer 5: MUSIC                                             │
│  ├─ Adaptive score (scene emotion)                          │
│  └─ Stems mixing (tension ↑↓)                               │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 Open Source Components

| Task | Solution | Quality | Latency |
|------|----------|---------|---------|
| TTS | XTTS v2, StyleTTS2 | ⭐⭐⭐⭐ | 200–500ms |
| Voice clone | RVC, OpenVoice | ⭐⭐⭐⭐ | Real-time |
| Speech-to-Speech | GPT-SoVITS, Fish Speech | ⭐⭐⭐⭐ | 300–800ms |
| Emotion from text | Fine-tuned BERT | ⭐⭐⭐⭐ | 10ms |
| Emotion from audio | Wav2Vec classifier | ⭐⭐⭐ | 50ms |
| Phoneme alignment | Montreal Forced Aligner | ⭐⭐⭐⭐ | 100ms |
| Viseme mapping | Rhubarb Lip Sync | ⭐⭐⭐⭐ | 50ms |

### 3.4 Voice Output → Animation Input

```
TTS Output (audio waveform)
    │
    ├──► Phoneme Alignment (CTC/MFA)
    │         │
    │         └──► Viseme sequence with timing
    │                   │
    │                   └──► viseme_id (16D one-hot) ──┐
    │                                                   │
    ├──► Prosody Extraction                            │
    │         │                                        │
    │         └──► pitch, energy, tempo ───────────────┤
    │                                                   │
    └──► Emotion Classifier                            │
              │                                        │
              └──► emotion vector (8D) ────────────────┤
                                                       │
                                                       ▼
                                            ANIMA Neural Model
                                                       │
                                                       ▼
                                            Animation Params (170D)
```

### 3.5 Cost Comparison

**Per minute of generated content:**

| Component | Hume | Own Stack |
|-----------|------|-----------|
| TTS | included | $0.001 (GPU) |
| Emotion | included | $0.0001 (CPU) |
| Phoneme align | N/A | $0.0002 (CPU) |
| Voice clone | N/A | $0.001 (GPU) |
| **Total** | **$0.05–0.10** | **$0.002–0.003** |

**20–30× cheaper.**

### 3.6 Code Structure

```
anima-audio/
├─ tts/
│   ├─ xtts_inference.py       # XTTS v2 wrapper
│   ├─ styletts_inference.py   # StyleTTS2 wrapper  
│   ├─ voice_bank.py           # Character voice storage
│   └─ multilang.py            # Language routing
├─ emotion/
│   ├─ text_classifier.py      # Text → emotion (8D)
│   ├─ audio_classifier.py     # Audio → emotion (8D)
│   └─ emotion_to_params.py    # Emotion → animation hints
├─ sync/
│   ├─ phoneme_align.py        # Audio + text → timing
│   ├─ viseme_mapper.py        # Phonemes → visemes (16)
│   └─ lip_sync.py             # Visemes → mouth params
├─ sfx/
│   ├─ trigger_parser.py       # Script → SFX triggers
│   ├─ foley_generator.py      # Procedural sounds
│   └─ mixer.py                # Layer mixing
└─ music/
    ├─ adaptive_score.py       # Emotion → music selection
    └─ stems_mixer.py          # Dynamic mixing
```

---

## 4. ANIMA SDK — Custom Animation Engine

### 4.1 Why Not Live2D

| Issue | Impact |
|-------|--------|
| Proprietary SDK | License cost, no modification |
| Physics overhead | Unpredictable performance |
| Parameter limits | Can't express arbitrary deformations |
| No neural integration | Can't blend GenAI face into pipeline |
| Format lock-in | .moc3 is closed |

### 4.2 ANIMA SDK Design

**Open-source WebGL2 engine optimized for hybrid neural/parametric rendering.**

```
ANIMA SDK Architecture:

┌─────────────────────────────────────────┐
│           ANIMA SDK Core                │
├─────────────────────────────────────────┤
│  Asset Pipeline                         │
│  ├─ Import: Live2D (.moc3), Spine, PSD │
│  ├─ Convert to ANIMA format (.anima)    │
│  └─ Export: mesh + skeleton + params    │
├─────────────────────────────────────────┤
│  Deformation Engine                     │
│  ├─ Mesh skinning (GPU)                 │
│  ├─ Blend shapes (facial)               │
│  ├─ Bone IK (body)                      │
│  └─ Neural texture injection point      │
├─────────────────────────────────────────┤
│  Render Pipeline                        │
│  ├─ Layer compositor                    │
│  ├─ Neural face overlay                 │
│  ├─ Particle system                     │
│  ├─ Post-processing                     │
│  └─ Output: Canvas / Video stream       │
├─────────────────────────────────────────┤
│  Runtime                                │
│  ├─ Parameter interpolation             │
│  ├─ Animation state machine             │
│  ├─ Event system                        │
│  └─ Performance profiler                │
└─────────────────────────────────────────┘
```

### 4.3 Neural Face Injection

**Key innovation:** SDK has explicit slot for neural-rendered face region.

```
Frame composition:
1. Render body/background (parametric, fast)
2. Receive neural face texture from ANIMA Core
3. Composite face into head region with alpha blend
4. Apply unified post-processing
5. Output final frame
```

This allows GenAI to control face while SDK handles everything else efficiently.

### 4.4 Live2D Compatibility Layer

```
Import pipeline:
.moc3 → parse → extract:
  - Mesh topology
  - Texture atlas
  - Parameter definitions
  - Deformer hierarchy
→ Convert to .anima format
→ Load in ANIMA SDK

Goal: Drop-in replacement for existing Live2D assets
```

### 4.5 SDK Advantages

| Feature | Live2D | ANIMA SDK |
|---------|--------|-----------|
| License | Proprietary | MIT |
| Neural integration | No | Native |
| Physics control | Limited | Full |
| Custom shaders | No | Yes |
| Format | Closed | Open |
| Performance profiling | Basic | Deep |

---

## 5. Neural Architecture — Flow Matching

### 5.1 Core Principle

**ANIMA generates parameters, not pixels.**

```
Traditional (rule-based):
  phoneme "a" → mouth_open = 0.8 (lookup table)

ANIMA (neural):
  (audio, emotion, context, prev_frame) → Flow Matching → 170D params
```

### 5.2 Full Inference Pipeline

```
┌─────────────────────────────────────────────────────────────────┐
│                    ANIMA INFERENCE PIPELINE                      │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  INPUTS (per frame)                                             │
│  ├─ audio_features: [mel: 80D, phoneme: 32D] = 112D             │
│  ├─ emotion: 8D (joy, sad, anger, fear, surprise, disgust,      │
│  │                contempt, neutral)                             │
│  ├─ viseme_id: 16D (one-hot)                                    │
│  ├─ character_id: 64D (embedding)                               │
│  └─ prev_params: 170D (temporal continuity)                     │
│                                                                  │
│      Total input: 370D                                          │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STAGE 1: CONTEXT ENCODER                                       │
│  ┌────────────────────────────────────────────┐                 │
│  │  Linear(370 → 512)                         │                 │
│  │  ↓                                         │                 │
│  │  Transformer (4 layers, 8 heads, dim=512)  │                 │
│  │  ↓                                         │                 │
│  │  Linear(512 → 256) → Z_context             │                 │
│  └────────────────────────────────────────────┘                 │
│  Params: ~15M | Latency: ~8ms                                   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  STAGE 2: FLOW MATCHING DECODER                                 │
│  ┌────────────────────────────────────────────┐                 │
│  │  Input: Z_context (256D) + noise (170D)    │                 │
│  │  ↓                                         │                 │
│  │  Concat → 426D                             │                 │
│  │  ↓                                         │                 │
│  │  Velocity Network:                         │                 │
│  │    Linear(426 → 512)                       │                 │
│  │    ReLU + LayerNorm                        │                 │
│  │    Linear(512 → 512)                       │                 │
│  │    ReLU + LayerNorm                        │                 │
│  │    Linear(512 → 512)                       │                 │
│  │    ReLU + LayerNorm                        │                 │
│  │    Linear(512 → 170) → velocity            │                 │
│  │  ↓                                         │                 │
│  │  ODE step: params = noise + velocity       │                 │
│  └────────────────────────────────────────────┘                 │
│  Params: ~2M | Latency: ~12ms                                   │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OUTPUT: animation_params (170D)                                │
│  ├─ face: 80D (mouth, eyes, brows, cheeks)                      │
│  ├─ head: 20D (position, rotation, tilt)                        │
│  ├─ body: 50D (spine, shoulders, arms)                          │
│  └─ effects: 20D (blush, sweat, particles)                      │
│                                                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  TOTAL: ~17M params | ~20ms latency | 50 FPS capable            │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.3 Flow Matching — How It Works

```python
# Training
def train_step(x_0, condition):
    """
    x_0: ground truth params (170D)
    condition: Z_context (256D)
    """
    # Sample random timestep
    t = torch.rand(batch_size)
    
    # Sample noise
    x_1 = torch.randn_like(x_0)
    
    # Interpolate (linear path from noise to data)
    x_t = t * x_0 + (1 - t) * x_1
    
    # Target velocity = direction from noise to data
    v_target = x_0 - x_1
    
    # Predict velocity
    v_pred = velocity_network(x_t, t, condition)
    
    # Loss
    loss = F.mse_loss(v_pred, v_target)
    return loss


# Inference (single step!)
def generate(condition):
    """
    condition: Z_context from encoder
    """
    # Start from noise
    x_1 = torch.randn(170)
    
    # Single ODE step at t=0
    velocity = velocity_network(x_1, t=0, condition)
    
    # Move from noise to data
    x_0 = x_1 + velocity
    
    return x_0  # animation params
```

### 5.4 Why Flow Matching (Not Diffusion)

```
Diffusion:
  z_noise → step → step → step → ... → z_clean
            (20-50 steps, 500ms+)

Flow Matching:
  z_noise → single ODE step → z_clean
            (1 step, 15-20ms)
```

| Aspect | Diffusion | Flow Matching |
|--------|-----------|---------------|
| Steps | 20–50 | 1 |
| Latency | 200ms+ | 15–25ms |
| Quality | Excellent | Very good |
| Training | Stable | Stable |
| **Real-time viable** | **No** | **Yes** |

### 5.5 Parameter Space (170D)

| Category | Parameters | Dimensions |
|----------|------------|------------|
| **Mouth** | open, form, smile, teeth, lip_sync | 12D |
| **Eyes** | open L/R, pupil X/Y, squint, widen | 12D |
| **Eyebrows** | angle L/R, height, furrow | 8D |
| **Cheeks** | puff, blush intensity | 4D |
| **Face misc** | nose wrinkle, jaw | 4D |
| **Emotion blend** | 8 emotions × intensity | 8D |
| **Viseme blend** | 16 visemes × weight | 16D |
| **Head** | pos XYZ, rot XYZ | 6D |
| **Neck** | bend, twist | 4D |
| **Spine** | upper, lower, lean | 6D |
| **Shoulders** | L/R up/down, forward | 6D |
| **Arms** | L/R rotation, bend | 12D |
| **Hands** | L/R open, gesture_id | 8D |
| **Breathing** | chest, rhythm phase | 4D |
| **Effects** | blush, sweat, tears, sparkle | 8D |
| **Camera** | shake, zoom, focus | 6D |
| **Reserved** | future expansion | 46D |
| **Total** | | **170D** |

### 5.6 Temporal Smoothing

```
Problem: per-frame generation can jitter

Solution 1: prev_params in input (built-in)
  → Model learns temporal coherence

Solution 2: EMA on output
  smoothed = 0.3 * current + 0.7 * previous

Solution 3: Chunk-based (generate 4 frames at once)
  → Better temporal coherence, slightly higher latency
```

### 5.7 Model Specifications

| Metric | Value |
|--------|-------|
| Total Parameters | 17M |
| Input dimension | 370D |
| Output dimension | 170D |
| Latency (A100) | 20ms |
| Latency (RTX 3090) | 25ms |
| Latency (CPU) | 80ms |
| Memory footprint | ~100MB |
| Batch capacity | 32 streams / A100 |
| Throughput | 1600 FPS / A100 |

### 5.8 Comparison with Alternatives

| Approach | Params | Latency | Quality | Training time |
|----------|--------|---------|---------|---------------|
| **ANIMA Flow** | 17M | 20ms | High | 1 week |
| Diffusion | 100M+ | 500ms+ | Higher | 2 weeks |
| VAE + LSTM | 50M | 40ms | Medium | 1 week |
| MLP simple | 5M | 5ms | Low | 2 days |
| Rule-based | 0 | 1ms | Limited | N/A |

---

## 6. Animation Sources & Procedural Layer

### 6.1 Unified Parameter Output

The neural network outputs ALL parameters (face + body + effects) in one pass. But some aspects benefit from procedural augmentation:

### 6.2 Procedural Additions (Client-Side)

| Source | What | How |
|--------|------|-----|
| **Breathing** | Chest/shoulder micro-motion | sin(t × 0.5) modulation |
| **Idle sway** | Subtle body movement | Perlin noise |
| **Blink** | Natural eye blinks | Random 2–6 sec interval |
| **Physics** | Hair, clothing secondary motion | Simple spring simulation |

These run in ANIMA SDK (client), not server — zero additional latency.

### 6.3 Gesture Library

Pre-defined gesture sequences triggered by keywords or explicit commands:

| Gesture | Trigger | Duration |
|---------|---------|----------|
| Wave | "hello", "bye" | 1.5s |
| Nod | "yes", agreement | 0.8s |
| Shake head | "no", disagreement | 1.0s |
| Shrug | "I don't know" | 1.2s |
| Point | directive intent | 1.0s |
| Thinking | "hmm", pause | 2.0s |

Gestures blend with neural output via lerp.

---

## 7. Training Data Strategy

### 7.1 Data Sources

| Source | Volume | What We Extract |
|--------|--------|-----------------|
| **VTuber streams** | 10K+ hours | Audio → face tracking → params |
| **Live2D showcases** | 1K+ hours | Clean parameter sequences |
| **Anime clips** | 5K+ hours | Face landmarks → pseudo-params |
| **Hand-animated** | 100 hours | Gold standard pairs |
| **Synthetic** | Unlimited | TTS + rule-based animator |

### 7.2 Parameter Extraction Pipeline

```
Video/Stream input
    │
    ├──► Audio track extraction
    │         │
    │         ├──► Phoneme alignment (MFA) → timing
    │         └──► Emotion classifier → emotion (8D)
    │
    └──► Video frames
              │
              ├──► Face landmark detection (MediaPipe)
              │         │
              │         └──► Estimate: mouth, eyes, brows → ~40D
              │
              └──► Pose estimation
                        │
                        └──► Body params → ~30D

Result: (audio_features, emotion, visemes) → (170D params) per frame
```

### 7.3 Synthetic Data Generation

```
For unlimited training data:

1. Sample emotion trajectory (random walk)
2. Generate text matching emotion
3. TTS → audio waveform
4. Rule-based animator → baseline params
5. Add noise/variation
6. Model learns to exceed baseline quality

Advantage: infinite data, controlled conditions
Disadvantage: ceiling on quality (rules-based ground truth)
```

### 7.4 Training Procedure

| Stage | Duration | Data | Goal |
|-------|----------|------|------|
| 1. Pretraining | 3 days | Synthetic (10M frames) | Learn basic motion |
| 2. Fine-tuning | 4 days | VTuber (1M frames) | Real motion patterns |
| 3. Style adaptation | 1 day | Target avatar (10K frames) | Character specifics |

**Total: ~1 week training time on 4× A100**

---

## 8. Model Architecture Summary

### 8.1 Complete System

```
┌─────────────────────────────────────────────────────────────────┐
│                      ANIMA FULL PIPELINE                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  OFFLINE (Content Generation)                                   │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Script → TTS → Audio → Phoneme Align → Emotion Extract  │   │
│  │                              ↓                           │   │
│  │                    (audio_feat, emotion, viseme)         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  REAL-TIME (Inference)                                          │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ (audio_feat, emotion, viseme, char_id, prev) → 370D      │   │
│  │                              ↓                           │   │
│  │              Context Encoder (15M) → Z (256D)            │   │
│  │                              ↓                           │   │
│  │              Flow Decoder (2M) → Params (170D)           │   │
│  │                              ↓                           │   │
│  │                      JSON → WebSocket                    │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  CLIENT                                                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ JSON → Interpolation → SDK → WebGL Canvas                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 8.2 Inference Timeline

```
T=0ms    Audio features ready
         │
T=8ms    Context Encoder complete → Z (256D)
         │
T=20ms   Flow Decoder complete → Params (170D)
         │
T=22ms   JSON encoded, sent via WebSocket
         │
         ════════════ NETWORK (~10ms) ════════════
         │
T=32ms   Client receives JSON
         │
T=33ms   Interpolation + SDK apply
         │
T=38ms   WebGL render complete → Frame displayed

Total: ~38ms end-to-end (50+ FPS capable)
```

### 8.3 Model Specifications

| Component | Params | Latency |
|-----------|--------|---------|
| Context Encoder (Transformer 4L) | 15M | 8ms |
| Flow Velocity Network | 2M | 12ms |
| **Total Neural** | **17M** | **20ms** |
| JSON encode + network | — | 12ms |
| Client render | — | 6ms |
| **End-to-End** | | **~38ms** |

### 8.4 Scaling

| Metric | Value |
|--------|-------|
| Memory per model | ~100MB |
| Batch size (A100 40GB) | 400 streams |
| Throughput | 12,000 FPS |
| Concurrent users per A100 | 400 (@ 30 FPS) |
| Cost per user-hour | ~$0.005 |

---

## 9. Streaming Protocol — JSON Canvas Instructions

### 9.1 Core Architecture Principle

**ANIMA does NOT stream video. ANIMA streams rendering instructions.**

```
┌─────────────────┐         JSON params        ┌─────────────────┐
│  ANIMA Backend  │ ───────────────────────►   │  Client Browser │
│  (GPU inference)│      ~1KB/frame            │  (Canvas/WebGL) │
│                 │                            │                 │
│  Generates:     │                            │  Renders:       │
│  - Parameters   │                            │  - Full frames  │
│  - Instructions │                            │  - 30 FPS       │
│  - Events       │                            │  - Local GPU    │
└─────────────────┘                            └─────────────────┘
```

**Why this matters:**
- Server: lightweight inference (~30ms), no video encoding
- Bandwidth: ~30 KB/s (JSON) vs 2–5 Mbps (video)
- Client: full control over rendering, local GPU acceleration
- Scalability: 100× more users per GPU

### 9.2 Message Format

```json
{
  "frame_id": 1234,
  "timestamp_ms": 41133,
  "face": {
    "mouth_open": 0.7,
    "mouth_form": 0.3,
    "eye_l_open": 0.9,
    "eye_r_open": 0.85,
    "eyebrow_l": 0.1,
    "eyebrow_r": 0.15,
    "emotion_blend": {
      "happy": 0.6,
      "surprised": 0.2
    }
  },
  "body": {
    "position": [0.5, 0.6],
    "rotation": 0.02,
    "spine_bend": 0.05,
    "arm_l": [-0.3, 0.1],
    "arm_r": [0.2, -0.1]
  },
  "effects": [
    {"type": "particle", "emit": true, "position": [0.5, 0.3]},
    {"type": "glow", "intensity": 0.4}
  ],
  "audio_sync": {
    "viseme_id": 8,
    "viseme_weight": 0.9,
    "phoneme": "a"
  }
}
```

### 9.3 Delta Encoding

Only send what changed:

```json
{
  "frame_id": 1235,
  "delta": true,
  "face.mouth_open": 0.65,
  "face.emotion_blend.happy": 0.7,
  "audio_sync.viseme_id": 3
}
```

**Typical frame size:** 200–500 bytes (delta) vs 2KB (full state)

### 9.4 Transport Options

| Protocol | Latency | Use Case |
|----------|---------|----------|
| WebSocket | 10–30ms | Default, reliable |
| WebRTC DataChannel | 5–15ms | Ultra-low latency |
| SSE | 30–50ms | Fallback, simple |

### 9.5 Client-Side Rendering

ANIMA SDK (WebGL2) receives JSON and renders locally:

```
JSON instructions → ANIMA SDK → Canvas/WebGL

Rendering pipeline:
1. Parse delta/full state
2. Interpolate between frames (smoothing)
3. Apply to mesh deformations
4. Composite layers (background → body → face → effects)
5. Post-process (color grading, glow)
6. Output to canvas
```

**Client GPU does the heavy lifting, server only thinks.**

---

## 10. Infrastructure

### 10.1 Backend Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     ANIMA BACKEND                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  CONTENT PIPELINE (Offline)                                 │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Script → TTS (XTTS v2) → Phoneme Align → Emotion    │  │
│  │                          ↓                            │  │
│  │              Pre-computed audio + features            │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  INFERENCE SERVICE (Real-time)                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  FastAPI Gateway                                      │  │
│  │  ├─ Session manager                                   │  │
│  │  ├─ WebSocket handler                                 │  │
│  │  └─ Load balancer                                     │  │
│  │              ↓                                        │  │
│  │  GPU Workers (A100)                                   │  │
│  │  ├─ Flow Matching inference (17M model)               │  │
│  │  ├─ Batched: 400 streams per GPU                     │  │
│  │  └─ Latency: 20ms per batch                          │  │
│  │              ↓                                        │  │
│  │  Redis                                                │  │
│  │  ├─ Session state                                     │  │
│  │  └─ Metrics                                           │  │
│  └───────────────────────────────────────────────────────┘  │
│                          ↓                                   │
│                    WebSocket                                 │
│                          ↓                                   │
│                      Client                                  │
└─────────────────────────────────────────────────────────────┘
```

### 10.2 Scaling — The JSON Advantage

**Video streaming approach (HeyGen, Synthesia):**
- GPU renders frames → encodes video → streams
- Heavy: encoding + bandwidth
- ~5–10 users per A100

**ANIMA approach (JSON instructions):**
- GPU infers parameters → sends JSON → client renders
- Light: just inference, minimal bandwidth
- ~400 users per A100

| Metric | Video Streaming | ANIMA (JSON) |
|--------|-----------------|--------------|
| GPU work per frame | Render + Encode | Inference only |
| Bandwidth per user | 2–5 Mbps | 30–100 KB/s |
| Users per A100 | 5–10 | **400** |
| Server cost per user | High | **40–80× lower** |

### 10.3 Cost Model — Final Economics

**Per-minute costs (own stack):**

| Component | Cost/min | Notes |
|-----------|----------|-------|
| TTS (XTTS v2) | $0.001 | GPU, amortized |
| Phoneme align | $0.0002 | CPU |
| Emotion classifier | $0.0001 | CPU |
| Flow inference | $0.0004 | GPU, 400 users/A100 |
| Bandwidth | $0.0001 | ~30 KB/s |
| **Total** | **$0.002/min** | |

**Comparison with competitors:**

| Provider | Price/min | Our cost/min | Potential margin |
|----------|-----------|--------------|------------------|
| HeyGen | $0.30 | $0.002 | **150×** |
| Synthesia | $0.50 | $0.002 | **250×** |
| D-ID | $0.20 | $0.002 | **100×** |
| Character.ai (text) | ~$0.01 | $0.002 | 5× |

**Why we're cheap:**
- No Hume ($0.05–0.10/min saved)
- JSON streaming, not video
- Small model (17M vs 100M+)
- High batching (400 users per GPU)

### 10.4 Pricing Strategy

**B2C (End users):**
- Free tier: 60 min/month
- Pro: $10/month for 20 hrs ($0.008/min)
- Unlimited: $25/month

**B2B (Developers, studios):**
- API: $0.03/min (15× margin)
- Self-hosted: License + support

**Content platforms (Interactive Anime):**
- Per-view: $0.001–0.003
- Subscription revenue share

### 10.5 Infrastructure Costs (Monthly)

**For 10,000 concurrent users:**

| Component | Cost |
|-----------|------|
| GPU (25× A100 spot @ $1/hr) | $18,000 |
| CPU (TTS, alignment) | $2,000 |
| Servers (API, Redis) | $1,000 |
| Bandwidth | $500 |
| **Total** | **$21,500** |

**Per concurrent user:** $2.15/month
**Per active minute:** $0.002

**Unit economics @ $0.03/min API:**
- Cost: $0.002/min
- Margin: 93%
- 1M minutes/month = $30K revenue, $28K profit

---

## 11. Use Cases & Applications

### 11.1 Primary Use Cases

| Category | Use Case | Description | Revenue Model |
|----------|----------|-------------|---------------|
| **Gaming** | NPC companions | AI characters that talk, emote, react | Per-game license |
| **Gaming** | Visual novels | Interactive story with animated avatars | SDK license |
| **Gaming** | VTuber tools | Real-time avatar for streamers | SaaS subscription |
| **Entertainment** | Interactive anime | Choose-your-story anime series | Per-episode/subscription |
| **Entertainment** | AI companions | Chat companions with personality | Consumer subscription |
| **Education** | AI tutors | Animated teachers for e-learning | B2B licensing |
| **Business** | Virtual assistants | Customer service avatars | Enterprise API |
| **Social** | Avatar chat | Animated self-expression in chat | Freemium |

### 11.2 Interactive Anime Series

**Concept:** Netflix-style anime where viewer choices affect story, characters react in real-time.

```
Viewer experience:
┌─────────────────────────────────────────┐
│  Episode plays (pre-rendered anime)     │
│                 ↓                       │
│  Decision point: "What do you say?"     │
│  [Option A] [Option B] [Option C]       │
│                 ↓                       │
│  ANIMA avatar reacts LIVE to choice     │
│  - Emotional response (real-time)       │
│  - Dialogue (TTS + voice clone)         │
│  - Unique scene based on choice         │
│                 ↓                       │
│  Story branches, continues              │
└─────────────────────────────────────────┘
```

**Technical approach:**
- Pre-rendered: background scenes, action sequences
- ANIMA real-time: character close-ups, dialogue scenes, reactions
- Hybrid: seamless transition between pre-rendered and live

**Business model:**
- Subscription: $15/month for interactive anime platform
- Per-series: $5–10 for premium interactive series
- In-episode purchases: alternate storylines, character relationships

### 11.3 Gaming Applications

**Visual Novel / Dating Sim:**
- Full character animation during dialogue
- Emotion reacts to player choices
- Voice synthesis for all text
- Cost: ~$0.01 per conversation minute

**RPG NPCs:**
- Shopkeepers, quest givers come alive
- Dynamic reactions to player reputation/actions
- Procedural dialogue with consistent personality

**Companion Apps:**
- Mobile games with AI companion
- Tamagotchi-style virtual pets with personality
- Idle games with interactive characters

**Streaming/VTuber:**
- Real-time avatar driven by voice
- Emotion detection from streamer
- Chat integration for audience interaction

### 11.4 Enterprise Applications

| Application | Value Proposition |
|-------------|-------------------|
| Customer support | Animated avatar instead of chatbot text |
| E-learning | Engaging AI instructor with personality |
| Corporate training | Interactive scenarios with realistic NPCs |
| Virtual events | Animated hosts and presenters |
| Healthcare | Empathetic patient communication |

---

## 12. Game Engine Integration

### 12.1 Architecture Philosophy

**ANIMA is an Avatar Service, NOT a game engine.**

```
Game Engine (Unity/Godot/Phaser/Custom)
    │
    │ ANIMA Client SDK (lightweight)
    │
    ▼
ANIMA Service (cloud)
    │
    │ JSON canvas instructions
    │
    ▼
ANIMA SDK renders in game's canvas/texture
```

### 12.2 Integration Options

| Game Type | Recommended Stack | ANIMA Integration |
|-----------|-------------------|-------------------|
| Web Visual Novel | Ink.js + Vanilla JS | Direct canvas overlay |
| Web 2D Game | Phaser.js / PixiJS | Texture in scene |
| Web 3D Game | Three.js / Babylon | Render-to-texture plane |
| Desktop/Mobile | Godot | GDScript addon |
| AAA/Complex | Unity WebGL | C# plugin |
| Lightweight Chat | Pure HTML/CSS/JS | Video element or canvas |

### 12.3 ANIMA Client SDK

Lightweight library for any environment:

```
anima-client-sdk/
├─ web/           # Browser (ES modules, UMD)
│   ├─ anima-client.js
│   └─ anima-renderer.js  (WebGL canvas)
├─ godot/         # GDScript addon
├─ unity/         # C# package
└─ python/        # Ren'Py / server-side

Core API:
- connect(url, apiKey)
- speak(text, {emotion, gesture})
- setEmotion(emotion, intensity)
- triggerGesture(gesture)
- onFrame(callback)        // receive JSON params
- onEvent(callback)        // avatar events
- getCanvas()              // get render target
```

### 12.4 Web Integration Example (Ink.js Visual Novel)

```javascript
// Minimal visual novel setup
import { AnimaClient, AnimaRenderer } from 'anima-sdk';
import { Story } from 'inkjs';

const anima = new AnimaClient('wss://api.anima.ai');
const renderer = new AnimaRenderer(document.getElementById('avatar-canvas'));
const story = new Story(storyJson);

anima.onFrame(params => renderer.render(params));

async function continueStory() {
  while (story.canContinue) {
    const text = story.Continue();
    const tags = story.currentTags;
    
    // Parse ANIMA tags from Ink
    const emotion = tags.find(t => t.startsWith('emotion:'))?.split(':')[1];
    const gesture = tags.find(t => t.startsWith('gesture:'))?.split(':')[1];
    
    // Avatar speaks with emotion
    await anima.speak(text, { emotion, gesture });
    
    // Show choices if any
    if (story.currentChoices.length > 0) {
      showChoices(story.currentChoices);
      break;
    }
  }
}
```

### 12.5 Ink Script Example

```ink
=== tavern_meeting ===
# scene: tavern_interior
# music: tavern_ambient

店主が近づいてきた。
# avatar: shopkeeper
# emotion: friendly

SHOPKEEPER: やあ、旅人さん。何かお探しかい？
# gesture: wave
# emotion: curious

* [情報を聞く]
  SHOPKEEPER: ふむ、この辺りで何か変わったことか...
  # emotion: thoughtful
  -> info_path
  
* [買い物をする]
  SHOPKEEPER: もちろんだ！何がいるんだい？
  # emotion: excited
  # gesture: present_goods
  -> shop_path
  
* [無視して去る]
  SHOPKEEPER: ...まあ、また来てくれ。
  # emotion: disappointed
  -> leave_tavern
```

### 12.6 Godot Integration

```gdscript
# AnimaAvatar.gd
extends Control

@export var api_key: String
@export var avatar_id: String

var client: AnimaClient
var renderer: AnimaRenderer

func _ready():
    client = AnimaClient.new()
    client.connect_to_service("wss://api.anima.ai", api_key)
    client.frame_received.connect(_on_frame)
    
    renderer = AnimaRenderer.new()
    add_child(renderer)

func speak(text: String, emotion: String = "neutral"):
    client.speak(text, {"emotion": emotion})

func set_emotion(emotion: String, intensity: float = 1.0):
    client.set_emotion(emotion, intensity)

func _on_frame(params: Dictionary):
    renderer.apply_params(params)

# Usage in game:
func _on_npc_interact():
    $AnimaAvatar.speak("冒険者さん、ようこそ！", "excited")
```

### 12.7 Why Not Build a Game Engine

| Own Game Engine | Problems |
|-----------------|----------|
| Physics | Box2D/Matter.js exist |
| Scene graph | Years of development |
| Input handling | Browser quirks |
| Asset pipeline | Unity/Godot did 10+ years |
| Level editor | Massive scope creep |

**ANIMA's value = GenAI avatars, not game infrastructure.**

Developers use familiar tools (Unity, Godot, web frameworks), ANIMA adds the "living" avatar as a service.

---

## 13. Competitive Positioning

### 13.1 Market Landscape (2025)

| Player | Approach | Latency | Limitation |
|--------|----------|---------|------------|
| HeyGen | Pre-trained humans | <100ms | No stylized avatars |
| Synthesia | Render farm | Seconds | Not real-time |
| D-ID | GAN talking head | ~200ms | Limited expression |
| VTube Studio | Parameter-based | <10ms | No AI, manual |
| **ANIMA** | **Neural params + JSON** | **35–50ms** | **Stylized 2D focus** |

### 13.2 Unique Value Proposition

1. **JSON streaming** — 100× cheaper than video rendering
2. **Real-time** — 30 FPS, <50ms latency
3. **Stylized aesthetic** — VTuber/anime, not photorealistic
4. **Open SDK** — no Live2D lock-in
5. **Emotion-native** — Hume integration from day one
6. **Game-ready** — easy integration with any engine

### 13.3 Why We Win

| vs Competitor | Our Advantage |
|---------------|---------------|
| HeyGen/Synthesia | 100× lower cost, stylized avatars |
| VTube Studio | AI-driven, no manual rigging |
| D-ID | Better expression, lower latency |
| Custom dev | 6+ months saved, production-ready |

---

## 14. Implementation Roadmap

### Phase 1: Foundation (Weeks 1–4)

| Week | Deliverable |
|------|-------------|
| 1 | Hume EVI integration, audio → emotion pipeline |
| 2 | ANIMA SDK skeleton, WebGL2 renderer, Live2D import |
| 3 | Basic parametric body animation |
| 4 | End-to-end demo: Hume → SDK → animated Octopus (no GenAI face yet) |

**Milestone:** Octopus speaks with Hume voice, body moves, face is parameter-based.

### Phase 2: Face Autoencoder (Weeks 5–6)

| Week | Deliverable |
|------|-------------|
| 5 | Collect face crops from VTuber data, train VAE |
| 6 | Validate reconstruction quality, optimize decoder |

**Milestone:** Can encode/decode anime faces at 256×256 in <10ms.

### Phase 3: Face Flow Model (Weeks 7–10)

| Week | Deliverable |
|------|-------------|
| 7 | Flow matching training setup |
| 8–9 | Train on VTuber data with audio/emotion conditioning |
| 10 | Integrate into pipeline, benchmark latency |

**Milestone:** GenAI face moves with audio, emotion affects expression.

### Phase 4: Integration & Polish (Weeks 11–14)

| Week | Deliverable |
|------|-------------|
| 11 | Face composite into SDK |
| 12 | End-to-end streaming (video or hybrid) |
| 13 | Performance optimization, batching |
| 14 | QA, lip-sync accuracy testing |

**Milestone:** Production-ready ANIMA with GenAI face.

### Phase 5: Scale (Weeks 15–20)

| Week | Deliverable |
|------|-------------|
| 15–16 | Own TTS (StyleTTS2) to reduce Hume cost |
| 17–18 | Multi-avatar support |
| 19–20 | SDK public release, documentation |

**Total: 20 weeks to full production system**

---

## 15. Open Risks

| Risk | Severity | Mitigation |
|------|----------|------------|
| Neural param quality vs rules | Medium | Start with rules baseline, A/B test |
| Hume latency adds up | Medium | Async pipeline, buffering |
| SDK development scope | Medium | Start minimal, iterate |
| VTuber data licensing | Medium | Focus on permissive sources, synthetic |
| Client GPU variance | Low | Fallback to simpler rendering |
| WebGL compatibility | Low | Test on target browsers early |

---

## 16. Success Criteria

### MVP (Week 4)
- [ ] Octopus speaks with Hume voice
- [ ] Body reacts to emotion
- [ ] 30 FPS stable
- [ ] <100ms end-to-end latency

### Neural Parameters (Week 14)
- [ ] Flow-based param generator integrated
- [ ] Lip-sync error <50ms
- [ ] Emotion expression matches Hume
- [ ] Quality exceeds rule-based baseline

### Production (Week 20)
- [ ] 100+ concurrent users per A100
- [ ] Own TTS operational
- [ ] SDK public release
- [ ] <$0.01/min cost

---

## 17. Appendix: Technology Choices

### 17.1 Why Flow Matching (Not Diffusion)

| Aspect | Diffusion | Flow Matching |
|--------|-----------|---------------|
| Steps | 20–50 | 1–4 |
| Latency | 500ms+ | 20–50ms |
| Quality | Excellent | Very good |
| Training | Stable | Stable |
| **Real-time viable** | **No** | **Yes** |

### 17.2 Why WebGL2 (Not WebGPU)

- WebGPU support still incomplete (Safari, older browsers)
- WebGL2 sufficient for 2D compositing
- Migrate to WebGPU when mature

### 17.3 Why Hume (Not OpenAI/ElevenLabs)

| Provider | Emotion | Latency | Integration |
|----------|---------|---------|-------------|
| Hume EVI | Native, excellent | Low | WebSocket, clean |
| OpenAI | None | Medium | REST only |
| ElevenLabs | Basic | Medium | Good but no emotion |

---

## 18. Vector Worlds — Generative Scenes with Physics

### 18.1 Vision

ANIMA doesn't just animate avatars — it generates **entire interactive vector worlds** in real-time. Everything computed on backend: scene generation, physics simulation, compositing. Client receives lightweight vector commands.

**Why Vector:**
- Resolution-independent (infinite zoom)
- 10–50 KB/frame (vs megabytes for video)
- Deterministic rendering (same commands = same output)
- Stylistically consistent (no compression artifacts)
- Editable/interactive (objects have identity)

### 18.2 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BACKEND (Full Compute)                    │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │    SCENE     │    │   PHYSICS    │    │   VECTOR     │  │
│  │  GENERATOR   │───▶│   ENGINE     │───▶│  COMPOSITOR  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│         │                   │                   │           │
│         ▼                   ▼                   ▼           │
│  Neural/Procedural   Deterministic 60Hz   Path/Shape/      │
│  Scene Graph         State Simulation     Transform Stream │
│                                                              │
├─────────────────────────────────────────────────────────────┤
│                         STREAM                               │
│            Vector Commands (MessagePack, ~20KB/frame)        │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (Render Only)                      │
├─────────────────────────────────────────────────────────────┤
│  Canvas2D Path API  or  WebGL Vector Renderer               │
│  Apply transforms, draw paths, done                         │
└─────────────────────────────────────────────────────────────┘
```

### 18.3 Scene Generator

**Two modes:**

**Mode A: Procedural (Fast, Controllable)**
```
Input: Scene template + parameters
  - "underwater_cave": depth, coral_density, light_rays
  - "neon_city": building_height, traffic, time_of_day
  - "abstract_space": complexity, color_palette, motion_style

Process:
  1. Layout algorithm (grammar-based or noise-based)
  2. Object instantiation from library
  3. Style application (colors, strokes, effects)

Output: Vector Scene Graph
```

**Mode B: Neural (Creative, Surprising)**
```
Input: Text prompt + style reference
  - "psychedelic forest with glowing mushrooms"
  - "brutalist architecture melting into ocean"

Model: Scene Diffusion in Vector Space
  - Not pixel diffusion — generates vector primitives directly
  - Architecture: VectorFusion-style (text → SVG paths)
  - Output: Bezier paths, gradients, layer hierarchy

Latency: 200–500ms for initial generation, then procedural animation
```

### 18.4 Physics Engine

**Full simulation on backend. Deterministic. 60 Hz internal, 30 Hz output.**

#### 18.4.1 Rigid Bodies

```
Engine: Custom or Box2D-compatible (Rapier2D in Rust for speed)

Features:
  - Collision detection (polygon, circle, capsule)
  - Gravity, friction, restitution
  - Joints: revolute, prismatic, distance, rope
  - Triggers (non-colliding sensors)

Objects:
  - Static: walls, platforms, scenery
  - Dynamic: props, debris, interactive elements
  - Kinematic: animated platforms, moving obstacles
```

#### 18.4.2 Particle Systems

```
Types:
  - Point particles: sparks, dust, snow, rain
  - Trail particles: fire, smoke, magic effects
  - Sprite particles: leaves, bubbles, confetti

Features:
  - Emitters: point, line, area, mesh surface
  - Forces: gravity, wind, turbulence, attractors
  - Lifetime, fade, scale over time
  - Collision with rigid bodies (optional)

Budget: 10,000 particles @ 60Hz = trivial on modern CPU
```

#### 18.4.3 Soft Bodies

```
Types:
  - Cloth: flags, capes, curtains
  - Rope/Chain: cables, tentacles, hair strands
  - Jelly: blob characters, squishy objects
  - Pressure bodies: balloons, inflatable

Implementation:
  - Mass-spring systems (simple, fast)
  - Position-Based Dynamics (stable, controllable)
  - Verlet integration (good for cloth)

Constraints:
  - Distance (stretch resistance)
  - Bending (stiffness)
  - Collision (self and external)
```

#### 18.4.4 2D Fluids (Simplified)

```
NOT full Navier-Stokes (too expensive for real-time).

Option A: Metaballs
  - Particles with influence radius
  - Render as merged blobs
  - Good for: slime, lava, blobs
  - Cost: cheap

Option B: Height-field Water
  - 1D wave equation along surface
  - Splash particles for impacts
  - Good for: pools, puddles, waves
  - Cost: moderate

Option C: SPH Lite
  - Simplified Smoothed Particle Hydrodynamics
  - 500–1000 particles max
  - Good for: contained fluid bodies
  - Cost: moderate-high

Recommendation: Metaballs + Height-field for MVP
```

### 18.5 Vector Format

**Custom binary format optimized for streaming animation.**

```
Scene Graph Structure:

World
├─ Layers[] (z-ordered)
│   ├─ Layer
│   │   ├─ id: u32
│   │   ├─ transform: Transform2D
│   │   ├─ opacity: f32
│   │   ├─ blend_mode: enum
│   │   └─ objects: Object[]
│   │
│   └─ ...
│
└─ Physics State (separate channel)

Object Types:

Path {
  id: u32,
  commands: [MoveTo, LineTo, CurveTo, Close],
  fill: Fill | null,
  stroke: Stroke | null,
  transform: Transform2D
}

Shape {
  id: u32,
  type: Circle | Rect | Polygon | Ellipse,
  params: type-specific,
  fill: Fill | null,
  stroke: Stroke | null,
  transform: Transform2D
}

Group {
  id: u32,
  children: Object[],
  transform: Transform2D,
  clip: Path | null
}

Image {
  id: u32,
  texture_id: u32,  // pre-loaded texture atlas
  source_rect: Rect,
  transform: Transform2D
}

Text {
  id: u32,
  content: string,
  font_id: u32,
  size: f32,
  fill: Fill,
  transform: Transform2D
}

Fill:
  | Solid { color: RGBA }
  | LinearGradient { stops: [(f32, RGBA)], start: Vec2, end: Vec2 }
  | RadialGradient { stops: [(f32, RGBA)], center: Vec2, radius: f32 }
  | Pattern { texture_id: u32, transform: Transform2D }

Stroke {
  color: RGBA,
  width: f32,
  line_cap: Butt | Round | Square,
  line_join: Miter | Round | Bevel,
  dash: [f32] | null
}

Transform2D {
  // 3x2 affine matrix, or decomposed:
  position: Vec2,
  rotation: f32,
  scale: Vec2,
  skew: Vec2
}
```

### 18.6 Delta Encoding

**Only send changes. Massive bandwidth savings.**

```
Frame N-1 State:
  Object 42: position (100, 200), rotation 0.0
  Object 43: position (300, 400), rotation 0.5
  Particle count: 1000

Frame N State:
  Object 42: position (102, 198), rotation 0.02  ← CHANGED
  Object 43: position (300, 400), rotation 0.5   ← SAME (skip)
  Particle count: 1050                            ← CHANGED

Delta Message:
{
  frame: 1234,
  timestamp_ms: 41166,
  
  transforms: [
    { id: 42, position: [102, 198], rotation: 0.02 }
  ],
  
  particles: {
    system_id: 1,
    spawned: 50,  // new particles with initial state
    died: [particle_ids...],
    // living particles: interpolate on client or send positions
  },
  
  // Full object updates only when shape/style changes
  objects: []
}

Compression: MessagePack + LZ4 → ~10-30 KB/frame typical
```

### 18.7 Client Renderer

**Thin client. Receives commands, renders vectors.**

```
Two options:

Option A: Canvas2D (Simpler)
  - Native Path2D API
  - Good gradient support
  - Sufficient for most 2D vector graphics
  - Limitation: no custom shaders

Option B: WebGL Vector (Advanced)
  - Tesselate paths to triangles (earcut/libtess)
  - GPU-accelerated fill/stroke
  - Custom shaders for effects
  - Signed Distance Field for smooth curves
  - Better performance at high complexity

Recommendation: Canvas2D for MVP, WebGL for scale

Client responsibilities:
  1. Receive delta stream
  2. Apply transforms to scene graph
  3. Render via Canvas2D/WebGL
  4. Handle input (click/touch → send to backend)
  5. Audio sync (lip-sync timing)
```

### 18.8 Performance Budget

**Target: 30 FPS with complex scenes**

| Component | Budget | Notes |
|-----------|--------|-------|
| Physics step | 5ms | 60Hz internal, batch 2 steps |
| Scene graph update | 2ms | Apply deltas |
| Vector serialize | 3ms | MessagePack encode |
| Network | 10ms | Variable, buffered |
| **Backend total** | **~20ms** | Comfortable margin |
| Client render | 10–15ms | Depends on complexity |
| **End-to-end** | **~50ms** | Acceptable for 30 FPS |

**Complexity limits (per frame):**
- Rigid bodies: 500 max
- Particles: 10,000 max
- Vector paths: 2,000 max
- Gradient fills: 200 max

### 18.9 Physics-Avatar Integration

**Avatar exists within physics world.**

```
Avatar ↔ World Interactions:

1. Avatar affects world:
   - Footsteps create ripples in water
   - Movement disturbs nearby particles
   - Gestures can push/grab objects
   - Voice creates sound waves (visual)

2. World affects avatar:
   - Wind moves hair/clothing (soft body)
   - Rain/snow particles land on avatar
   - Lighting changes based on scene
   - Physics objects can bonk avatar

3. Shared physics space:
   - Avatar has collision body
   - Can ride physics platforms
   - Interact with joints (hold rope, etc.)
```

### 18.10 Scene Types (Examples)

```
1. UNDERWATER CAVE
   - Fluid: height-field water surface + caustics
   - Particles: bubbles, floating debris
   - Soft body: seaweed, jellyfish tentacles
   - Rigid: rocks, shells, treasure
   - Avatar: swimming animation, hair floats

2. NEON CITY
   - Rigid: vehicles, flying drones
   - Particles: rain, sparks, holographic glitter
   - Soft body: flags, cables, neon signs swaying
   - Effects: glow, reflections on wet ground
   - Avatar: walking, interacting with props

3. ABSTRACT SPACE
   - Particles: stars, energy flows
   - Soft body: flowing ribbons, morphing shapes
   - Procedural: fractal generation, noise fields
   - No rigid physics — pure visual
   - Avatar: floating, ethereal movement

4. COZY INTERIOR
   - Rigid: furniture, objects, physics toys
   - Soft body: curtains, blankets, pet
   - Particles: dust motes, fireplace sparks
   - Fluid: coffee cup steam, fish tank
   - Avatar: sitting, interacting with objects
```

---

## 17. Updated Architecture (Full System)

### 17.1 Complete Data Flow

```
USER INPUT
├─ Voice → Hume EVI → emotion + audio
├─ Text prompt → Scene Generator
└─ Interaction → Physics triggers

        ↓

ANIMA BACKEND (GPU + CPU)
│
├─ SCENE GENERATOR (GPU, async)
│   ├─ Neural: text → vector scene (on prompt change)
│   └─ Procedural: template → instantiated scene
│
├─ PHYSICS ENGINE (CPU, 60Hz)
│   ├─ Rigid body simulation
│   ├─ Particle systems
│   ├─ Soft body solver
│   └─ Fluid simulation (simplified)
│
├─ AVATAR ENGINE (GPU, 30Hz)
│   ├─ GenAI Face (flow model)
│   ├─ Parametric Body
│   └─ Avatar ↔ Physics coupling
│
├─ VECTOR COMPOSITOR (CPU, 30Hz)
│   ├─ Scene graph + physics state
│   ├─ Avatar composite
│   ├─ Effects overlay
│   └─ Delta encoding
│
└─ STREAM ENCODER
    ├─ Vector commands (MessagePack)
    ├─ Face texture (if hybrid mode)
    └─ Audio (Opus)

        ↓ WebSocket/WebRTC

CLIENT (Render Only)
├─ ANIMA SDK (WebGL2/Canvas2D)
│   ├─ Vector renderer
│   ├─ Avatar compositor
│   └─ Post-processing
├─ Audio player
└─ Input handler → backend
```

### 17.2 Backend Services

```
┌─────────────────────────────────────────────────────────────┐
│                    ANIMA Backend Cluster                     │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Gateway   │  │   Session   │  │   Scene     │         │
│  │   (FastAPI) │  │   Manager   │  │   Cache     │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│         │                │                │                 │
│         └────────────────┼────────────────┘                 │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Session Worker (per user)               │   │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐   │   │
│  │  │  Hume   │ │ Physics │ │ Avatar  │ │ Vector  │   │   │
│  │  │ Client  │ │ Engine  │ │ Engine  │ │ Compose │   │   │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────┘   │   │
│  └─────────────────────────────────────────────────────┘   │
│                          │                                  │
│         ┌────────────────┼────────────────┐                │
│         ▼                ▼                ▼                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  GPU Pool   │  │   Redis     │  │  Hume EVI   │        │
│  │ (Avatar AI) │  │  (State)    │  │ (External)  │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 17.3 Resource Requirements (Updated)

| Component | CPU | GPU | RAM | Per Session |
|-----------|-----|-----|-----|-------------|
| Physics Engine | 1 core | — | 100 MB | Dedicated |
| Scene Generator | 0.5 core | 0.2 A100 | 500 MB | On-demand |
| Avatar Engine | 0.5 core | 0.3 A100 | 1 GB | Dedicated |
| Vector Compositor | 0.5 core | — | 200 MB | Dedicated |
| **Total per session** | **2.5 cores** | **0.5 A100** | **1.8 GB** | |

**Scaling:**
- 1x A100 (80GB) = ~10 concurrent sessions with GenAI face
- 1x A100 + 32-core CPU = 10 full world simulations
- Cost: ~$6000/month for 10 concurrent users

---

## 18. Updated Roadmap (24 Weeks)

### Phase 1: Foundation (Weeks 1–4)
| Week | Deliverable |
|------|-------------|
| 1 | Hume EVI integration |
| 2 | ANIMA SDK skeleton + Canvas2D vector renderer |
| 3 | Basic physics engine (rigid bodies only) |
| 4 | **Milestone:** Avatar in physics world, voice working |

### Phase 2: Physics & Vectors (Weeks 5–8)
| Week | Deliverable |
|------|-------------|
| 5 | Particle systems |
| 6 | Soft body basics (cloth, rope) |
| 7 | Delta encoding + streaming protocol |
| 8 | **Milestone:** Full physics demo, 30 FPS streaming |

### Phase 3: GenAI Face (Weeks 9–12)
| Week | Deliverable |
|------|-------------|
| 9–10 | Face autoencoder training |
| 11–12 | Flow model training + integration |
| 12 | **Milestone:** Neural face in physics world |

### Phase 4: Scene Generation (Weeks 13–16)
| Week | Deliverable |
|------|-------------|
| 13 | Procedural scene templates (3 types) |
| 14 | Scene ↔ physics integration |
| 15 | Neural scene generator (experimental) |
| 16 | **Milestone:** Generated worlds with avatar |

### Phase 5: Polish & Scale (Weeks 17–20)
| Week | Deliverable |
|------|-------------|
| 17 | Voice cloning pipeline (RVC) |
| 18 | WebGL vector renderer (performance) |
| 19 | Multi-user shared worlds (experimental) |
| 20 | **Milestone:** Production-ready system |

### Phase 6: Release (Weeks 21–24)
| Week | Deliverable |
|------|-------------|
| 21 | SDK documentation + examples |
| 22 | Public API + developer portal |
| 23 | Performance optimization |
| 24 | **Launch** |

---

## 20. Final Success Criteria

### MVP (Week 4)
- [ ] Avatar speaks with own TTS
- [ ] Lip sync working (<50ms error)
- [ ] Emotion affects animation
- [ ] 30 FPS JSON streaming

### Neural Integration (Week 8)
- [ ] Flow Matching model trained
- [ ] Quality exceeds rule-based baseline
- [ ] <40ms end-to-end latency

### Physics & Effects (Week 12)
- [ ] Particles, soft bodies working
- [ ] Delta encoding <1 KB/frame
- [ ] Client rendering stable

### Full System (Week 20)
- [ ] 3+ procedural scene types
- [ ] 400 concurrent users per A100
- [ ] Cost <$0.003/min
- [ ] Voice cloning operational

### Launch (Week 24)
- [ ] Public SDK release
- [ ] Developer documentation
- [ ] <$3/user/month cost

---

**Document Version:** 3.0 (Flow Matching + Own Audio Stack)  
**Status:** Ready for Implementation  
**Next Step:** Phase 1 kickoff — Hume + SDK + Physics foundation
