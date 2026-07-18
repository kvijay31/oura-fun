export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export type StreamEvent =
  | { type: "text"; text: string }
  | { type: "tool_start"; name: string }
  | { type: "tool_running"; name: string; input: Record<string, unknown> }
  | { type: "tool_done"; name: string }
  | { type: "done" }
  | { type: "error"; message: string };

export async function* streamChat(
  messages: ChatMessage[]
): AsyncGenerator<StreamEvent> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });

  if (!response.ok) {
    const text = await response.text();
    yield { type: "error", message: `HTTP ${response.status}: ${text}` };
    return;
  }

  const reader = response.body!.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() ?? "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        const data = line.slice(6).trim();
        if (data) {
          try {
            yield JSON.parse(data) as StreamEvent;
          } catch {
            // malformed SSE line — skip
          }
        }
      }
    }
  }

  // flush any remaining
  if (buffer.startsWith("data: ")) {
    const data = buffer.slice(6).trim();
    if (data) {
      try {
        yield JSON.parse(data) as StreamEvent;
      } catch {
        // ignore
      }
    }
  }
}

export function formatToolName(name: string): string {
  return name
    .split("_")
    .map((w) => w[0].toUpperCase() + w.slice(1))
    .join(" ");
}
