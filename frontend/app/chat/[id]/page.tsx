'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams, useRouter } from 'next/navigation';
import { Loader2 } from "lucide-react";
import { WS_URL } from "@/lib/utils";
import apiClient from "@/api/client";
import { 
  ChatIdHeader, 
  MessageBubble, 
  ToolCallsDropdown, 
  PreviewPanel, 
  ChatInput 
} from "@/components/chat";
import { 
  consolidateMessages, 
  getAllToolCalls 
} from "@/lib/chat-utils";
import { 
  handleWebSocketMessage, 
  createWebSocketHandlers 
} from "@/lib/websocket-handlers";
import type { Message, ActiveToolCall } from "@/lib/chat-types";

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
  const [showAllToolsDropdown, setShowAllToolsDropdown] = useState(false);
  const [projectFiles, setProjectFiles] = useState<string[]>([]);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
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

  // Function to fetch project files
  const fetchProjectFiles = async () => {
    // Check if we're in a browser environment
    if (typeof window === 'undefined') {
      console.log('❌ Not in browser environment, skipping file fetch');
      return;
    }

    try {
      const token = localStorage.getItem("auth_token");
      if (!token) {
        console.log('No auth token available for fetching files');
        return;
      }

      console.log('📁 Fetching project files for:', chatId);
      
      const response = await apiClient.get<{
        project_id: string;
        files: string[];
        sandbox_id: string;
        sandbox_active: boolean;
      }>(`/projects/${chatId}/files`);
      
      console.log('✅ Files fetched successfully:', response.data.files?.length || 0, 'files');
      setProjectFiles(response.data.files || []);
    } catch (error) {
      console.error('❌ Error fetching files:', error);
      if (error instanceof Error) {
        console.error('Error message:', error.message);
      }
    }
  };

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

  // Fetch files when appUrl becomes available
  useEffect(() => {
    // Only run in browser environment
    if (typeof window === 'undefined') {
      console.log('⚠️ Not in browser, skipping file fetch setup');
      return;
    }

    if (appUrl && chatId) {
      // Delay initial fetch to ensure everything is ready
      const initialTimeout = setTimeout(() => {
        fetchProjectFiles();
      }, 1000);

      // Refetch files every 10 seconds while building
      const interval = setInterval(() => {
        if (isBuilding) {
          fetchProjectFiles();
        }
      }, 10000);
      
      return () => {
        clearTimeout(initialTimeout);
        clearInterval(interval);
      };
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [appUrl, isBuilding, chatId]);

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

  // WebSocket connection setup
  useEffect(() => {
    const connectWebSocket = () => {
      const token = localStorage.getItem("auth_token");
      
      if (!token) {
        console.log('No token available for WebSocket connection');
        return;
      }

      try {
        const wsUrl = `${WS_URL}/ws/${chatId}?token=${token}`;
        console.log('🔗 WebSocket URL being used:', wsUrl);
        const ws = new WebSocket(wsUrl);

        // Create handlers using utility
        const wsHandlers = createWebSocketHandlers(
          chatId,
          () => {
            setWsConnected(true);
            setError(null);
          },
          () => setWsConnected(false),
          () => setWsConnected(false),
          (event) => handleWebSocketMessage(event, {
            setCurrentTool,
            setIsBuilding,
            pollUrlUntilReady,
            setMessages,
            setAppUrl,
            setError,
            setUserData,
            consolidateMessages,
            currentTool,
          })
        );

        ws.onopen = wsHandlers.onopen;
        ws.onerror = wsHandlers.onerror;
        ws.onmessage = wsHandlers.onmessage;
        ws.onclose = wsHandlers.onclose;

        wsRef.current = ws;
      } catch (err) {
        console.log("failed")
        setWsConnected(false);
      }
    };

    connectWebSocket();

    return () => {
      // Cleanup WebSocket connection
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
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
        <ChatIdHeader
          userData={userData}
          showPreview={showPreview}
          onTogglePreview={() => setShowPreview(!showPreview)}
          onNewChat={() => router.push("/chat")}
          onBack={() => router.push("/chat")}
        />

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
                <MessageBubble
                  key={index}
                  message={msg}
                  isLastMessage={index === messages.length - 1}
                  currentTool={currentTool}
                />
              ))}
              
              <div ref={messagesEndRef} />
            </div>

            <ToolCallsDropdown
              toolCalls={getAllToolCalls(messages)}
              isExpanded={showAllToolsDropdown}
              onToggle={() => setShowAllToolsDropdown(!showAllToolsDropdown)}
            />

            <ChatInput
              input={input}
              wsConnected={wsConnected}
              isBuilding={isBuilding}
              onInputChange={setInput}
              onSubmit={handleSendMessage}
            />
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
            <PreviewPanel
              appUrl={appUrl}
              isCheckingUrl={isCheckingUrl}
              previewWidth={previewWidth}
              files={projectFiles}
              projectId={chatId}
            />
          )}
        </div>
      </div>
    </div>
  );
}
