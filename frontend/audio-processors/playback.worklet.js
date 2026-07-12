/**
 * Audio Playback Worklet Processor for playing PCM audio
 * Adds queue stats so main thread can estimate playback delay.
 */

class PCMProcessor extends AudioWorkletProcessor {
  constructor() {
    super();

    this.audioQueue = [];
    this.queuedSamples = 0;

    // report throttling (seconds in audio clock)
    this._lastReportT = 0;
    this._reportIntervalS = 0.25;

    this.port.onmessage = (event) => {
      if (event.data === "interrupt") {
        this.audioQueue = [];
        this.queuedSamples = 0;
        return;
      }

      if (event.data instanceof Float32Array) {
        this.audioQueue.push(event.data);
        this.queuedSamples += event.data.length;
      }
    };
  }

  process(inputs, outputs /*, parameters */) {
    const output = outputs[0];
    if (!output || output.length === 0) return true;

    const channel = output[0];
    let outputIndex = 0;

    // Fill the output buffer from the queue
    while (outputIndex < channel.length && this.audioQueue.length > 0) {
      const currentBuffer = this.audioQueue[0];

      if (!currentBuffer || currentBuffer.length === 0) {
        this.audioQueue.shift();
        continue;
      }

      const remainingOutput = channel.length - outputIndex;
      const remainingBuffer = currentBuffer.length;
      const copyLength = Math.min(remainingOutput, remainingBuffer);

      for (let i = 0; i < copyLength; i++) {
        channel[outputIndex++] = currentBuffer[i];
      }

      // Update queued sample count (we just consumed copyLength samples)
      this.queuedSamples -= copyLength;
      if (this.queuedSamples < 0) this.queuedSamples = 0;

      if (copyLength < remainingBuffer) {
        this.audioQueue[0] = currentBuffer.slice(copyLength);
      } else {
        this.audioQueue.shift();
      }
    }

    // Fill remaining output with silence
    while (outputIndex < channel.length) {
      channel[outputIndex++] = 0;
    }

    // Periodically report queue seconds to main thread
    // AudioWorklet global: currentTime (s), sampleRate (Hz)
    if ((currentTime - this._lastReportT) >= this._reportIntervalS) {
      this._lastReportT = currentTime;

      const queuedSeconds = this.queuedSamples / sampleRate;
      this.port.postMessage({
        type: "stats",
        queuedSamples: this.queuedSamples,
        queuedSeconds,
      });
    }

    return true;
  }
}

registerProcessor("pcm-processor", PCMProcessor);
