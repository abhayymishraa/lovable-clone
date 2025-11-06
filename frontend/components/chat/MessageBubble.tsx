import { Loader2, ChevronDown, ChevronRight, Code2 } from "lucide-react";
import { useState } from "react";
import { FormattedMessage } from "./FormattedMessage";

interface ToolCall {
  name: string;
  status: "success" | "error" | "running";
  output?: string;
}

interface ActiveToolCall {
  name: string;
  status: "running" | "completed";
  output?: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  formatted?: string; // New field for formatted markdown
  event_type?: string;
  tool_calls?: ToolCall[];
}

interface MessageBubbleProps {
  message: Message;
  isLastMessage: boolean;
  currentTool: ActiveToolCall | null;
}

// Helper to detect and format JSON
function formatContent(content: string) {
  const parts: Array<{ type: "text" | "json" | "code"; content: string }> = [];

  // Split by double newlines first to separate sections
  const sections = content.split("\n\n");

  sections.forEach((section) => {
    section = section.trim();
    if (!section) return;

    // Try to detect JSON blocks with ```json wrapper
    const jsonBlockMatch = section.match(/```json\s*([\s\S]*?)\s*```/);
    if (jsonBlockMatch) {
      const textBefore = section.substring(0, jsonBlockMatch.index).trim();
      if (textBefore) {
        parts.push({ type: "text", content: textBefore });
      }
      parts.push({ type: "json", content: jsonBlockMatch[1].trim() });
      const textAfter = section
        .substring(jsonBlockMatch.index! + jsonBlockMatch[0].length)
        .trim();
      if (textAfter) {
        parts.push({ type: "text", content: textAfter });
      }
      return;
    }

    // Check if entire section is JSON
    if (section.startsWith("{") && section.endsWith("}")) {
      try {
        JSON.parse(section);
        parts.push({ type: "json", content: section });
        return;
      } catch {
        // Not valid JSON, treat as text
      }
    }

    // Check for code blocks
    const codeBlockMatch = section.match(/```(\w+)?\s*([\s\S]*?)\s*```/);
    if (codeBlockMatch) {
      const textBefore = section.substring(0, codeBlockMatch.index).trim();
      if (textBefore) {
        parts.push({ type: "text", content: textBefore });
      }
      parts.push({
        type: "code",
        content: codeBlockMatch[2].trim(),
      });
      const textAfter = section
        .substring(codeBlockMatch.index! + codeBlockMatch[0].length)
        .trim();
      if (textAfter) {
        parts.push({ type: "text", content: textAfter });
      }
      return;
    }

    // Otherwise it's text
    parts.push({ type: "text", content: section });
  });

  return parts.length > 0 ? parts : [{ type: "text" as const, content }];
}

function JsonBlock({ content }: { content: string }) {
  const [isExpanded, setIsExpanded] = useState(false);

  try {
    const parsed = JSON.parse(content);
    const formatted = JSON.stringify(parsed, null, 2);
    const lines = formatted.split("\n");
    const preview = lines.slice(0, 3).join("\n");

    // Try to extract a title from the JSON
    const title =
      parsed.planTitle || parsed.title || parsed.name || "Implementation Plan";

    return (
      <div className="my-3 border border-white/10 rounded-lg overflow-hidden bg-black/40">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="w-full flex items-center gap-2 px-3 py-2 bg-white/5 hover:bg-white/10 transition-colors text-xs"
        >
          {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
          <Code2 size={14} />
          <span className="text-white/70 font-medium">{title}</span>
          <span className="text-white/40 text-[10px] ml-auto">
            {lines.length} lines •{" "}
            {isExpanded ? "Click to collapse" : "Click to expand"}
          </span>
        </button>
        {isExpanded && (
          <pre className="p-3 text-[11px] leading-relaxed font-mono text-white/70 overflow-x-auto max-h-96 overflow-y-auto">
            {formatted}
          </pre>
        )}
        {!isExpanded && (
          <pre className="p-3 text-[11px] leading-relaxed font-mono text-white/40">
            {preview}
            <span className="text-white/30">...</span>
          </pre>
        )}
      </div>
    );
  } catch {
    return (
      <pre className="my-3 p-3 text-xs font-mono text-white/60 bg-black/40 border border-white/10 rounded-lg overflow-x-auto">
        {content}
      </pre>
    );
  }
}

function CodeBlock({ content, lang }: { content: string; lang?: string }) {
  return (
    <div className="my-3 border border-white/10 rounded-lg overflow-hidden bg-black/40">
      {lang && (
        <div className="px-3 py-1.5 bg-white/5 text-[10px] text-white/50 font-mono border-b border-white/10">
          {lang}
        </div>
      )}
      <pre className="p-3 text-xs leading-relaxed font-mono text-white/70 overflow-x-auto max-h-96 overflow-y-auto">
        {content}
      </pre>
    </div>
  );
}

function CollapsibleText({ paragraphs }: { paragraphs: string[] }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const displayParagraphs = isExpanded ? paragraphs : paragraphs.slice(0, 5);

  return (
    <>
      {displayParagraphs.map((line, j) => (
        <p key={j} className="text-white/90">
          {line}
        </p>
      ))}
      {paragraphs.length > 5 && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="text-xs text-white/50 hover:text-white/70 transition-colors flex items-center gap-1 mt-2"
        >
          {isExpanded ? (
            <>
              <ChevronDown size={12} />
              Show less
            </>
          ) : (
            <>
              <ChevronRight size={12} />
              Show {paragraphs.length - 5} more lines
            </>
          )}
        </button>
      )}
    </>
  );
}

export function MessageBubble({
  message,
  isLastMessage,
  currentTool,
}: MessageBubbleProps) {
  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-xl px-4 py-3 rounded-lg bg-white text-black">
          <p className="text-sm">{message.content}</p>
        </div>
      </div>
    );
  }

  // Check if we have formatted content (from backend)
  const hasFormatted =
    message.formatted && message.formatted !== message.content;

  return (
    <div className="flex justify-start">
      <div className="max-w-2xl w-full bg-white/5 text-white border border-white/10 rounded-lg p-4">
        <div className="flex items-start gap-3">
          <div className="flex-1 min-w-0">
            {/* Use FormattedMessage component for formatted content */}
            {hasFormatted ? (
              <FormattedMessage
                content={message.content}
                formatted={message.formatted}
                type={message.event_type}
              />
            ) : (
              <div className="text-sm leading-relaxed space-y-2">
                {formatContent(message.content).map((part, i) => {
                  if (part.type === "json") {
                    return <JsonBlock key={i} content={part.content} />;
                  } else if (part.type === "code") {
                    return <CodeBlock key={i} content={part.content} />;
                  } else {
                    const paragraphs = part.content
                      .split("\n")
                      .filter((line) => line.trim());

                    if (paragraphs.length > 10) {
                      return (
                        <CollapsibleText key={i} paragraphs={paragraphs} />
                      );
                    }

                    return paragraphs.map((line, j) => (
                      <p key={`${i}-${j}`} className="text-white/90">
                        {line}
                      </p>
                    ));
                  }
                })}
              </div>
            )}

            {/* Active Tool Section - only show on last message */}
            {currentTool && isLastMessage && (
              <div className="mt-4 pt-3 border-t border-white/10">
                <div className="bg-black/40 border border-amber-500/30 rounded-lg p-3">
                  <div className="flex items-start gap-2">
                    {currentTool.status === "running" ? (
                      <Loader2
                        size={14}
                        className="animate-spin text-amber-400 mt-0.5 shrink-0"
                      />
                    ) : (
                      <span className="text-green-400 text-sm shrink-0">✓</span>
                    )}
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-mono text-amber-300 mb-1">
                        Tool: {currentTool.name}
                      </p>
                      {currentTool.status === "running" ? (
                        <p className="text-xs text-white/50">Processing...</p>
                      ) : (
                        currentTool.output && (
                          <div className="text-xs text-white/60 bg-black/30 rounded p-2 mt-1 font-mono max-h-32 overflow-y-auto wrap-break-word">
                            {currentTool.output}
                          </div>
                        )
                      )}
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
