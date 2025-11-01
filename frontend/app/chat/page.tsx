'use client';

import type React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Plus, Paperclip, Settings, ArrowUp } from "lucide-react";
import { v4 } from 'uuid';

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    setIsLoading(true);
    try {
      // Generate UUID for this chat
      const chatId = v4();
      
      // Call FastAPI backend to start the agent
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/chat/${chatId}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input.trim() }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || "Failed to start chat");
      }

      router.push(`/chat/${chatId}`);
    } catch (error) {
      console.error("Error creating chat:", error);
      setIsLoading(false);
    }
  };

  const examplePrompts = [
    'Create a todo list app with dark mode',
    'Build an e-commerce product page',
    'Create a weather dashboard with charts',
    'Build a blog with comments section',
  ];

  return (
    <div className="min-h-screen w-full relative bg-black">
      <div
        className="absolute inset-0 z-0"
        style={{
          background: "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(226, 232, 240, 0.15), transparent 70%), #000000",
        }}
      />

      <nav className="relative z-20 border-b border-white/5 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="text-white font-semibold text-lg">WEB BUILDER</div>
          <div className="flex items-center gap-8">
            <div className="hidden md:flex gap-8 text-sm text-slate-400">
              <a href="#" className="hover:text-white transition">
                Pricing
              </a>
              <a href="#" className="hover:text-white transition">
                Product
              </a>
              <a href="#" className="hover:text-white transition">
                Docs
              </a>
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="text-white border-white/20 hover:bg-white/5 bg-transparent">
                Sign In
              </Button>
              <Button className="bg-white text-black hover:bg-slate-100">Sign Up</Button>
            </div>
          </div>
        </div>
      </nav>

      {/* Content */}
      <div className="relative z-10 min-h-[calc(100vh-60px)] flex flex-col items-center justify-center px-4">
        {/* Badge */}
        <div className="mb-8 flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
          <div className="w-2 h-2 rounded-full bg-green-400"></div>
          <span className="text-sm text-white">New - Try AI Agents</span>
          <span className="text-white/40">›</span>
        </div>

        {/* Logo/Title */}
        <div className="mb-12">
          <h1 className="text-5xl font-semibold text-white text-center tracking-tight">WEB BUILDER AI</h1>
        </div>

        <div className="w-full max-w-2xl">
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="bg-white/5 border border-white/10 rounded-2xl p-4 backdrop-blur-sm hover:border-white/20 transition-colors">
              <Input
                type="text"
                placeholder="Message Web Builder"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
                className="border-0 bg-transparent text-white placeholder:text-white/40 focus-visible:ring-0 text-lg"
              />

              <div className="flex items-center justify-between mt-4 pt-4 border-t border-white/5">
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-white/10 rounded-lg transition text-white/60 hover:text-white">
                    <Plus size={20} />
                  </button>
                  <button className="p-2 hover:bg-white/10 rounded-lg transition text-white/60 hover:text-white">
                    <Paperclip size={20} />
                  </button>
                  <select className="bg-transparent text-white text-sm px-2 py-1 hover:bg-white/10 rounded transition outline-none cursor-pointer">
                    <option>Select Models</option>
                    <option>GPT-4</option>
                    <option>Claude 3</option>
                    <option>Mistral</option>
                  </select>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-white/10 rounded-lg transition text-white/60 hover:text-white">
                    <Settings size={20} />
                  </button>
                  <Button
                    type="submit"
                    disabled={isLoading || !input.trim()}
                    size="icon"
                    className="rounded-lg w-8 h-8 bg-white text-black hover:bg-slate-100"
                  >
                    <ArrowUp size={18} />
                  </Button>
                </div>
              </div>
            </div>
          </form>

          <div className="mt-6 text-center">
            <p className="text-sm text-white/50">
              Get access to the best AI Agent. +30M users choose WEB BUILDER.
              <a href="#" className="text-blue-400 hover:text-blue-300 ml-2">
                Upgrade plan
              </a>
            </p>
          </div>
        </div>

        <div className="mt-32 px-4 py-4 rounded-2xl border border-white/10 bg-white/5 backdrop-blur-sm max-w-2xl w-full flex items-center justify-between">
          <div className="flex items-center gap-4">
            <div className="px-3 py-1 rounded-full bg-white text-black text-xs font-semibold">New</div>
            <span className="text-white text-sm">Advanced AI on Browser, CLI, Phone...</span>
          </div>
          <div className="flex gap-2">
            <Button variant="ghost" className="text-white/60 hover:bg-white/5">
              Close
            </Button>
            <Button className="bg-white text-black hover:bg-slate-100">Explore</Button>
          </div>
        </div>
      </div>
    </div>
  );
}
