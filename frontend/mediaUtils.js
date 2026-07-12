/**
 * Media Utilities - Audio and Video streaming helpers for Gemini Live API
 * Handles media capture, processing, and playback
 * Includes Face ID detection and processing
 */

/**
 * Face ID Detector - Detects and identifies faces from video frames
 */
class FaceIDDetector {
  constructor() {
    this.isProcessing = false;
    this.lastDetectionTime = 0;
    this.detectionThrottle = 1000; // Process max 1 time per second
    this.onFaceDetected = null; // Callback for detection results
    this.faceDetectionModel = null; // MediaPipe FaceMesh model
    this.lastResults = null; // Store latest detection results
    this.isInitialized = false;
  }

  /**
   * Initialize Face Detection model (TFLite + MediaPipe)
   */
  async init() {
    if (this.isInitialized) return;

    try {
      // Check if MediaPipe Face Detection is loaded
      if (typeof FaceMesh !== 'undefined') {
        this.faceDetectionModel = new FaceMesh({
          locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/face_mesh/${file}`
        });

        // Configure FaceMesh
        await this.faceDetectionModel.setOptions({
          maxNumFaces: 1,
          refineLandmarks: false,
          minDetectionConfidence: 0.5,
          minTrackingConfidence: 0.5
        });

        // Set up result callback
        this.faceDetectionModel.onResults((results) => {
          // Store results for async processing
          this.lastResults = results;
        });

        await this.faceDetectionModel.initialize();

        this.isInitialized = true;
        console.log("✅ Face ID Detector initialized (MediaPipe)");
      } else {
        console.warn("⚠️ MediaPipe Face Mesh not loaded, Face ID detection disabled");
      }
    } catch (error) {
      console.error("❌ Failed to initialize Face ID Detector:", error);
    }
  }

  /**
   * Process frame for face detection
   * @param {string} base64Image - Base64 encoded image
   * @param {number} width - Image width
   * @param {number} height - Image height
   * @returns {Promise<Object>} Detection result {faces: [...], timestamp}
   */
  async processFrame(base64Image, width, height) {
    // Throttle detection
    const now = Date.now();
    if (now - this.lastDetectionTime < this.detectionThrottle) {
      return null;
    }
    this.lastDetectionTime = now;

    if (!this.isInitialized || !this.faceDetectionModel) {
      return null;
    }

    try {
      // Convert base64 to image element
      const img = await this._base64ToImage(base64Image);

      // Send image to MediaPipe
      await this.faceDetectionModel.send({ image: img });

      // Wait a bit for results callback
      await new Promise(resolve => setTimeout(resolve, 50));

      // Check stored results
      if (!this.lastResults || !this.lastResults.multiFaceLandmarks || this.lastResults.multiFaceLandmarks.length === 0) {
        return { faces: [], timestamp: now };
      }

      // Extract face data from stored results
      const faces = this.lastResults.multiFaceLandmarks.map((landmarks, idx) => ({
        id: idx,
        landmarks: landmarks,
        confidence: 0.95, // MediaPipe doesn't give confidence, use high default
        detected: true
      }));

      return { faces, timestamp: now };

    } catch (error) {
      console.error("❌ Face detection error:", error);
      return null;
    }
  }

  /**
   * Convert base64 image to Image element for MediaPipe
   */
  async _base64ToImage(base64) {
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => resolve(img);
      img.onerror = reject;
      img.src = 'data:image/jpeg;base64,' + base64;
    });
  }
}

/**
 * Audio Streamer - Captures and streams microphone audio
 */
class AudioStreamer {
  constructor(geminiClient) {
    this.client = geminiClient;
    this.audioContext = null;
    this.audioWorklet = null;
    this.mediaStream = null;
    this.isStreaming = false;
    this.sampleRate = 16000; // Target 16kHz for Gemini
    this.inputSampleRate = 16000;
    this._lastDebugTs = 0;
  }

  /**
   * Start streaming audio from microphone
   * @param {string} deviceId - Optional device ID for specific microphone
   */
  async start(deviceId = null) {
    try {
      // Build audio constraints
      const audioConstraints = {
        sampleRate: { ideal: this.sampleRate },
        channelCount: { ideal: 1 },
        echoCancellation: true,
        noiseSuppression: true,
        autoGainControl: true,
      };

      // Add device ID if specified
      if (deviceId) {
        audioConstraints.deviceId = { exact: deviceId };
      }

      // Get microphone access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        audio: audioConstraints,
      });

      // Create audio context targeting 16kHz (browser may still choose another rate)
      this.audioContext = new (window.AudioContext ||
        window.webkitAudioContext)({ sampleRate: this.sampleRate });
      this.inputSampleRate = this.audioContext.sampleRate;
      const trackRate = this.mediaStream.getAudioTracks()[0]?.getSettings?.()
        ?.sampleRate;
      console.log("🎤 capture sampleRate", this.inputSampleRate, "trackRate", trackRate);

      // Load the audio worklet module
      await this.audioContext.audioWorklet.addModule(
        "audio-processors/capture.worklet.js"
      );

      // Create the audio worklet node
      this.audioWorklet = new AudioWorkletNode(
        this.audioContext,
        "audio-capture-processor"
      );

      // Ensure the graph is connected so the worklet actually runs.
      const sink = this.audioContext.createGain();
      sink.gain.value = 0.0;

      // Set up message handling from the worklet
      this.audioWorklet.port.onmessage = (event) => {
        if (!this.isStreaming) return;

        if (event.data.type === "diag") {
          console.log(`🎤 worklet diag #${event.data.diagCount}: hasInput=${event.data.hasInput} maxAmp=${event.data.maxAmp.toFixed(6)}`);
          return;
        }

        if (event.data.type === "audio") {
          const inputData = event.data.data;
          const now = Date.now();
          if (now - this._lastDebugTs > 1000) {
            this._lastDebugTs = now;
            console.log("🎤 audio chunk", inputData.length);
          }
          const resampled = this.resampleTo16k(inputData, this.inputSampleRate);
          const pcmData = this.convertToPCM16(resampled);
          const base64Audio = this.arrayBufferToBase64(pcmData);

          // Send to Gemini
          if (this.client && this.client.connected) {
            this.client.sendAudioMessage(base64Audio, 16000);
          }
        }
      };

      // Connect the audio graph
      const source = this.audioContext.createMediaStreamSource(
        this.mediaStream
      );
      source.connect(this.audioWorklet);
      this.audioWorklet.connect(sink);
      sink.connect(this.audioContext.destination);

      // Always resume — AudioContext may be suspended even if state reports "running"
      await this.audioContext.resume();
      console.log(`🎤 AudioContext state=${this.audioContext.state} sampleRate=${this.audioContext.sampleRate}`);

      const tracks = this.mediaStream.getAudioTracks();
      console.log(`🎤 mic tracks: ${tracks.length}`, tracks.map(t => `${t.label} enabled=${t.enabled} muted=${t.muted}`));

      this.isStreaming = true;
      console.log("🎤 Audio streaming started");
      return true;
    } catch (error) {
      console.error("Failed to start audio streaming:", error);
      throw error;
    }
  }

  /**
   * Stop audio streaming
   */
  stop() {
    this.isStreaming = false;

    if (this.audioWorklet) {
      this.audioWorklet.disconnect();
      this.audioWorklet.port.close();
      this.audioWorklet = null;
    }

    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    console.log("🛑 Audio streaming stopped");
  }

  /**
   * Convert Float32Array to PCM16 Int16Array
   */
  convertToPCM16(float32Array) {
    const int16Array = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      const sample = Math.max(-1, Math.min(1, float32Array[i]));
      int16Array[i] = sample * 0x7fff;
    }
    return int16Array.buffer;
  }

  /**
   * Simple linear resampler to 16kHz
   */
  resampleTo16k(float32Array, fromRate) {
    if (!float32Array || float32Array.length === 0) return float32Array;
    if (!fromRate || fromRate === 16000) return float32Array;
    const ratio = 16000 / fromRate;
    const newLength = Math.max(1, Math.round(float32Array.length * ratio));
    const out = new Float32Array(newLength);
    const invRatio = fromRate / 16000;
    for (let i = 0; i < newLength; i++) {
      const pos = i * invRatio;
      const idx = Math.floor(pos);
      const frac = pos - idx;
      const a = float32Array[idx] || 0;
      const b = float32Array[idx + 1] || a;
      out[i] = a + (b - a) * frac;
    }
    return out;
  }

  /**
   * Convert ArrayBuffer to base64
   */
  arrayBufferToBase64(buffer) {
    const bytes = new Uint8Array(buffer);
    let binary = "";
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return window.btoa(binary);
  }
}

/**
 * Base Video Capture - Shared functionality for video/screen capture
 */
class BaseVideoCapture {
  constructor(geminiClient) {
    this.client = geminiClient;
    this.video = null;
    this.canvas = null;
    this.ctx = null;
    this.mediaStream = null;
    this.isStreaming = false;
    this.captureInterval = null;
    this.fps = 20; // Default 20 frames per second
    this.quality = 0.8; // Default JPEG quality
    this.onFrame = null;
  }

  /**
   * Initialize canvas and video elements
   */
  initializeElements(width, height) {
    // Create video element
    this.video = document.createElement("video");
    this.video.srcObject = this.mediaStream;
    this.video.autoplay = true;
    this.video.playsInline = true;
    this.video.muted = true;

    // Create canvas for frame capture
    this.canvas = document.createElement("canvas");
    this.canvas.width = width;
    this.canvas.height = height;
    this.ctx = this.canvas.getContext("2d");
  }

  /**
   * Wait for video to be ready and start playing
   */
  async waitForVideoReady() {
    await new Promise((resolve) => {
      this.video.onloadedmetadata = resolve;
    });
    this.video.play();
  }

  /**
   * Start capturing and sending frames
   */
  startCapturing() {
    const captureFrame = () => {
      if (!this.isStreaming) return;

      // Draw current frame to canvas
      this.ctx.drawImage(
        this.video,
        0,
        0,
        this.canvas.width,
        this.canvas.height
      );

      // Convert to JPEG and send
      this.canvas.toBlob(
        (blob) => {
          if (!blob) return;

          const reader = new FileReader();
          reader.onloadend = () => {
            const base64 = reader.result.split(",")[1];
            if (typeof this.onFrame === "function") {
              try {
                this.onFrame(base64, "image/jpeg", this.canvas.width, this.canvas.height);
              } catch (_) { }
            }
            if (this.client && this.client.connected) {
              this.client.sendImageMessage(base64, "image/jpeg");
            }
          };
          reader.readAsDataURL(blob);
        },
        "image/jpeg",
        this.quality
      );
    };

    // Start interval
    this.captureInterval = setInterval(captureFrame, 1000 / this.fps);
  }

  /**
   * Stop capturing
   */
  stop() {
    this.isStreaming = false;

    if (this.captureInterval) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.video) {
      this.video.srcObject = null;
      this.video = null;
    }

    this.canvas = null;
    this.ctx = null;
  }

  /**
   * Take a single snapshot
   */
  takeSnapshot() {
    if (!this.video || !this.canvas) {
      throw new Error("Video not initialized");
    }

    this.ctx.drawImage(
      this.video,
      0,
      0,
      this.canvas.width,
      this.canvas.height
    );
    return this.canvas.toDataURL("image/jpeg", this.quality);
  }

  /**
   * Get the video element for preview
   */
  getVideoElement() {
    return this.video;
  }
}

/**
 * Video Streamer - Captures and streams camera video
 */
class VideoStreamer extends BaseVideoCapture {
  /**
   * Start video streaming from camera
   * @param {Object} options - { fps: number, width: number, height: number, facingMode: string, quality: number, deviceId: string }
   */
  async start(options = {}) {
    try {
      const {
        fps = 1,
        width = 640,
        height = 480,
        facingMode = "user", // 'user' for front camera, 'environment' for back
        quality = 0.8,
        deviceId = null,
      } = options;

      this.fps = fps;
      this.quality = quality;

      // Build video constraints
      const videoConstraints = {
        width: { ideal: width },
        height: { ideal: height },
      };

      // Add device ID if specified, otherwise use facingMode
      if (deviceId) {
        videoConstraints.deviceId = { exact: deviceId };
      } else {
        videoConstraints.facingMode = facingMode;
      }

      // Get camera access
      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints,
      });

      // Initialize video and canvas elements
      this.initializeElements(width, height);

      // Wait for video to be ready
      await this.waitForVideoReady();

      // Start capturing frames
      this.isStreaming = true;
      this.startCapturing();

      console.log("📹 Camera streaming started at", fps, "fps");
      return this.video; // Return video element for preview
    } catch (error) {
      console.error("Failed to start camera streaming:", error);
      throw error;
    }
  }

  stop() {
    super.stop();
    console.log("🛑 Camera streaming stopped");
  }
}

/**
 * Split Video Streamer - One camera, two output sizes/fps (Gemini + Gaze)
 * Includes Face ID detection before sending to Gemini
 */
class SplitVideoStreamer {
  constructor(geminiClient) {
    this.client = geminiClient;
    this.mediaStream = null;
    this.video = null;
    this.isStreaming = false;
    this.gemini = { fps: 1, width: 640, height: 480, quality: 0.8 };
    this.gaze = { fps: 6, width: 320, height: 240, quality: 0.6 };
    this.geminiCanvas = null;
    this.geminiCtx = null;
    this.gazeCanvas = null;
    this.gazeCtx = null;
    this.geminiInterval = null;
    this.gazeInterval = null;
    this.gazeOnFrame = null;

    // Face ID Detection
    this.faceIDDetector = new FaceIDDetector();
    this.onFaceIDResult = null; // Callback for Face ID results
    this.faceIDEnabled = true;
  }

  async start(options = {}) {
    try {
      const {
        gemini = {},
        gaze = {},
        facingMode = "user",
        deviceId = null,
      } = options;

      this.gemini = { ...this.gemini, ...gemini };
      this.gaze = { ...this.gaze, ...gaze };

      const width = Math.max(this.gemini.width, this.gaze.width);
      const height = Math.max(this.gemini.height, this.gaze.height);
      const videoConstraints = {
        width: { ideal: width },
        height: { ideal: height },
      };
      if (deviceId) {
        videoConstraints.deviceId = { exact: deviceId };
      } else {
        videoConstraints.facingMode = facingMode;
      }

      this.mediaStream = await navigator.mediaDevices.getUserMedia({
        video: videoConstraints,
      });

      this.video = document.createElement("video");
      this.video.srcObject = this.mediaStream;
      this.video.autoplay = true;
      this.video.playsInline = true;
      this.video.muted = true;

      this.geminiCanvas = document.createElement("canvas");
      this.geminiCanvas.width = this.gemini.width;
      this.geminiCanvas.height = this.gemini.height;
      this.geminiCtx = this.geminiCanvas.getContext("2d");

      this.gazeCanvas = document.createElement("canvas");
      this.gazeCanvas.width = this.gaze.width;
      this.gazeCanvas.height = this.gaze.height;
      this.gazeCtx = this.gazeCanvas.getContext("2d");

      await new Promise((resolve) => {
        this.video.onloadedmetadata = resolve;
      });
      this.video.play();

      // Initialize Face ID detection
      if (this.faceIDEnabled) {
        await this.faceIDDetector.init();
      }

      this.isStreaming = true;
      this.startLoop("gemini");
      this.startLoop("gaze");
      console.log(
        "📹 Camera streaming started gemini",
        this.gemini.fps,
        "fps",
        "gaze",
        this.gaze.fps,
        "fps"
      );
      return this.video;
    } catch (error) {
      console.error("Failed to start camera streaming:", error);
      throw error;
    }
  }

  startLoop(kind) {
    const cfg = kind === "gemini" ? this.gemini : this.gaze;
    const canvas = kind === "gemini" ? this.geminiCanvas : this.gazeCanvas;
    const ctx = kind === "gemini" ? this.geminiCtx : this.gazeCtx;
    const fps = Math.max(1, cfg.fps || 1);
    const tick = () => {
      if (!this.isStreaming || !this.video) return;
      ctx.drawImage(this.video, 0, 0, canvas.width, canvas.height);
      canvas.toBlob(
        (blob) => {
          if (!blob) return;
          const reader = new FileReader();
          reader.onloadend = async () => {
            const base64 = reader.result.split(",")[1];

            // GEMINI STREAM: Обработать Face ID перед отправкой
            if (kind === "gemini" && this.faceIDEnabled) {
              try {
                // Запустить Face ID обработку асинхронно
                this._processFaceID(base64, canvas.width, canvas.height);
              } catch (error) {
                console.error("Face ID processing error:", error);
              }
            }

            // Отправить в зависимости от типа потока
            if (kind === "gaze") {
              if (typeof this.gazeOnFrame === "function") {
                this.gazeOnFrame(base64, "image/jpeg", canvas.width, canvas.height);
              }
              return;
            }

            // Отправить в Gemini (кадр пойдет дальше после Face ID обработки)
            if (this.client && this.client.connected) {
              this.client.sendImageMessage(base64, "image/jpeg");
            }
          };
          reader.readAsDataURL(blob);
        },
        "image/jpeg",
        cfg.quality
      );
    };

    const interval = setInterval(tick, 1000 / fps);
    if (kind === "gemini") {
      this.geminiInterval = interval;
    } else {
      this.gazeInterval = interval;
    }
  }

  /**
   * Process frame for Face ID detection (async, non-blocking)
   */
  async _processFaceID(base64Image, width, height) {
    try {
      const result = await this.faceIDDetector.processFrame(base64Image, width, height);

      if (!result || !result.faces || result.faces.length === 0) {
        if (typeof this.onFaceIDResult === "function") {
          this.onFaceIDResult({ type: "no_face", timestamp: result?.timestamp || Date.now() });
        }
        return;
      }

      // Один запрос на бэкенд со всем кадром — бэкенд сам найдёт все лица
      this._identifyFace(base64Image);

    } catch (error) {
      console.error("❌ Face ID processing error:", error);
    }
  }

  /**
   * Identify all faces in frame by sending to backend API
   */
  async _identifyFace(base64Image) {
    try {
      const response = await fetch("/api/face/identify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image_b64: base64Image, threshold: 0.6 })
      });

      if (!response.ok) {
        console.error("Face identification failed:", response.status);
        return;
      }

      const result = await response.json();

      if (typeof this.onFaceIDResult === "function") {
        const users = result.users || [];
        if (users.length > 0) {
          this.onFaceIDResult({
            type: "face_identified",
            users: users,
            timestamp: result.timestamp
          });
          console.log(`✅ Identified ${users.length} user(s):`, users.map(u => u.user_name).join(", "));
        } else if (result.status === "face_unknown") {
          this.onFaceIDResult({
            type: "face_unknown",
            message: result.message,
            timestamp: result.timestamp
          });
        } else {
          this.onFaceIDResult({ type: "no_face", timestamp: result.timestamp });
        }
      }

    } catch (error) {
      console.error("❌ Face identification error:", error);
    }
  }

  /**
   * Сделать снимок для photobooth
   */
  takeSnapshot(quality = 0.9) {
    if (!this.video || !this.geminiCanvas) {
      throw new Error("Video not initialized");
    }

    // Используем основной холст Gemini для снимка
    this.geminiCtx.drawImage(
      this.video,
      0,
      0,
      this.geminiCanvas.width,
      this.geminiCanvas.height
    );
    return this.geminiCanvas.toDataURL("image/jpeg", quality);
  }

  stop() {
    this.isStreaming = false;

    if (this.geminiInterval) {
      clearInterval(this.geminiInterval);
      this.geminiInterval = null;
    }
    if (this.gazeInterval) {
      clearInterval(this.gazeInterval);
      this.gazeInterval = null;
    }

    if (this.mediaStream) {
      this.mediaStream.getTracks().forEach((track) => track.stop());
      this.mediaStream = null;
    }

    if (this.video) {
      this.video.srcObject = null;
      this.video = null;
    }

    this.geminiCanvas = null;
    this.geminiCtx = null;
    this.gazeCanvas = null;
    this.gazeCtx = null;
  }
}

/**
 * Screen Capture - Captures and streams screen/window
 */
class ScreenCapture extends BaseVideoCapture {
  /**
   * Start screen capture
   * @param {Object} options - { fps: number, width: number, height: number, quality: number }
   */
  async start(options = {}) {
    try {
      const {
        fps = 1,
        width = 1280,
        height = 720,
        quality = 0.7
      } = options;

      this.fps = fps;
      this.quality = quality;

      // Get screen capture permission
      this.mediaStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          width: { ideal: width },
          height: { ideal: height },
        },
        audio: false,
      });

      // Initialize video and canvas elements
      this.initializeElements(width, height);

      // Wait for video to be ready
      await this.waitForVideoReady();

      // Start capturing frames
      this.isStreaming = true;
      this.startCapturing();

      // Handle stream end (user stops sharing)
      this.mediaStream.getVideoTracks()[0].onended = () => {
        console.log("User stopped screen sharing");
        this.stop();
      };

      console.log("🖥️ Screen capture started at", fps, "fps");
      return this.video; // Return video element for preview
    } catch (error) {
      console.error("Failed to start screen capture:", error);
      throw error;
    }
  }

  stop() {
    super.stop();
    console.log("🛑 Screen capture stopped");
  }
}

/**
 * Audio Player - Plays audio responses from Gemini
 */
class AudioPlayer {
  constructor() {
    this.audioContext = null;
    this.workletNode = null;
    this.gainNode = null;
    this.isInitialized = false;
    this.volume = 1.0;
    this.sampleRate = 24000; // Gemini outputs at 24kHz

    this.queuedSamples = 0;
    this.lastQueueSr = this.sampleRate;
    this.queuedSeconds = 0;
    this.totalSentSamples = 0;
  }

  /**
   * Initialize the audio player
   */
  async init() {
    if (this.isInitialized) return;

    try {
      // Create audio context at 24kHz to match Gemini
      this.audioContext = new (window.AudioContext ||
        window.webkitAudioContext)({
          sampleRate: this.sampleRate,
        });

      // Load the audio worklet from external file
      await this.audioContext.audioWorklet.addModule(
        "audio-processors/playback.worklet.js"
      );

      // Create worklet node
      this.workletNode = new AudioWorkletNode(
        this.audioContext,
        "pcm-processor"
      );

      // Create gain node for volume control
      this.gainNode = this.audioContext.createGain();
      this.gainNode.gain.value = this.volume;

      // Connect nodes
      this.workletNode.connect(this.gainNode);
      this.gainNode.connect(this.audioContext.destination);



      this.workletNode.port.onmessage = (event) => {
        const d = event.data;
        if (d && d.type === "queue") {
          this.queuedSamples = d.queuedSamples || 0;
          this.lastQueueSr = d.sr || this.sampleRate;
        } else if (d && d.type === "stats") {
          this.queuedSamples = d.queuedSamples || 0;
          this.lastQueueSr = this.sampleRate;
          this.queuedSeconds = typeof d.queuedSeconds === "number" ? d.queuedSeconds : (this.queuedSamples / this.lastQueueSr);
        }
      };
      this.isInitialized = true;
      console.log("🔊 Audio player initialized");
    } catch (error) {
      console.error("Failed to initialize audio player:", error);
      throw error;
    }
  }

  /**
   * Play audio chunk from base64 PCM
   */
  async play(base64Audio) {
    if (!this.isInitialized) {
      await this.init();
    }

    try {
      // Resume audio context if suspended
      if (this.audioContext.state === "suspended") {
        await this.audioContext.resume();
      }

      // Convert base64 to Float32Array
      const binaryString = atob(base64Audio);
      const bytes = new Uint8Array(binaryString.length);
      for (let i = 0; i < binaryString.length; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      // Convert PCM16 LE to Float32
      const inputArray = new Int16Array(bytes.buffer);
      const float32Data = new Float32Array(inputArray.length);
      for (let i = 0; i < inputArray.length; i++) {
        float32Data[i] = inputArray[i] / 32768;
      }

      // Send to worklet for playback
      this.workletNode.port.postMessage(float32Data);
      this.totalSentSamples += float32Data.length;
    } catch (error) {
      console.error("Error playing audio chunk:", error);
      throw error;
    }
  }

  getPlayheadS() {
    // 🔥 Использовать audioContext.currentTime для точного timing
    // Это работает правильно при микрофонном вводе с маленькими chunks
    if (this.audioContext) {
      return this.audioContext.currentTime;
    }
    // Fallback если audioContext не готов
    const played = Math.max(0, this.totalSentSamples - this.queuedSamples);
    return played / this.sampleRate;
  }

  /**
   * Interrupt current playback
   */
  interrupt() {
    if (this.workletNode) {
      this.workletNode.port.postMessage("interrupt");
    }
  }

  /**
   * Set volume (0.0 to 1.0)
   */
  setVolume(volume) {
    this.volume = Math.max(0, Math.min(1, volume));
    if (this.gainNode) {
      this.gainNode.gain.value = this.volume;
    }
  }

  /**
   * Clean up resources
   */
  destroy() {
    if (this.audioContext) {
      this.audioContext.close();
      this.audioContext = null;
    }
    this.isInitialized = false;
  }
}
