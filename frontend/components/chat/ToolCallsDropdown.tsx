import { ChevronDown, Loader2 } from "lucide-react";

interface ToolCall {
  name: string;
  status: 'success' | 'error' | 'running';
  output?: string;
}

interface ToolCallsDropdownProps {
  toolCalls: ToolCall[];
  isExpanded: boolean;
  onToggle: () => void;
}

export function ToolCallsDropdown({ toolCalls, isExpanded, onToggle }: ToolCallsDropdownProps) {
  if (toolCalls.length === 0) return null;

  return (
    <div className="border-t border-white/5 bg-black/50 px-4 py-2">
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between gap-2 text-sm text-white/70 hover:text-white transition-colors py-2"
      >
        <div className="flex items-center gap-2">
          <span className="text-base">🔧</span>
          <span className="font-medium">
            {toolCalls.length} tool call{toolCalls.length !== 1 ? 's' : ''} executed
          </span>
        </div>
        <ChevronDown 
          size={18} 
          className={`transition-transform ${isExpanded ? 'rotate-180' : ''}`}
        />
      </button>
      
      {isExpanded && (
        <div className="mt-2 mb-3 space-y-2 max-h-64 overflow-y-auto">
          {toolCalls.map((tool, idx) => (
            <div 
              key={idx}
              className="flex items-start gap-3 text-xs px-4 py-3 bg-black/60 border border-white/5 rounded-lg hover:border-white/10 transition-colors"
            >
              <div className="flex items-center justify-center w-6 h-6 rounded-full bg-white/5 shrink-0 mt-0.5">
                {tool.status === 'success' ? (
                  <span className="text-green-400 text-sm">✓</span>
                ) : tool.status === 'error' ? (
                  <span className="text-red-400 text-sm">✗</span>
                ) : (
                  <Loader2 size={14} className="animate-spin text-amber-400" />
                )}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-white/90 font-medium mb-1">{tool.name}</div>
                {tool.output && (
                  <div className="text-white/50 text-[11px] leading-relaxed wrap-break-word">
                    {tool.output}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
