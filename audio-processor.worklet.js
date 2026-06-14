/**
 * VoiceBridge AI - AudioWorklet Processor
 * Runs in a dedicated audio thread (not the main JS thread).
 *
 * Responsibilities:
 *  - Receive raw PCM float32 samples from the Web Audio graph
 *  - Accumulate samples into fixed-size frames
 *  - Compute RMS for Voice Activity Detection
 *  - Post frames to the main thread for base64 encoding + Socket.IO send
 *
 * Loaded via: audioContext.audioWorklet.addModule('/audio-processor.worklet.js')
 */

const FRAME_SIZE   = 4096   // samples per frame (~256ms at 16kHz)
const SAMPLE_RATE  = 16000
const VAD_THRESHOLD = 0.008  // RMS threshold for speech detection

class AudioProcessor extends AudioWorkletProcessor {
  constructor() {
    super()
    this._buffer    = new Float32Array(FRAME_SIZE)
    this._writePos  = 0
    this._frameNum  = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (!input || !input[0]) return true

    const samples = input[0]  // mono channel

    for (let i = 0; i < samples.length; i++) {
      this._buffer[this._writePos++] = samples[i]

      if (this._writePos >= FRAME_SIZE) {
        // Compute RMS for VAD
        let sumSq = 0
        for (let j = 0; j < FRAME_SIZE; j++) {
          sumSq += this._buffer[j] * this._buffer[j]
        }
        const rms = Math.sqrt(sumSq / FRAME_SIZE)
        const isSpeaking = rms > VAD_THRESHOLD

        // Convert Float32 → Int16 for compact transmission
        const int16 = new Int16Array(FRAME_SIZE)
        for (let j = 0; j < FRAME_SIZE; j++) {
          int16[j] = Math.max(-32768, Math.min(32767, this._buffer[j] * 32768))
        }

        // Post to main thread
        this.port.postMessage(
          {
            type:       'audio_frame',
            int16:      int16.buffer,
            rms,
            isSpeaking,
            frameNum:   this._frameNum++,
          },
          [int16.buffer]  // transfer ownership (zero-copy)
        )

        this._buffer    = new Float32Array(FRAME_SIZE)
        this._writePos  = 0
      }
    }

    return true  // keep processor alive
  }
}

registerProcessor('audio-processor', AudioProcessor)
