import { useState, useRef } from "react"
import { ChatMessage, type Message } from "@/components/ChatMessage"
import { VoiceInput, type StreamingEvent } from "@/components/VoiceInput"
import { pcmBase64ToWavBase64 } from "@/audio/pcmToWav"
import { createStreamingPlayer } from "@/audio/StreamingAudioPlayer"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

const API_URL = import.meta.env.VITE_API_URL || ""
const TTS_SAMPLE_RATE = 44100

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)
  const streamingUserMsgIdRef = useRef<string | null>(null)
  const streamingAssistantMsgIdRef = useRef<string | null>(null)
  const streamingAudioChunksRef = useRef<string[]>([])
  const streamingPlayerRef = useRef(createStreamingPlayer())

  const streamAudioChunk = (chunkBase64: string) => {
    streamingAudioChunksRef.current.push(chunkBase64)
    streamingPlayerRef.current.playChunk(chunkBase64)
  }

  const handleStreaming = (event: StreamingEvent) => {
    if (event.type === "start") {
      streamingPlayerRef.current.unlock()
      setLoading(true)
      const userMsgId = crypto.randomUUID()
      streamingUserMsgIdRef.current = userMsgId
      streamingAudioChunksRef.current = []
      streamingPlayerRef.current.reset()
      setMessages((prev) => [
        ...prev,
        { id: userMsgId, role: "user", text: event.text ?? "(recording...)" },
      ])
    } else if (event.type === "transcript") {
      const id = streamingUserMsgIdRef.current
      if (id)
        setMessages((prev) =>
          prev.map((m) => (m.id === id ? { ...m, text: event.text } : m))
        )
    } else if (event.type === "text") {
      const id = streamingAssistantMsgIdRef.current
      if (id) {
        setMessages((prev) =>
          prev.map((m) => (m.id === id ? { ...m, text: event.text } : m))
        )
      } else {
        const assistantMsgId = crypto.randomUUID()
        streamingAssistantMsgIdRef.current = assistantMsgId
        setMessages((prev) => [
          ...prev,
          { id: assistantMsgId, role: "assistant", text: event.text },
        ])
      }
    } else if (event.type === "audio_chunk") {
      streamAudioChunk(event.data)
    } else if (event.type === "done") {
      const id = streamingAssistantMsgIdRef.current
      const chunks = streamingAudioChunksRef.current
      if (id && chunks.length > 0) {
        const pcmBase64 = chunks.join("")
        const audioBase64 = pcmBase64ToWavBase64(pcmBase64, TTS_SAMPLE_RATE)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === id ? { ...m, audioBase64 } : m
          )
        )
      }
      streamingUserMsgIdRef.current = null
      streamingAssistantMsgIdRef.current = null
      streamingAudioChunksRef.current = []
      setLoading(false)
    } else if (event.type === "error") {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `Error: ${event.error}`,
        },
      ])
      streamingUserMsgIdRef.current = null
      streamingAssistantMsgIdRef.current = null
      setLoading(false)
    }
  }

  const sendMessage = async (text: string, audioBlob?: Blob) => {
    setLoading(true)
    const userText = text || "(recording...)"
    const userMsgId = crypto.randomUUID()
    setMessages((prev) => [
      ...prev,
      { id: userMsgId, role: "user", text: userText },
    ])

    try {
      const formData = new FormData()
      if (audioBlob) {
        formData.append("audio", audioBlob, "recording.webm")
      } else if (text) {
        formData.append("text", text)
      }

      const base = API_URL || ""
      const url = base ? `${base}/api/chat` : "/api/chat"
      const res = await fetch(url, {
        method: "POST",
        body: formData,
      })

      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }))
        throw new Error(err.detail || "Request failed")
      }

      const data = await res.json()
      const transcript = data.transcript
      const audioBase64 = data.audio || undefined
      setMessages((prev) => {
        const updated = transcript
          ? prev.map((m) =>
              m.id === userMsgId ? { ...m, text: transcript } : m
            )
          : prev
        return [
          ...updated,
          {
            id: crypto.randomUUID(),
            role: "assistant",
            text: data.text,
            audioBase64,
          },
        ]
      })
      if (audioBase64) {
        streamingPlayerRef.current.unlock()
        const audio = new Audio(`data:audio/wav;base64,${audioBase64}`)
        audio.play()
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          text: `Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col p-4 max-w-2xl mx-auto">
      <Card className="flex-1 flex flex-col min-h-0">
        <CardHeader>
          <h1 className="text-xl font-semibold">TicTalk</h1>
          <p className="text-sm text-muted-foreground">
            Voice chat with Cartesia + Claude. Type or hold mic to speak.
          </p>
        </CardHeader>
        <CardContent className="flex-1 flex flex-col min-h-0 p-0">
          <ScrollArea className="flex-1 p-4 min-h-[300px]">
            <div className="space-y-4">
              {messages.length === 0 && (
                <p className="text-sm text-muted-foreground text-center py-8">
                  No messages yet. Type something or hold the mic to speak.
                </p>
              )}
              {messages.map((m) => (
                <ChatMessage key={m.id} message={m} />
              ))}
              {loading && (
                <div className="flex gap-3 p-3 rounded-lg bg-primary/5 mr-8">
                  <div className="animate-pulse h-4 w-4 rounded bg-muted" />
                  <p className="text-sm text-muted-foreground">Thinking...</p>
                </div>
              )}
            </div>
          </ScrollArea>
          <div className="p-4 border-t">
            <VoiceInput
              onSend={sendMessage}
              onStreaming={handleStreaming}
              onStreamEnd={() => setLoading(false)}
              onUnlock={() => streamingPlayerRef.current.unlock()}
              disabled={loading}
            />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default App
