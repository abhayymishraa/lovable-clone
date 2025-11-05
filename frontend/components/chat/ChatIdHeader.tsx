import { Button } from "@/components/ui/button";
import { ChevronLeft, Eye, EyeOff } from "lucide-react";
import type { UserData } from "@/api";

interface ChatIdHeaderProps {
  userData: UserData | null;
  showPreview: boolean;
  onTogglePreview: () => void;
  onNewChat: () => void;
  onBack: () => void;
}

export function ChatIdHeader({ userData, showPreview, onTogglePreview, onNewChat, onBack }: ChatIdHeaderProps) {
  return (
    <div className="border-b border-white/5 backdrop-blur-md px-4 py-4">
      <div className="flex items-center justify-between">
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="text-white/60 hover:text-white hover:bg-white/5 font-sans"
        >
          <ChevronLeft size={24} />
        </Button>
        <h1 className="font-mono font-semibold tracking-tight text-white">WEB BUILDER AI</h1>
        <div className="flex items-center gap-2">
          {userData && (
            <div className="hidden md:flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
              <span className="text-sm text-white/60">{userData.email}</span>
              <span className="text-xs text-white/40">•</span>
              <span className="text-sm text-white font-medium">{userData.tokens_remaining} tokens</span>
            </div>
          )}
          <Button
            variant="ghost"
            size="icon"
            onClick={onTogglePreview}
            className="text-white/60 hover:text-white hover:bg-white/5 hidden md:flex"
          >
            {showPreview ? <Eye size={20} /> : <EyeOff size={20} />}
          </Button>
          <Button 
            className="bg-white text-black hover:bg-slate-100 text-sm font-sans"
            onClick={onNewChat}
          >
            New Chat
          </Button>
        </div>
      </div>
    </div>
  );
}
