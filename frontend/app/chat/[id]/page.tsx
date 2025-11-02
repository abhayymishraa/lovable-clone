'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowUp, Plus, Paperclip, ChevronLeft, Loader2, Eye, EyeOff } from "lucide-react";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  e?: string;
  url?: string;
}

type WebSocketMessage = {
  e: string;
  message?: string;
  url?: string;
  [key: string]: any;
};

export default function ChatIdPage() {
  const params = useParams();
  const router = useRouter();
  const chatId = params.id as string;
  
  const [wsConnected, setWsConnected] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [appUrl, setAppUrl] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  const [previewWidth, setPreviewWidth] = useState(50);
  const [isDragging, setIsDragging] = useState(false);
  const [showPreview, setShowPreview] = useState(true);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle drag resize
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!isDragging || !containerRef.current) return;

      const container = containerRef.current;
      const rect = container.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const chatWidth = (mouseX / rect.width) * 100;
      const newPreviewWidth = 100 - chatWidth;

      if (chatWidth > 20 && chatWidth < 70) {
        setPreviewWidth(newPreviewWidth);
      }
    };

    const handleMouseUp = () => {
      setIsDragging(false);
    };

    if (isDragging) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);

      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isDragging]);

  useEffect(() => {
    // Save messages to localStorage
    localStorage.setItem(`chat_messages_${chatId}`, JSON.stringify(messages));
  }, [messages, chatId]);

  // Save appUrl to localStorage when it changes
  // Save appUrl and building state to localStorage when they change
  useEffect(() => {
    if (appUrl) {
      localStorage.setItem(`app_url_${chatId}`, appUrl);
    }
    localStorage.setItem(`is_building_${chatId}`, JSON.stringify(isBuilding));
  }, [appUrl, isBuilding, chatId]);

  // Load saved messages and app URL from localStorage
  useEffect(() => {
    const savedMessages = localStorage.getItem(`chat_messages_${chatId}`);
    const savedAppUrl = localStorage.getItem(`app_url_${chatId}`);
    
    if (savedMessages) {
      setMessages(JSON.parse(savedMessages));
    }
    
    if (savedAppUrl) {
      setAppUrl(savedAppUrl);
    }

    // Restore building state
    const savedBuildingState = localStorage.getItem(`is_building_${chatId}`);
    if (savedBuildingState) {
      setIsBuilding(JSON.parse(savedBuildingState));
    }
    
    // Simulate initial loading
    const timer = setTimeout(() => {
      setIsLoading(false);
    }, 500);

    return () => clearTimeout(timer);
  }, [chatId]);

  useEffect(() => {
    // WebSocket connection setup
    const connectWebSocket = () => {
      try {
        const wsUrl = `${process.env.NEXT_PUBLIC_WS_URL}/ws/${chatId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('WebSocket connected for chat:', chatId);
          setWsConnected(true);
          setError(null);
        };

        ws.onmessage = (event) => {
          try {
            const data: WebSocketMessage = JSON.parse(event.data);
            console.log('Received message:', data);
            
            // Check if building has started
            if (data.e === 'builder_started' || data.e === 'workflow_started') {
              setIsBuilding(true);
            }
            
            // Check if app URL is received
            if (data.url) {
              setAppUrl(data.url);
              setIsBuilding(false);
            }
            
            // Check if workflow completed
            if (data.e === 'workflow_completed') {
              setIsBuilding(false);
            }
            
            // Convert WebSocketMessage to Message
            const newMessage: Message = {
              id: Date.now().toString() + '-assistant',
              role: 'assistant',
              content: data.message || '',
              timestamp: new Date(),
              e: data.e,
              url: data.url
            };
            
            setMessages((prev) => [...prev, newMessage]);
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };
        ws.onclose = () => {
          console.log('WebSocket disconnected');
          setWsConnected(false);
          
          setTimeout(() => {
            console.log('Attempting to reconnect...');
            connectWebSocket();
          }, 3000);
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('Failed to create WebSocket:', err);
        setError('Failed to create WebSocket connection');
      }
    };

    connectWebSocket();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
    };
  }, [chatId]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || isBuilding) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      timestamp: new Date(),
    };

    // Send message through WebSocket
    const message = {
      type: 'chat_message',
      prompt: input.trim()
    };
    wsRef.current.send(JSON.stringify(message));

    // Add user message to chat
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsBuilding(true); // Immediately show building state
  };

  return (
    <div className="min-h-screen w-full bg-black relative overflow-hidden" ref={containerRef}>
      <div
        className="absolute inset-0 z-0 pointer-events-none"
        style={{
          background:
            "radial-gradient(ellipse 50% 100% at 10% 0%, rgba(226, 232, 240, 0.15), transparent 65%), #000000",
        }}
      />
      
      <div className="relative z-10 h-screen flex flex-col">
        {/* Header */}
        <div className="border-b border-white/5 backdrop-blur-md px-4 py-4">
          <div className="flex items-center justify-between">
            <Button
              variant="ghost"
              size="icon"
              onClick={() => router.push("/")}
              className="text-white/60 hover:text-white hover:bg-white/5 font-sans"
            >
              <ChevronLeft size={24} />
            </Button>
            <h1 className="font-mono font-semibold tracking-tight text-white">WEB BUILDER AI</h1>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowPreview(!showPreview)}
                className="text-white/60 hover:text-white hover:bg-white/5 hidden md:flex"
              >
                {showPreview ? <Eye size={20} /> : <EyeOff size={20} />}
              </Button>
              <Button className="bg-white text-black hover:bg-slate-100 text-sm font-sans">
                New Chat
              </Button>
            </div>
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden">
          {/* Chat Panel */}
          <div
            className="flex flex-col border-r border-white/5"
            style={{
              width: showPreview ? `${100 - previewWidth}%` : "100%",
              transition: isDragging ? "none" : "width 0.3s ease-out",
            }}
          >
            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.map((msg, index) => (
                <div 
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div 
                    className={`max-w-xs px-4 py-3 rounded-lg ${
                      msg.role === 'user'
                        ? 'bg-white text-black'
                        : 'bg-white/5 text-white border border-white/10'
                    }`}
                  >
                    <div className="flex items-start gap-2">
                      {msg.role !== 'user' && (
                        <span className="text-lg shrink-0 mt-0.5">⚡</span>
                      )}
                      <div className="flex-1 font-sans">
                        {msg.content && (
                          <p className="text-sm">{msg.content}</p>
                        )}
                        {msg.e && msg.role !== 'user' && (
                          <p className="text-xs opacity-75 mt-1 font-mono">{msg.e}</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>

            {/* Input Area */}
            <div className="border-t border-white/5 bg-black/40 backdrop-blur-md p-4">
              <form onSubmit={handleSendMessage}>
                <div className="bg-white/5 border border-white/10 rounded-lg p-3 hover:border-white/20 transition-colors">
                  <div className="flex gap-3">
                    <Input
                      type="text"
                      value={input}
                      onChange={(e) => setInput(e.target.value)}
                      placeholder="Type your message..."
                      className="flex-1 border-0 bg-transparent text-white font-sans placeholder:text-white/40 focus-visible:ring-0"
                      disabled={!wsConnected || isBuilding}
                    />
                    <div className="flex items-center gap-1">
                      <button type="button" className="p-2 hover:bg-white/10 rounded transition text-white/60 hover:text-white">
                        <Plus size={18} />
                      </button>
                      <button type="button" className="p-2 hover:bg-white/10 rounded transition text-white/60 hover:text-white">
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
          </div>

          {/* Divider */}
          {showPreview && (
            <div
              className="w-1 bg-white/5 hover:bg-white/20 cursor-col-resize transition-colors"
              onMouseDown={() => setIsDragging(true)}
              style={{ userSelect: "none" }}
            />
          )}

          {/* Preview Area */}
          {showPreview && (
            <div 
              className="flex flex-col bg-black/50 border-l border-white/5"
              style={{
                width: `${previewWidth}%`,
              }}
            >
              <div className="flex-1 p-6">
                {appUrl ? (
                  <div className="w-full h-full rounded-lg overflow-hidden border border-white/10">
                    <iframe
                      src={appUrl}
                      title="App Preview"
                      className="w-full h-full"
                      sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
                    />
                  </div>
                ) : (
                  <div className="w-full h-full rounded-lg border border-white/10 flex items-center justify-center">
                    <div className="text-center">
                      <Eye className="w-12 h-12 text-white/20 mx-auto mb-4" />
                      <p className="text-white/60 font-sans">Preview will appear here</p>
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
