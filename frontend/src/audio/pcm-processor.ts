/**
 * AudioWorklet processor for capturing raw PCM from the microphone.
 * Converts Float32 to Int16 and downsamples to 16kHz for Cartesia STT.
 */
/// <reference path="./audio-worklet.d.ts" />

const SAMPLE_RATE_OUT = 16000
const CHUNK_MS = 100
const SAMPLES_PER_CHUNK = (SAMPLE_RATE_OUT * CHUNK_MS) / 1000

class PcmProcessor extends AudioWorkletProcessor {
  private buffer: number[] = []
  private inputSampleRate = sampleRate

  process(
    inputs: Float32Array[][],
    _outputs: Float32Array[][],
    _parameters: Record<string, Float32Array>
  ): boolean {
    const input = inputs[0]?.[0]
    if (!input) return true

    for (let i = 0; i < input.length; i++) {
      this.buffer.push(input[i])
    }

    const ratio = this.inputSampleRate / SAMPLE_RATE_OUT
    const neededForChunk = Math.floor(SAMPLES_PER_CHUNK * ratio)

    while (this.buffer.length >= neededForChunk) {
      const chunk: number[] = []
      for (let i = 0; i < neededForChunk; i += ratio) {
        const idx = Math.floor(i)
        if (idx < this.buffer.length) {
          chunk.push(this.buffer[idx])
        }
      }
      this.buffer = this.buffer.slice(neededForChunk)

      const int16 = new Int16Array(chunk.length)
      for (let i = 0; i < chunk.length; i++) {
        const s = Math.max(-1, Math.min(1, chunk[i]))
        int16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
      }
      this.port.postMessage(int16.buffer, [int16.buffer])
    }

    return true
  }
}

registerProcessor("pcm-processor", PcmProcessor)
