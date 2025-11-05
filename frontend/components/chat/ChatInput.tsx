import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowUp, Plus, Paperclip } from "lucide-react";

interface ChatInputProps {
  input: string;
  wsConnected: boolean;
  isBuilding: boolean;
  onInputChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

export function ChatInput({
  input,
  wsConnected,
  isBuilding,
  onInputChange,
  onSubmit,
}: ChatInputProps) {
  return (
    <div className="border-t border-white/5 bg-black/40 backdrop-blur-md p-4">
      <form onSubmit={onSubmit}>
        <div className="bg-white/5 border border-white/10 rounded-lg p-3 hover:border-white/20 transition-colors">
          <div className="flex gap-3">
            <Input
              type="text"
              value={input}
              onChange={(e) => onInputChange(e.target.value)}
              placeholder="Type your message..."
              className="flex-1 border-0 bg-transparent text-white font-sans placeholder:text-white/40 focus-visible:ring-0"
              disabled={!wsConnected || isBuilding}
            />
            <div className="flex items-center gap-1">
              <button
                type="button"
                className="p-2 hover:bg-white/10 rounded transition text-white/60 hover:text-white"
              >
                <Plus size={18} />
              </button>
              <button
                type="button"
                className="p-2 hover:bg-white/10 rounded transition text-white/60 hover:text-white"
              >
                <Paperclip size={18} />
              </button>
              <Button
                type="submit"
                disabled={!wsConnected || !input.trim() || isBuilding}
                size="icon"
                className="rounded-lg w-8 h-8 bg-white text-black hover:bg-slate-100"
              >
                <ArrowUp size={16} />
              </Button>
            </div>
          </div>
        </div>
      </form>
    </div>
  );
}
