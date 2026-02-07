import { useState, useRef } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { cn } from "@/lib/utils"
import { Mic, Send, Square } from "lucide-react"
import { PcmCapture } from "@/audio/PcmCapture"

const API_URL = import.meta.env.VITE_API_URL || ""
const CARTESIA_AGENT_ID = import.meta.env.VITE_CARTESIA_AGENT_ID || ""
const CARTESIA_VERSION = "2025-04-16"

export type StreamingEvent =
  | { type: "start"; text?: string }
  | { type: "transcript" | "text"; text: string }
  | { type: "audio_chunk"; data: string }
  | { type: "clear" }
  | { type: "done" }
  | { type: "error"; error: string }

interface VoiceInputProps {
  onSend: (text: string, audioBlob?: Blob) => Promise<void>
  onStreaming?: (event: StreamingEvent) => void
  onStreamEnd?: () => void
  onUnlock?: () => void
  disabled?: boolean
}

export function VoiceInput({ onSend, onStreaming, onStreamEnd, onUnlock, disabled }: VoiceInputProps) {
  const [text, setText] = useState("")
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])
  const pcmCaptureRef = useRef<PcmCapture | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const streamIdRef = useRef<string | null>(null)
  const streamEndTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const clearStreamEndTimeout = () => {
    if (streamEndTimeoutRef.current) {
      clearTimeout(streamEndTimeoutRef.current)
      streamEndTimeoutRef.current = null
    }
  }

  const scheduleStreamEnd = () => {
    clearStreamEndTimeout()
    onStreamEnd?.()
  }

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
    }
    pcmCaptureRef.current?.stop()
    pcmCaptureRef.current = null
    setRecording(false)
  }

  const closeLineWs = () => {
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) ws.close()
    wsRef.current = null
    streamIdRef.current = null
  }

  const handleMicToggle = () => {
    if (recording) {
      stopRecording()
      // Do not close WS - keep connection open to receive agent response
    } else {
      closeLineWs()
      startRecording()
    }
  }

  const startLineVoiceRecording = async () => {
    if (!onStreaming || !CARTESIA_AGENT_ID) {
      if (!CARTESIA_AGENT_ID) {
        onStreaming?.({ type: "error", error: "VITE_CARTESIA_AGENT_ID not configured" })
      }
      return
    }
    closeLineWs()
    setRecording(true)
    onStreaming({ type: "start" })
    streamEndTimeoutRef.current = setTimeout(scheduleStreamEnd, 180000)

    const base = API_URL || ""
    const tokenUrl = base ? `${base}/api/access-token` : "/api/access-token"
    let token: string
    try {
      const resp = await fetch(tokenUrl, { method: "POST" })
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}))
        throw new Error(err.detail || `Token request failed: ${resp.status}`)
      }
      const data = await resp.json()
      token = data.token || ""
      if (!token) throw new Error("No token in response")
    } catch (err) {
      stopRecording()
      onStreaming({ type: "error", error: err instanceof Error ? err.message : "Failed to get token" })
      return
    }

    const wsUrl = `wss://api.cartesia.ai/agents/stream/${CARTESIA_AGENT_ID}?access_token=${encodeURIComponent(token)}&cartesia_version=${CARTESIA_VERSION}`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    const startPcmCapture = () => {
      const pcm = new PcmCapture()
      pcmCaptureRef.current = pcm
      pcm.start({
        onChunk: (buf: ArrayBuffer) => {
          const w = wsRef.current
          const s = streamIdRef.current
          if (w?.readyState === WebSocket.OPEN && s) {
            const bytes = new Uint8Array(buf)
            const binary = String.fromCharCode.apply(null, Array.from(bytes))
            w.send(
              JSON.stringify({
                event: "media_input",
                stream_id: s,
                media: { payload: btoa(binary) },
              })
            )
          }
        },
        onError: (err) => {
          stopRecording()
          onStreaming({ type: "error", error: err.message })
          closeLineWs()
        },
      })
    }

    ws.onopen = () => {
      ws.send(
        JSON.stringify({
          event: "start",
          config: { input_format: "pcm_44100" },
        })
      )
    }

    ws.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.event === "ack") {
          streamIdRef.current = data.stream_id ?? null
          startPcmCapture()
        } else if (data.event === "media_output" && data.media?.payload) {
          onStreaming({ type: "audio_chunk", data: data.media.payload })
        } else if (data.event === "clear") {
          onStreaming({ type: "clear" })
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      clearStreamEndTimeout()
      onStreaming({ type: "error", error: "WebSocket error" })
      closeLineWs()
      stopRecording()
    }

    ws.onclose = () => {
      closeLineWs()
      clearStreamEndTimeout()
      onStreaming({ type: "done" })
      scheduleStreamEnd()
    }
  }

  const startLineRecording = () => {
    startLineVoiceRecording()
  }

  const startBatchRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      chunksRef.current = []

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data)
      }

      recorder.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop())
        if (chunksRef.current.length > 0) {
          const blob = new Blob(chunksRef.current, { type: "audio/webm" })
          await onSend("", blob)
        }
      }

      recorder.start(100)
      mediaRecorderRef.current = recorder
      setRecording(true)
    } catch (err) {
      console.error("Mic access failed:", err)
    }
  }

  const startRecording = async () => {
    if (onStreaming) {
      await startLineRecording()
    } else {
      await startBatchRecording()
    }
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const toSend = text.trim()
    if (!toSend) return
    await onSend(toSend)
    setText("")
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder={
          onStreaming
            ? "Type or hold mic to talk (Cartesia Line)"
            : "Type or press mic to record"
        }
        disabled={disabled || recording}
        className="flex-1 border-2 border-black bg-white text-black placeholder:text-gray-500 focus-visible:ring-0"
      />
      <Button
        type="button"
        variant="outline"
        size="icon"
        onClick={handleMicToggle}
        disabled={disabled}
        className={cn(
          "border-2 border-black bg-white text-black hover:bg-black hover:text-white",
          recording && "bg-black text-white hover:bg-black"
        )}
      >
        {recording ? (
          <Square className="h-4 w-4" />
        ) : (
          <Mic className="h-4 w-4" />
        )}
      </Button>
      <Button
        type="submit"
        disabled={disabled || !text.trim()}
        onMouseDown={() => onUnlock?.()}
        onTouchStart={() => onUnlock?.()}
        className="border-2 border-black bg-white text-black hover:bg-black hover:text-white"
      >
        <Send className="h-4 w-4" />
      </Button>
    </form>
  )
}
