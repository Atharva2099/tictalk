/**
 * Captures raw PCM from the microphone at 16kHz via AudioWorklet.
 * Used for streaming STT with Cartesia.
 */

const SAMPLE_RATE = 16000

export interface PcmCaptureOptions {
  onChunk: (pcmData: ArrayBuffer) => void
  onError?: (err: Error) => void
}

export class PcmCapture {
  private context: AudioContext | null = null
  private node: AudioWorkletNode | null = null
  private stream: MediaStream | null = null

  async start(options: PcmCaptureOptions): Promise<void> {
    try {
      this.stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.context = new AudioContext()
      const src = this.context.createMediaStreamSource(this.stream)

      await this.context.audioWorklet.addModule(
        new URL("./pcm-processor.ts", import.meta.url).href
      )

      this.node = new AudioWorkletNode(this.context, "pcm-processor")
      this.node.port.onmessage = (e: MessageEvent<ArrayBuffer>) => {
        options.onChunk(e.data)
      }
      src.connect(this.node)
    } catch (err) {
      options.onError?.(err instanceof Error ? err : new Error(String(err)))
    }
  }

  stop(): void {
    if (this.node) {
      this.node.disconnect()
      this.node = null
    }
    if (this.stream) {
      this.stream.getTracks().forEach((t) => t.stop())
      this.stream = null
    }
    if (this.context) {
      this.context.close()
      this.context = null
    }
  }

  getSampleRate(): number {
    return SAMPLE_RATE
  }
}
