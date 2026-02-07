import { useState } from "react"
import { ChatMessage, type Message } from "@/components/ChatMessage"
import { VoiceInput } from "@/components/VoiceInput"
import { Card, CardContent, CardHeader } from "@/components/ui/card"
import { ScrollArea } from "@/components/ui/scroll-area"

const API_URL = import.meta.env.VITE_API_URL || ""

function App() {
  const [messages, setMessages] = useState<Message[]>([])
  const [loading, setLoading] = useState(false)

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
            audioBase64: data.audio || undefined,
          },
        ]
      })
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
            <VoiceInput onSend={sendMessage} disabled={loading} />
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default App
