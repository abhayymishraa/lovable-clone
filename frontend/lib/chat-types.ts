// Message Types
export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  formatted?: string; // Formatted markdown content from backend
  created_at: string;
  event_type?: string;
  tool_calls?: Array<{
    name: string;
    status: "success" | "error" | "running";
    output?: string;
  }>;
}

export interface ActiveToolCall {
  name: string;
  status: "running" | "completed";
  output?: string;
}

export interface WebSocketMessage {
  type?: string;
  e?: string;
  message?: string;
  content?: any; // Raw content
  formatted?: string; // Formatted markdown
  url?: string;
  app_url?: string;
  messages?: Message[];
  tool_name?: string;
  tool_output?: string | object;
  tokens_remaining?: number;
  reset_in_hours?: number;
  [key: string]: unknown;
}

// State Setters Type
export interface WebSocketHandlers {
  setCurrentTool: (tool: ActiveToolCall | null) => void;
  setIsBuilding: (isBuilding: boolean) => void;
  pollUrlUntilReady: (url: string) => void;
  setMessages: React.Dispatch<React.SetStateAction<Message[]>>;
  setAppUrl: (url: string | null) => void;
  setError: (error: string | null) => void;
  setUserData: (data: any) => void;
  consolidateMessages: (messages: Message[]) => Message[];
  currentTool: ActiveToolCall | null;
}
