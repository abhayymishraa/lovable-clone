import type { WebSocketMessage, WebSocketHandlers } from "./chat-types";

/**
 * Handles incoming WebSocket messages for the chat
 * Processes different event types and updates UI state accordingly
 */
export function handleWebSocketMessage(
  event: MessageEvent,
  handlers: WebSocketHandlers,
) {
  try {
    const data: WebSocketMessage = JSON.parse(event.data);
    console.log("📨 Received WebSocket message:", data);

    // Handle tool start events - show temporary tool card
    if (data.e === "tool_started") {
      const toolName = (data.tool_name as string) || "Unknown Tool";
      handlers.setCurrentTool({
        name: toolName,
        status: "running",
      });

      // Add tool to the last assistant message's tool_calls
      handlers.setMessages((prev) => {
        if (prev.length === 0) return prev;

        const lastMsg = prev[prev.length - 1];
        if (lastMsg.role === "assistant") {
          const newToolCall = {
            name: toolName,
            status: "running" as const,
          };

          return [
            ...prev.slice(0, -1),
            {
              ...lastMsg,
              tool_calls: [...(lastMsg.tool_calls || []), newToolCall],
            },
          ];
        }

        // If last message isn't assistant, create a new one
        return [
          ...prev,
          {
            id: Date.now().toString() + "-assistant",
            role: "assistant" as const,
            content: "",
            created_at: new Date().toISOString(),
            event_type: "tool_started",
            tool_calls: [
              {
                name: toolName,
                status: "running" as const,
              },
            ],
          },
        ];
      });

      return;
    }

    // Handle tool end events - show output briefly then hide
    if (data.e === "tool_completed") {
      const toolName =
        (data.tool_name as string) || handlers.currentTool?.name || "Tool";
      const toolOutput = data.tool_output || "Completed";

      handlers.setCurrentTool({
        name: toolName,
        status: "completed",
        output:
          typeof toolOutput === "string"
            ? toolOutput.substring(0, 200)
            : JSON.stringify(toolOutput).substring(0, 200),
      });

      // Update the tool status in messages
      handlers.setMessages((prev) => {
        return prev.map((msg) => {
          if (msg.role === "assistant" && msg.tool_calls) {
            return {
              ...msg,
              tool_calls: msg.tool_calls.map((tool) =>
                tool.name === toolName && tool.status === "running"
                  ? {
                      ...tool,
                      status: "success" as const,
                      output:
                        typeof toolOutput === "string"
                          ? toolOutput
                          : JSON.stringify(toolOutput),
                    }
                  : tool,
              ),
            };
          }
          return msg;
        });
      });

      // Hide after 2 seconds
      setTimeout(() => {
        handlers.setCurrentTool(null);
      }, 2000);

      return;
    }

    // Check if building has started
    if (data.e === "builder_started" || data.e === "workflow_started") {
      handlers.setIsBuilding(true);
    }

    // Check if app URL is received - start health check
    if (data.url) {
      handlers.setIsBuilding(false);
      handlers.pollUrlUntilReady(data.url);
    }

    // Check if workflow completed
    if (data.e === "workflow_completed") {
      handlers.setIsBuilding(false);
      handlers.setCurrentTool(null);

      // Refresh user data to update token count
      const updatedUser = localStorage.getItem("user_data");
      if (updatedUser) {
        handlers.setUserData(JSON.parse(updatedUser));
      }
    }

    // Handle initial message history
    if (data.type === "history" && data.messages) {
      console.log(
        "📜 Received message history:",
        data.messages.length,
        "messages",
      );
      console.log("🔍 Full history data:", data);
      console.log("🔗 App URL in data:", data.app_url);
      const consolidatedMessages = handlers.consolidateMessages(data.messages);
      console.log(
        "📦 Consolidated to:",
        consolidatedMessages.length,
        "messages",
      );
      handlers.setMessages(consolidatedMessages);

      // Set app URL if it exists - skip health check for restored URLs
      if (data.app_url) {
        console.log(
          "✅ Setting app URL directly (no health check for restored URL):",
          data.app_url,
        );
        handlers.setAppUrl(data.app_url);
      } else {
        console.log("⚠️ No app_url found in history data");
      }

      return;
    }

    // Handle errors
    if (data.type === "error" || data.e === "error") {
      handlers.setError((data.message as string) || "An error occurred");
    }

    // Handle token status updates
    if (data.type === "token_update" || data.tokens_remaining !== undefined) {
      console.log("🔄 Token update received:", data.tokens_remaining);
      const user = JSON.parse(localStorage.getItem("user_data") || "{}");
      user.tokens_remaining = data.tokens_remaining;
      if (data.reset_in_hours !== undefined) {
        user.reset_in_hours = data.reset_in_hours;
      }
      localStorage.setItem("user_data", JSON.stringify(user));
      handlers.setUserData(user);
      console.log("✅ User data updated:", user);
    }

    // Handle thinking content
    if (data.e === "thinking") {
      handlers.setMessages((prev) => {
        const lastMsg = prev[prev.length - 1];
        
        // Handle message that could be string or array
        let newContent = data.message || data.content;
        if (Array.isArray(newContent)) {
          // If message is an array, extract text from it (e.g., LLM content blocks)
          newContent = newContent
            .map((item: any) => {
              if (typeof item === "string") return item;
              if (item.text) return item.text;
              if (item.type === "text" && item.text) return item.text;
              return JSON.stringify(item);
            })
            .join("\n");
        }
        newContent = String(newContent); // Ensure it's a string
        const formatted = data.formatted as string | undefined;

        // Check if the new content looks like JSON (starts with { or contains ```json)
        const looksLikeJson =
          newContent.trim().startsWith("{") ||
          newContent.includes("```json") ||
          newContent.includes('"plan"') ||
          newContent.includes('"application_overview"');

        if (lastMsg?.role === "assistant") {
          // If new content is JSON-like, separate it with double newline for better parsing
          const separator = looksLikeJson ? "\n\n" : "\n";

          // Append thinking to existing assistant message
          return [
            ...prev.slice(0, -1),
            {
              ...lastMsg,
              content: lastMsg.content + separator + newContent,
              formatted: formatted || lastMsg.formatted,
            },
          ];
        }

        // Create new assistant message
        return [
          ...prev,
          {
            id: Date.now().toString() + "-assistant",
            role: "assistant" as const,
            content: newContent,
            formatted: formatted,
            created_at: new Date().toISOString(),
            event_type: data.e,
          },
        ];
      });
      return;
    }

    // Handle planner complete (with formatted plan)
    if (data.e === "planner_complete") {
      const planContent = data.content || data.plan;
      const formatted = data.formatted as string | undefined;
      const messageContent = data.message || "Planning completed";

      handlers.setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString() + "-plan",
          role: "assistant" as const,
          content:
            typeof planContent === "object"
              ? JSON.stringify(planContent, null, 2)
              : String(planContent),
          formatted: formatted,
          created_at: new Date().toISOString(),
          event_type: "planner_complete",
        },
      ]);
      return;
    }
  } catch (err) {
    console.error("Failed to parse WebSocket message:", err);
  }
}

/**
 * Creates WebSocket connection handlers
 */
export function createWebSocketHandlers(
  chatId: string,
  onConnected: () => void,
  onDisconnected: () => void,
  onError: (error: Event) => void,
  onMessage: (event: MessageEvent) => void,
) {
  return {
    onopen: () => {
      console.log("✅ WebSocket connected for chat:", chatId);
      onConnected();
    },
    onerror: (error: Event) => {
      onError(error);
    },
    onmessage: (event: MessageEvent) => {
      onMessage(event);
    },
    onclose: (event: CloseEvent) => {
      console.log(
        "⛔ WebSocket disconnected, code:",
        event.code,
        "reason:",
        event.reason,
      );
      onDisconnected();
    },
  };
}
