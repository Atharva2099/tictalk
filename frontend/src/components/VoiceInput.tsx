import { useState, useRef, useEffect } from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Mic, Send, Square } from "lucide-react"

const API_URL = import.meta.env.VITE_API_URL || ""

interface VoiceInputProps {
  onSend: (text: string, audioBlob?: Blob) => Promise<void>
  disabled?: boolean
}

export function VoiceInput({ onSend, disabled }: VoiceInputProps) {
  const [text, setText] = useState("")
  const [recording, setRecording] = useState(false)
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const chunksRef = useRef<Blob[]>([])

  const stopRecording = () => {
    if (mediaRecorderRef.current?.state === "recording") {
      mediaRecorderRef.current.stop()
      mediaRecorderRef.current = null
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

  const startRecording = async () => {
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
      <Button type="submit" disabled={disabled || !text.trim()}>
        <Send className="h-4 w-4" />
      </Button>
    </form>
  )
}
