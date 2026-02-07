/**
 * Wrap raw PCM (16-bit, mono) in a WAV header for playback.
 * Sample rate: 44100 (Cartesia TTS default).
 */
export function pcmBase64ToWavBase64(pcmBase64: string, sampleRate = 44100): string {
  const pcm = Uint8Array.from(atob(pcmBase64), (c) => c.charCodeAt(0))
  const numSamples = pcm.length / 2
  const dataSize = numSamples * 2
  const header = new ArrayBuffer(44)
  const view = new DataView(header)

  const writeStr = (offset: number, str: string) => {
    for (let i = 0; i < str.length; i++) view.setUint8(offset + i, str.charCodeAt(i))
  }

  writeStr(0, "RIFF")
  view.setUint32(4, 36 + dataSize, true)
  writeStr(8, "WAVE")
  writeStr(12, "fmt ")
  view.setUint32(16, 16, true) // fmt chunk size
  view.setUint16(20, 1, true) // PCM
  view.setUint16(22, 1, true) // mono
  view.setUint32(24, sampleRate, true)
  view.setUint32(28, sampleRate * 2, true) // byte rate
  view.setUint16(32, 2, true) // block align
  view.setUint16(34, 16, true) // bits per sample
  writeStr(36, "data")
  view.setUint32(40, dataSize, true)

  const wav = new Uint8Array(44 + pcm.length)
  wav.set(new Uint8Array(header), 0)
  wav.set(pcm, 44)

  let binary = ""
  for (let i = 0; i < wav.length; i += 8192) {
    binary += String.fromCharCode.apply(null, Array.from(wav.subarray(i, i + 8192)))
  }
  return btoa(binary)
}
