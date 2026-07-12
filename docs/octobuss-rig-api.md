# Octobuss SVG Rig — API поз и липсинка

Рантайм-риг персонажа: `frontend/octobuss_avatar.js` + арт `frontend/octobuss.rigged.svg`
(генерируется `generate_octobuss_rig.py`). Тест-страница: `frontend/test_octobuss.html`.

Щупальца — FK-цепочки костей: базовый хребет лежит в `data-spine` каждой группы
`g.tentacle`, «кожа» (контур, тень, присоски, пятна, манжеты) пересобирается каждый
кадр вокруг текущего хребта. Число точек пути постоянно (правило 7 из
CHARACTER_RIG_RULES.md), деформация отделена от декора (правило 6).

## Подключение

В `index.html` аватар доступен третьей кнопкой «🦑 SVG Rig» и через общий прокси
`window.octopusAnimator` — реализует тот же интерфейс, что `OctopusAnimator`:
`handleCommand / setEmotion / blink / activateAction / triggerGesture / triggerFxFromAction`.

```js
const avatar = new OctobussAvatar('octobuss-box', 'octobuss.rigged.svg');
```

## Щупальца (7 групп)

| id | описание |
|---|---|
| `tentacle_up_l` / `tentacle_up_r` | поднятые руки (правая — с манжетой) |
| `tentacle_band_l` | левое длинное с манжетой и завитком |
| `tentacle_far_r` | правое длинное |
| `tentacle_front_l` / `tentacle_front_c` / `tentacle_front_r` | передний веер |

### Параметры изгиба (на щупальце)

| параметр | диапазон | значение |
|---|---|---|
| `rot` | рад | поворот у корня (экранный CW положительный) |
| `curl` | ~-1.5..2.5 | до-сгиб вдоль цепочки; >0 — закрутить глубже «естественного» завитка, <0 — раскрутить |
| `straighten` | 0..1 | разгибание: 1 = прямая линия от корня |
| `stretch` | 0.8..1.2 | удлинение сегментов |
| `swingAmp`,`swingSpeed`,`swingPhase` | рад / рад/с | циклический мах (wave, clap) |
| `waveMul` | 0..3 | амплитуда идл-волны (0 = замереть) |

```js
avatar.setTentacle('tentacle_up_r', {curl: 2.0}, 800);            // согнуть
avatar.setTentacle('tentacle_up_r', {straighten: 1, rot: -0.5});  // разогнуть вверх
avatar.setPose({ tentacle_up_r: {rot:-0.6, curl:1.2}, tentacle_up_l: {rot:0.3} });
```

### Позы-пресеты (`avatar.setPose(name, {durationMs, holdMs})`)

`rest, wave_right, wave_left, point_right, reach_up, sing, curl_shy, droop_sad,
excited, hug_front, think, shrug, clap` — список: `avatar.listPoses()` /
`window.OCTOBUSS_POSES`. Все позы задействуют и нижний веер щупалец.

Ограничитель видимости: перед применением любая поза просчитывается — если
кончик уходит за стекло шлема, за тело-перепонку (для заднего слоя) или за
край холста, отклонение автоматически ужимается до видимой зоны.

Брови (`brow_l`/`brow_r`, скрыты по умолчанию) управляются эмоциями:
angry/sad/surprised/confused/curious/sarcastic/empathetic/nervous/excited.

## Команды от ИИ (3 канала)

1. **Действия timeline-sync** (существующий пайплайн `type:"action"` →
   `render_packet` → `handleCommand({cmd:"action", action, duration_ms})`).
   Прежний словарь работает: `wave→wave_right, point→point_right, hug→hug_front,
   shrug, clap, sing, laugh, whisper, shout, photobooth…` Имя любой позы-пресета
   тоже валидно как action.

2. **Прямая команда позы** (новый cmd, можно слать тем же каналом):
   ```json
   {"cmd":"pose", "pose":"curl_shy", "duration_ms":600, "hold_ms":3000}
   {"cmd":"pose", "pose":{"tentacle_up_r":{"curl":2.2,"rot":-0.4}}, "duration_ms":800}
   ```

3. **Tool calling** (Gemini function call, стиль `tools.js`):
   ```js
   class SetOctopusPoseTool extends FunctionCallDefinition {
     constructor() {
       super("set_octopus_pose",
         "Set octopus body pose. Presets: rest, wave_right, wave_left, point_right, reach_up, curl_shy, droop_sad, excited, hug_front, think, shrug, clap",
         { type: "object", properties: {
             pose: { type: "string", description: "preset name" },
             hold_ms: { type: "number", description: "how long to hold before returning to emotion posture" }
         } }, ["pose"]);
     }
     functionToCall(p) {
       window.octopusAnimator?._active?.setPose?.(p.pose, { durationMs: 600, holdMs: p.hold_ms || 3000 });
     }
   }
   ```

Эмоции (`setEmotion`) задают фоновую осанку + лицо: `sad→droop_sad`,
`excited→excited`, `nervous→curl_shy`, `playful→wave_right` и т.д. — активное
действие/поза временно перекрывает осанку и возвращается по истечении.

## Липсинк

Совместим с пакетами `timeline_sync.py` (см. timeline-sync.md):

```json
{"cmd":"audio_sync", "start_s":0.0, "duration_s":3.2, "speaking":true,
 "jaw":          {"step_ms":20, "values":[0.0, 0.4, 0.9, ...]},
 "viseme_proxy": {"step_ms":50, "values":["A","E","REST", ...]},
 "emotion": {"value":"happy"}, "action":"none"}
```

- `jaw.values` — амплитуда 0..1 (открытие), шаг `step_ms`; выравнивание по
  `window.getAudioPlayheadS()` и догон при опоздании — как в legacy-аниматоре.
- `viseme_proxy.values` — буквы `REST|A|E|I|O|U` (числа 0..1 тоже принимаются и
  квантуются в буквы). Форма рта = визема × jaw: параметрический морф пути
  (ширина/округлость/глубина), язык и блик следуют за открытием.
- Также поддержаны `{cmd:"sync", visemes:[...], duration}`,
  `{cmd:"mouth", value:0..1, speaking}`, `{cmd:"end"}`.

## Прочее

- `avatar.blink()` — моргнуть; авто-моргание ~раз в 4 с.
- `avatar.setGaze(x, y)` — взгляд, нормализованные −1..1 (канал `gaze` timeline-sync).
- Пересборка арта: `python3 generate_octobuss_rig.py && cp octobuss.rigged.svg frontend/`.
