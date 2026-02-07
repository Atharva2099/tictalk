/**
 * Gapless streaming PCM playback using Web Audio API.
 * Schedules chunks with precise timing to avoid gaps between Audio elements.
 */
import { pcmBase64ToWavBase64 } from "./pcmToWav"

const SAMPLE_RATE = 44100

let sharedContext: AudioContext | null = null

function getContext(): AudioContext {
  if (!sharedContext) sharedContext = new AudioContext()
  return sharedContext
}

/** Play a silent buffer to unlock AudioContext for autoplay. Call on user gesture. */
function unlockContext(ctx: AudioContext): void {
  if (ctx.state === "suspended") ctx.resume()
  const buffer = ctx.createBuffer(1, 1, 22050)
  const source = ctx.createBufferSource()
  source.buffer = buffer
  source.connect(ctx.destination)
  source.start(0)
}

export type StreamingPlayer = {
  playChunk: (chunkBase64: string) => void
  reset: () => void
  /** Call on user gesture (e.g. mic press, send click) to allow autoplay. */
  unlock: () => void
}

export function createStreamingPlayer(): StreamingPlayer {
  const chunkQueue: string[] = []
  let nextStartTime = 0
  let isProcessing = false

  const processQueue = async () => {
    if (chunkQueue.length === 0 || isProcessing) return
    isProcessing = true

    const ctx = getContext()
    if (ctx.state === "suspended") await ctx.resume()

    while (chunkQueue.length > 0) {
      const chunk = chunkQueue.shift()!
      const wavBase64 = pcmBase64ToWavBase64(chunk, SAMPLE_RATE)
      const binary = atob(wavBase64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i)

      try {
        const buffer = await ctx.decodeAudioData(bytes.buffer.slice(0))
        const source = ctx.createBufferSource()
        source.buffer = buffer
        source.connect(ctx.destination)
        nextStartTime = Math.max(nextStartTime, ctx.currentTime)
        source.start(nextStartTime)
        nextStartTime += buffer.duration
      } catch (e) {
        console.warn("StreamingAudioPlayer decode error:", e)
      }
    }

    isProcessing = false
  }

  return {
    playChunk(chunkBase64: string) {
      chunkQueue.push(chunkBase64)
      processQueue()
    },
    reset() {
      chunkQueue.length = 0
      nextStartTime = 0
    },
    unlock() {
      unlockContext(getContext())
    },
  }
}
