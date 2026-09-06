/** A single chat message displayed in the UI */
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  sources?: string[];
  isSaved?: boolean;
  feedback?: "like" | "dislike";
  isStreaming?: boolean;
}

/** Response shape from POST /text_query */
export interface QueryResponse {
  status: "success" | "error";
  query: string;
  message: string;
}

/** Response shape from GET / */
export interface HealthResponse {
  status: string;
  version: string;
}
