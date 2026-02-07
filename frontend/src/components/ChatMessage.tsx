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
  return (
    <div
      className={cn(
        "flex gap-3 p-3 border-2 border-black bg-white",
        message.role === "user"
          ? "ml-8 bg-black text-white"
          : "mr-8 bg-white text-black",
        className
      )}
    >
      <div className="flex-shrink-0 mt-0.5">
        {message.role === "user" ? (
          <Mic className="h-4 w-4 text-white" />
        ) : (
          <Volume2 className="h-4 w-4 text-black" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <p
          className={cn(
            "text-xs font-bold uppercase mb-1 tracking-wide",
            message.role === "user" ? "text-white" : "text-black"
          )}
        >
          {message.role === "user" ? "You" : "Assistant"}
        </p>
        <p className="text-sm whitespace-pre-wrap leading-relaxed">{message.text}</p>
      </div>
    </div>
  )
}
