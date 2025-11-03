'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ArrowUp, Plus, Paperclip, ChevronLeft, Loader2, Eye, EyeOff, ChevronDown } from "lucide-react";
import { WS_URL, API_URL } from "@/lib/utils";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  created_at: string;
  event_type?: string;
  url?: string;
  status?: 'thinking' | 'processing' | 'done';
}

interface ActiveToolCall {
  name: string;
  status: 'running' | 'completed';
  output?: string;
}

interface ChatInfo {
  id: string;
  title: string;
  app_url: string | null;
  created_at: string;
}

type WebSocketMessage = {
  type?: string;
  e?: string;
  message?: string;
  url?: string;
  messages?: Message[];
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
  const [userData, setUserData] = useState<any>(null);
  const [currentTool, setCurrentTool] = useState<ActiveToolCall | null>(null);
  const [isCheckingUrl, setIsCheckingUrl] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const connectAttemptedRef = useRef(false);
  const urlCheckIntervalRef = useRef<NodeJS.Timeout | null>(null);

  // Check authentication and load initial data
  useEffect(() => {
    const loadInitialData = async () => {
      const user = localStorage.getItem("user_data");
      
      if (user) {
        try {
          setUserData(JSON.parse(user));
        } catch (err) {
          console.error('Failed to parse user data:', err);
        }
      }
      
      setIsLoading(false);
    };

    loadInitialData();
  }, []);

  // Function to check if URL is ready
  const checkUrlReady = async (url: string): Promise<boolean> => {
    try {
      const response = await fetch(url, { 
        method: 'HEAD',
        mode: 'no-cors' // This will prevent CORS errors
      });
      // With no-cors, we can't read the status, but if it doesn't throw, it's accessible
      return true;
    } catch (error) {
      console.log('URL not ready yet:', error);
      return false;
    }
  };

  // Poll URL until it's ready
  const pollUrlUntilReady = async (url: string) => {
    setIsCheckingUrl(true);
    console.log('🔍 Starting URL health check for:', url);
    
    let attempts = 0;
    const maxAttempts = 20; // 20 attempts over ~20 seconds
    
    const checkInterval = setInterval(async () => {
      attempts++;
      console.log(`⏱️ Health check attempt ${attempts}/${maxAttempts}`);
      
      const isReady = await checkUrlReady(url);
      
      if (isReady || attempts >= maxAttempts) {
        clearInterval(checkInterval);
        setIsCheckingUrl(false);
        
        if (isReady) {
          console.log('✅ URL is ready, setting iframe');
          setAppUrl(url);
        } else {
          console.log('⚠️ Max attempts reached, setting iframe anyway');
          setAppUrl(url);
        }
      }
    }, 1000); // Check every 1 second
    
    urlCheckIntervalRef.current = checkInterval;
  };

  // Cleanup interval on unmount
  useEffect(() => {
    return () => {
      if (urlCheckIntervalRef.current) {
        clearInterval(urlCheckIntervalRef.current);
      }
    };
  }, []);

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

  // Removed the separate loadMessages effect since it's now handled in the auth check

  useEffect(() => {
    // WebSocket connection setup - only connect once per chatId
    const connectWebSocket = () => {
      const token = localStorage.getItem("auth_token");
      
      if (!token) {
        console.log('No token available for WebSocket connection');
        return;
      }

      try {
        // Include token as query parameter
        const wsUrl = `${WS_URL}/ws/${chatId}?token=${token}`;
        console.log('🔗 WebSocket URL being used:', wsUrl);
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
          console.log('✅ WebSocket connected for chat:', chatId);
          setWsConnected(true);
          setError(null);
        };

        ws.onerror = (error) => {
          console.error('❌ WebSocket error:', error);
          setWsConnected(false);
        };

        ws.onmessage = (event) => {
          try {
            const data: WebSocketMessage = JSON.parse(event.data);
            console.log('📨 Received WebSocket message:', data);
            
            // Handle tool start events - show temporary tool card (don't update message content)
            if (data.e === 'tool_started') {
              const toolName = data.tool_name || 'Unknown Tool';
              setCurrentTool({
                name: toolName,
                status: 'running',
              });
              return; // Don't add to message content
            }
            
            // Handle tool end events - show output briefly then hide
            if (data.e === 'tool_completed') {
              const toolName = data.tool_name || currentTool?.name || 'Tool';
              const toolOutput = data.tool_output || 'Completed';
              
              // Show completion status briefly
              setCurrentTool({
                name: toolName,
                status: 'completed',
                output: typeof toolOutput === 'string' 
                  ? toolOutput.substring(0, 200) 
                  : JSON.stringify(toolOutput).substring(0, 200),
              });
              
              // Hide after 2 seconds
              setTimeout(() => {
                setCurrentTool(null);
              }, 2000);
              
              return; // Don't add to message content
            }
            
            // Check if building has started
            if (data.e === 'builder_started' || data.e === 'workflow_started') {
              setIsBuilding(true);
            }
            
            // Check if app URL is received - start health check before setting iframe
            if (data.url) {
              setIsBuilding(false);
              pollUrlUntilReady(data.url); // Check URL health before displaying
            }
            
            // Check if workflow completed
            if (data.e === 'workflow_completed') {
              setIsBuilding(false);
              setCurrentTool(null); // Clear any remaining tool
              
              // Refresh user data to update token count
              const updatedUser = localStorage.getItem("user_data");
              if (updatedUser) {
                setUserData(JSON.parse(updatedUser));
              }
            }
            
            // Handle initial message history
            if (data.type === 'history' && data.messages) {
              console.log('📜 Received message history:', data.messages.length, 'messages');
              setMessages(data.messages);
              return;
            }
            
            if (data.type === 'error' || data.e === 'error') {
              setError(data.message || 'An error occurred');
            }
            
            // Handle token status updates
            if (data.tokens_remaining !== undefined) {
              const user = JSON.parse(localStorage.getItem("user_data") || '{}');
              user.tokens_remaining = data.tokens_remaining;
              localStorage.setItem("user_data", JSON.stringify(user));
              setUserData(user);
            }
            
            // Handle ONLY thinking content - ignore other events
            if (data.e === 'thinking' && data.message) {
              setMessages(prev => {
                if (prev.length === 0) {
                  // Create new assistant message
                  return [...prev, {
                    id: Date.now().toString() + '-assistant',
                    role: 'assistant',
                    content: data.message || '',
                    created_at: new Date().toISOString(),
                    event_type: data.e,
                    status: 'thinking',
                  }];
                }
                
                const lastMsg = prev[prev.length - 1];
                if (lastMsg.role === 'assistant') {
                  // Append thinking to existing message
                  return [
                    ...prev.slice(0, -1),
                    {
                      ...lastMsg,
                      content: lastMsg.content + '\n' + (data.message || ''),
                    }
                  ];
                }
                
                // Create new message
                return [...prev, {
                  id: Date.now().toString() + '-assistant',
                  role: 'assistant',
                  content: data.message || '',
                  created_at: new Date().toISOString(),
                  event_type: data.e,
                  status: 'thinking',
                }];
              });
              return;
            }
          } catch (err) {
            console.error('Failed to parse WebSocket message:', err);
          }
        };

        ws.onclose = (event) => {
          console.log('⛔ WebSocket disconnected, code:', event.code, 'reason:', event.reason);
          setWsConnected(false);
        };

        wsRef.current = ws;
      } catch (err) {
        console.error('❌ Failed to create WebSocket:', err);
        setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      // Don't close on unmount - this was causing premature disconnection
      // The server will handle cleanup
    };
  }, [chatId]);

  const handleSendMessage = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !wsRef.current || isBuilding) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      created_at: new Date().toISOString(),
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
              onClick={() => router.push("/chat")}
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
                onClick={() => setShowPreview(!showPreview)}
                className="text-white/60 hover:text-white hover:bg-white/5 hidden md:flex"
              >
                {showPreview ? <Eye size={20} /> : <EyeOff size={20} />}
              </Button>
              <Button 
                className="bg-white text-black hover:bg-slate-100 text-sm font-sans"
                onClick={() => router.push("/chat")}
              >
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
              {isLoading ? (
                <div className="flex items-center justify-center h-full">
                  <div className="flex items-center gap-2 text-white/60">
                    <Loader2 className="w-5 h-5 animate-spin" />
                    <span>Loading messages...</span>
                  </div>
                </div>
              ) : error ? (
                <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg text-sm">
                  {error}
                </div>
              ) : null}
              
              {messages.map((msg, index) => (
                <div 
                  key={index}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {msg.role === 'user' ? (
                    // User message
                    <div className="max-w-xl px-4 py-3 rounded-lg bg-white text-black">
                      <p className="text-sm">{msg.content}</p>
                    </div>
                  ) : (
                    // Assistant message - single response card with tool section at bottom
                    <div className="max-w-2xl w-full bg-white/5 text-white border border-white/10 rounded-lg p-4">
                      <div className="flex items-start gap-3">
                        <span className="text-lg shrink-0 mt-0.5">⚡</span>
                        <div className="flex-1">
                          {/* Main thinking/response - each line separated */}
                          <div className="text-sm leading-relaxed space-y-2">
                            {msg.content.split('\n').filter(line => line.trim()).map((line, i) => (
                              <p key={i}>{line}</p>
                            ))}
                          </div>
                          
                          {/* Tool Call Section - only shows when tool is active */}
                          {currentTool && index === messages.length - 1 && (
                            <div className="mt-4 pt-3 border-t border-white/10">
                              <div className="bg-black/40 border border-amber-500/30 rounded-lg p-3">
                                <div className="flex items-start gap-2">
                                  {currentTool.status === 'running' ? (
                                    <Loader2 size={14} className="animate-spin text-amber-400 mt-0.5" />
                                  ) : (
                                    <span className="text-green-400 text-sm">✓</span>
                                  )}
                                  <div className="flex-1">
                                    <p className="text-xs font-mono text-amber-300 mb-1">
                                      🔧 {currentTool.name}
                                    </p>
                                    {currentTool.status === 'running' ? (
                                      <p className="text-xs text-white/50">Processing...</p>
                                    ) : (
                                      currentTool.output && (
                                        <div className="text-xs text-white/60 bg-black/30 rounded p-2 mt-1 font-mono max-h-32 overflow-y-auto">
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
                  )}
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
                {isCheckingUrl ? (
                  <div className="w-full h-full rounded-lg border border-white/10 flex items-center justify-center">
                    <div className="text-center">
                      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-white/60 mx-auto mb-4" />
                      <p className="text-white/60 font-sans">Checking if app is ready...</p>
                    </div>
                  </div>
                ) : appUrl ? (
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
