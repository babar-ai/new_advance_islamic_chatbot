import { QueryResponse, HealthResponse } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

/**
 * Send a user query to the FastAPI backend.
 * Returns the AI-generated response string.
 */
export async function sendQuery(query: string): Promise<string> {
  try {
    const res = await fetch(`${API_URL}/text_query`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (res.status === 429) {
      throw new Error("Rate limit exceeded (10 requests/min). Please wait a moment and try again.");
    }

    if (res.status === 504) {
      throw new Error("The request timed out while generating a response. Please try again.");
    }

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      const detail = errorData?.detail || "Unable to reach the server. Please check your backend connection.";
      throw new Error(detail);
    }

    const data: QueryResponse = await res.json();

    if (data.status !== "success") {
      throw new Error(data.message || "Failed to get a response from Islamic Assistant.");
    }

    return data.message;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error("Cannot connect to backend server at http://localhost:8000. Please ensure the FastAPI server or Docker containers are running.");
    }
    throw error;
  }
}

/**
 * Check backend health status (GET /)
 */
export async function checkBackendHealth(): Promise<{ isOnline: boolean; version?: string }> {
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 3500);
    const res = await fetch(`${API_URL}/`, {
      method: "GET",
      signal: controller.signal,
    });
    clearTimeout(timeoutId);

    if (res.ok) {
      const data: HealthResponse = await res.json();
      return { isOnline: true, version: data.version };
    }
    return { isOnline: false };
  } catch {
    return { isOnline: false };
  }
}

/**
 * Stream a user query via Server-Sent Events (SSE).
 * Calls onToken for each LLM token chunk, onStatus for pipeline phase updates.
 * Returns the full response string once streaming completes.
 */
export async function sendQueryStream(
  query: string,
  onToken: (token: string) => void,
  onStatus?: (status: string, message: string) => void,
): Promise<string> {
  try {
    const res = await fetch(`${API_URL}/text_query/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ query }),
    });

    if (res.status === 429) {
      throw new Error("Rate limit exceeded (10 requests/min). Please wait a moment and try again.");
    }

    if (!res.ok) {
      const errorData = await res.json().catch(() => null);
      const detail = errorData?.detail || "Unable to reach the server. Please check your backend connection.";
      throw new Error(detail);
    }

    if (!res.body) {
      throw new Error("No response body received from streaming endpoint.");
    }

    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let fullResponse = "";
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });

      // SSE events are separated by double newlines
      const parts = buffer.split("\n\n");
      // Keep the last incomplete chunk in the buffer
      buffer = parts.pop() || "";

      for (const part of parts) {
        const trimmed = part.trim();
        if (!trimmed) continue;

        // Each SSE event line starts with "data: "
        for (const line of trimmed.split("\n")) {
          if (!line.startsWith("data: ")) continue;

          try {
            const event = JSON.parse(line.slice(6));

            // Status events (searching / generating)
            if (event.status && onStatus) {
              onStatus(event.status, event.message);
            }

            // Token chunk
            if (event.token !== undefined && !event.done) {
              onToken(event.token);
              fullResponse += event.token;
            }

            // Done event — return the full response
            if (event.done) {
              return event.full_response || fullResponse;
            }
          } catch {
            // Skip malformed SSE lines
          }
        }
      }
    }

    return fullResponse;
  } catch (error) {
    if (error instanceof TypeError && error.message.includes("fetch")) {
      throw new Error("Cannot connect to backend server. Please ensure the FastAPI server or Docker containers are running.");
    }
    throw error;
  }
}

