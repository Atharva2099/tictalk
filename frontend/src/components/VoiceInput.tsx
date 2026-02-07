import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Mic, Send, Square } from "lucide-react"
import { PcmCapture } from "@/audio/PcmCapture"

const API_URL = import.meta.env.VITE_API_URL || ""

export type StreamingEvent =
  | { type: "start"; text?: string }
  | { type: "transcript" | "text"; text: string }
  | { type: "audio_chunk"; data: string }
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
    const ws = wsRef.current
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: "audio_end", sample_rate: 16000 }))
    }
    setRecording(false)
  }

  useEffect(() => {
    if (!recording) return
    const handleUp = () => stopRecording()
    window.addEventListener("mouseup", handleUp)
    window.addEventListener("touchend", handleUp)
    return () => {
      window.removeEventListener("mouseup", handleUp)
      window.removeEventListener("touchend", handleUp)
    }
  }, [recording])

  const startStreamingRecording = async () => {
    if (!onStreaming) return
    onStreaming({ type: "start" })
    streamEndTimeoutRef.current = setTimeout(scheduleStreamEnd, 90000)
    const base = API_URL || ""
    const wsUrl = base ? `${base.replace(/^http/, "ws")}/api/ws/chat` : `ws://${location.host}/api/ws/chat`
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws

    ws.onopen = async () => {
      const capture = new PcmCapture()
      pcmCaptureRef.current = capture
      await capture.start({
        onChunk: (buf) => {
          if (ws.readyState === WebSocket.OPEN) {
            const bytes = new Uint8Array(buf)
            let binary = ""
            for (let i = 0; i < bytes.length; i += 8192) {
              binary += String.fromCharCode.apply(null, Array.from(bytes.subarray(i, i + 8192)))
            }
            ws.send(JSON.stringify({ type: "audio_chunk", data: btoa(binary) }))
          }
        },
        onError: (err) => onStreaming({ type: "error", error: err.message }),
      })
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === "transcript" || msg.type === "text") {
          onStreaming({ type: msg.type, text: msg.text })
        } else if (msg.type === "audio_chunk") {
          onStreaming({ type: "audio_chunk", data: msg.data })
        } else if (msg.type === "done") {
          clearStreamEndTimeout()
          onStreaming({ type: "done" })
          ws.close()
        } else if (msg.type === "error") {
          clearStreamEndTimeout()
          onStreaming({ type: "error", error: msg.error })
          ws.close()
        }
      } catch {
        // ignore parse errors
      }
    }

    ws.onerror = () => {
      clearStreamEndTimeout()
      onStreaming({ type: "error", error: "WebSocket error" })
      ws.close()
    }
    ws.onclose = () => {
      wsRef.current = null
      scheduleStreamEnd()
    }

    setRecording(true)
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
      await startStreamingRecording()
    } else {
      await startBatchRecording()
    }
  }

  const sendTextViaStreaming = (toSend: string) => {
    if (!onStreaming) return
    onStreaming({ type: "start", text: toSend })
    streamEndTimeoutRef.current = setTimeout(scheduleStreamEnd, 90000)
    const base = API_URL || ""
    const wsUrl = base ? `${base.replace(/^http/, "ws")}/api/ws/chat` : `ws://${location.host}/api/ws/chat`
    const ws = new WebSocket(wsUrl)

    ws.onopen = () => {
      ws.send(JSON.stringify({ type: "text", text: toSend }))
    }

    ws.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data)
        if (msg.type === "transcript" || msg.type === "text") {
          onStreaming({ type: msg.type, text: msg.text })
        } else if (msg.type === "audio_chunk") {
          onStreaming({ type: "audio_chunk", data: msg.data })
        } else if (msg.type === "done") {
          clearStreamEndTimeout()
          onStreaming({ type: "done" })
          ws.close()
        } else if (msg.type === "error") {
          clearStreamEndTimeout()
          onStreaming({ type: "error", error: msg.error })
          ws.close()
        }
      } catch {
        // ignore
      }
    }

    ws.onerror = () => {
      clearStreamEndTimeout()
      onStreaming({ type: "error", error: "WebSocket error" })
      ws.close()
    }
    ws.onclose = () => {
      wsRef.current = null
      scheduleStreamEnd()
    }

    wsRef.current = ws
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    const toSend = text.trim()
    if (!toSend) return
    if (onStreaming) {
      sendTextViaStreaming(toSend)
      setText("")
    } else {
      await onSend(toSend)
      setText("")
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex gap-2">
      <Input
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Type or hold mic to speak..."
        disabled={disabled || recording}
        className="flex-1"
      />
      <Button
        type="button"
        variant={recording ? "destructive" : "outline"}
        size="icon"
        onMouseDown={recording ? undefined : startRecording}
        onTouchStart={(e) => {
          if (!recording) {
            e.preventDefault()
            startRecording()
          }
        }}
        disabled={disabled}
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
      >
        <Send className="h-4 w-4" />
      </Button>
    </form>
  )
}
