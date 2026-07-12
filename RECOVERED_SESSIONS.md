# Recovered Session Data

**Дата восстановления**: 2026-05-22  
**Источник**: Логи субагентов из `.claude/projects/-Users-miguelaprossine-octopus-thorvg/`  
**Статус**: Основные файлы сессий удалены, восстановлены фрагменты из субагентов

---

## Сессия 1: Face Recognition & Lip-Sync Issues

**ID**: `71664836-05c0-4740-b615-c10f5522ebbe`  
**Дата**: 2026-01-20  
**Размер**: 1.9MB субагентов  
**Первое сообщение**: "теперь добавь туда проблемы как работает распознавание лиц и проблему почему не решается вопрос с липсинком при использовании микрофона"

### Что исследовалось:

#### Frontend Architecture
- **Octopus Avatar** — веб-приложение с SVG-аватаром осьминога
- **Canvas Animation**: `OctopusAnimator` класс в `index.html`
- **Gemini Live API**: модель `gemini-live-2.5-flash-native-audio`
- **WebSocket Connection**: протокол WS/WSS для общения с backend

#### Key Frontend Files
```
frontend/index.html — основное приложение (>1100 строк)
├── OctopusAnimator (canvas animation)
├── GeminiLiveAPI (WebSocket connection)
├── AudioStreamer (микрофон)
├── SplitVideoStreamer (камера + gaze)
└── State management (geminiClient, audioStreamer, videoStreamer, gazeSocket)
```

#### Lip-Sync Implementation
```javascript
// Line ~1004-1010: Avatar animation hook
if (a && window.octopusAnimator && typeof window.octopusAnimator.handleCommand === "function") {
    if (a.cmd === "start") {
        // align visemes with audio playback start (one-shot)
        if (state.audioT0 != null && a.t0 === undefined) {
            a.t0 = state.audioT0;
            state.audioT0 = null;
        }
        window.octopusAnimator.handleCommand(a);
    }
}

// Visemes: REST, A, E, I, O, U, E, A, REST
```

#### Audio Control
```javascript
// Line ~1043-1051: toggleAudio()
async function toggleAudio() {
    if (!state.audioStreamer) {
        state.audioStreamer = new AudioStreamer(state.geminiClient);
        await state.audioStreamer.start();
        state.micUserEnabled = true;
    }
}
```

#### Video Control
```javascript
// Line ~1069-1076: toggleVideo()
async function toggleVideo() {
    if (!state.videoStreamer) {
        state.videoStreamer = new SplitVideoStreamer(state.geminiClient);
        state.videoStreamer.gazeOnFrame = (b64, mime, w, h) => { ... }
    }
}
```

#### Gaze WebSocket
```javascript
// Line ~674-690: ensureGazeSocket()
function ensureGazeSocket() {
    if (state.gazeSocket && state.gazeSocket.readyState === WebSocket.OPEN) {
        return state.gazeSocket;
    }
    const url = getGazeWsUrl(); // wss://host/gaze-client
    state.gazeSocket = new WebSocket(url);
    state.gazeSocket.onopen = () => { ... }
}
```

#### Heartbeat & Playback Sync
```javascript
// Line ~1032-1039: Heartbeat with playback delay
state.geminiClient.sendMessage({
    client_event: {
        type: "heartbeat",
        playback_delay_s: playbackDelay
    }
});
// Интервал: 1500ms (увеличено с 250ms для снижения нагрузки)
```

#### Text Input
```javascript
// Line ~750-783: sendTextMessage()
function sendTextMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    // Отправляется через geminiClient.sendMessage()
}
// Также перехватывает Enter в chatInput
```

#### Emotions & Actions
```javascript
// Эмоции: calm, happy, excited, neutral
// Действия: с префиксом sfx_ или "wipe"
// Duration: 1400ms
window.octopusAnimator.handleCommand({
    cmd: "emotion" | "action",
    emotion: string,
    action: string,
    duration_ms: 1400
});
```

#### Sound Effects
```javascript
// Line ~551-630: playSfx(action)
- Кэширование аудио в sfxAudioCache
- Настройка volume: 0.35
- Распределение по времени (rate limiting)
- Поддержка специальных запросов типа "sing" (4-7s duration)
```

#### SVG Avatar Structure
- **Fill colors**: например `#B57AW` (фиолетовый)
- **Multiple path elements**: щупальца, голова и т.д.
- **Canvas rendering**: из SVG конвертируется в Canvas для анимации

---

## Сессия 2: Error Finding

**ID**: `a01e00ee-9aec-4e29-980a-3609a80a1b37`  
**Дата**: 2026-01-16  
**Размер**: 36KB субагентов + 117 сообщений  
**Первое сообщение**: "мне нужно найти ошибку в файлах. контекст в файле context2.txt"

**Статус**: Полный диалог удалён, остались только warmup-логи субагентов

---

## Сессия 3: Unknown

**ID**: `a858b9f6-141e-4309-8682-887ddc994606`  
**Размер**: 12KB субагентов  
**Статус**: Только warmup-логи, содержание неизвестно

---

## Key Insights from Code Review

### Potential Lip-Sync Issue (микрофон vs чат)

1. **audioT0 synchronization** (line 1005-1008):
   - При чат-вводе: `state.audioT0` устанавливается правильно перед первым viseme
   - При микрофонном вводе: возможна асинхронность в потоке аудиопотока

2. **Heartbeat timing** (1500ms интервал):
   - Может быть слишком редко для синхронизации реального времени
   - Playback delay рассчитывается из queue, но может быть недостаточно точно

3. **AudioStreamer vs AudioPlayer**:
   - Нужно проверить, как они взаимодействуют при микрофонном вводе
   - WebSocket frames vs audio chunks timing

4. **Buffer Management**:
   - queuedSeconds / queuedSamples используются для playback_delay
   - При микрофоне может быть другая стратегия queuing

---

## Files to Investigate

```
/Users/miguelaprossine/octopus-thorvg/
├── frontend/index.html (1100+ lines, main app)
├── scripts/ (AudioStreamer, SplitVideoStreamer, OctopusAnimator?)
├── backend/
│   ├── app.py
│   └── gaze_ws.py
├── svg/
│   └── octopus_animated.svg
└── context2.txt (упоминался в сессии a01e00ee)
```

---

## Questions to Resolve

1. **Lip-sync микрофон**: Почему `audioT0` может не синхронизироваться при микрофонном вводе?
2. **Face Recognition**: Как интегрирована (какая библиотека? MediaPipe?)
3. **Gaze Tracking**: Как работает `/gaze-client` WebSocket?
4. **Canvas Rendering**: Как SVG конвертируется в Canvas для анимации?

---

*Восстановлено из сохранённых логов субагентов. Полные диалоги сессий удалены.*
