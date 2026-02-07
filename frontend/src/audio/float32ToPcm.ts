/**
 * Converts Float32Array audio (-1 to 1) to PCM s16le (Int16Array)
 * for Cartesia STT which expects 16kHz, 16-bit PCM.
 */
export function float32ToPcmS16le(float32: Float32Array): Uint8Array {
  const pcm = new Int16Array(float32.length)
  for (let i = 0; i < float32.length; i++) {
    const s = Math.max(-1, Math.min(1, float32[i]))
    pcm[i] = s < 0 ? s * 0x8000 : s * 0x7fff
  }
  return new Uint8Array(pcm.buffer)
}
