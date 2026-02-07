import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { Mic, Volume2 } from "lucide-react"

export interface Message {
  id: string
  role: "user" | "assistant"
  text: string
  audioBase64?: string
}

interface ChatMessageProps {
  message: Message
  className?: string
}

export function ChatMessage({ message, className }: ChatMessageProps) {
  const playAudio = () => {
    if (!message.audioBase64) return
    const audio = new Audio(`data:audio/wav;base64,${message.audioBase64}`)
    audio.play()
  }

  return (
    <div
      className={cn(
        "flex gap-3 p-3 rounded-lg",
        message.role === "user"
          ? "bg-muted ml-8"
          : "bg-primary/5 mr-8",
        className
      )}
    >
      <div className="flex-shrink-0 mt-0.5">
        {message.role === "user" ? (
          <Mic className="h-4 w-4 text-muted-foreground" />
        ) : (
          <Volume2 className="h-4 w-4 text-muted-foreground" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-muted-foreground mb-1">
          {message.role === "user" ? "You" : "Assistant"}
        </p>
        <p className="text-sm whitespace-pre-wrap">{message.text}</p>
        {message.role === "assistant" && message.audioBase64 && (
          <Button
            variant="outline"
            size="sm"
            className="mt-2"
            onClick={playAudio}
          >
            <Volume2 className="h-4 w-4 mr-2" />
            Play
          </Button>
        )}
      </div>
    </div>
  )
}
