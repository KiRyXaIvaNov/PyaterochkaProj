export type ChatState = "clarify" | "solution" | "finish" | "specialist";

export interface Message {
  id: string;
  role: "user" | "assistant";
  text: string;
  timestamp: number;
}

export interface ChatResponse {
  sessionId: string;
  reply: string;
  category: string | null;
  state: ChatState;
  options: string[] | null;
  steps: string[] | null;
  confidence: number | null;
}