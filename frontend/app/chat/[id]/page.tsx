'use client';

import { useEffect, useState, useRef } from 'react';
import { useParams } from 'next/navigation';

type WebSocketMessage = {
  e: string;
  message?: string;
  url?: string;
  [key: string]: any;
};

export default function ChatIdPage() {
  const params = useParams();
  const chatId = params.id as string;
  
  const [wsConnected, setWsConnected] = useState(false);
  const [messages, setMessages] = useState<WebSocketMessage[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [appUrl, setAppUrl] = useState<string | null>(null);
  const [isBuilding, setIsBuilding] = useState(false);
  
  const wsRef = useRef<WebSocket | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
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
        const wsUrl = `ws://localhost:8000/ws/${chatId}`;
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
            
            setMessages((prev) => [...prev, data]);
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

  const handleSendPrompt = (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || !wsRef.current || isBuilding) return;
    
    // Send message through WebSocket
    const message = {
      type: 'chat_message',
      prompt: prompt.trim()
    };
    wsRef.current.send(JSON.stringify(message));

    // Add user message to chat
    setMessages((prev) => [
      ...prev,
      {
        e: 'user_message',
        message: prompt,
        timestamp: new Date().toLocaleTimeString(),
      },
    ]);
    
    setPrompt('');
    setIsBuilding(true); // Immediately show building state
  };

  return (
    <div className="flex h-screen bg-gray-50">
      {/* Left Sidebar - Chat Interface (30%) */}
      <div className="w-3/10 bg-white border-r border-gray-200 flex flex-col">
        {/* Header */}
        <div className="border-b border-gray-200 px-6 py-4">
          <h1 className="text-xl font-semibold text-gray-900">Build</h1>
          <p className="text-xs text-gray-500 mt-1">ID: {chatId.slice(0, 8)}...</p>
        </div>

        {/* Connection Status */}
        <div className="px-6 py-3 bg-gray-50 border-b border-gray-200">
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-yellow-500'}`}></div>
            <span className="text-xs text-gray-600">
              {wsConnected ? 'Connected to backend' : 'Connecting...'}
            </span>
          </div>
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {isLoading ? (
            <div className="flex items-center justify-center h-full">
              <div className="text-center">
                <div className="w-8 h-8 text-blue-600 animate-spin mx-auto mb-2 border-4 border-blue-200 border-t-blue-600 rounded-full"></div>
                <p className="text-sm text-gray-600">Loading chat...</p>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div className="flex items-center justify-center h-full text-center">
              <div>
                <div className="w-12 h-12 text-gray-300 mx-auto mb-2">✨</div>
                <p className="text-sm text-gray-600 mb-1">No messages yet</p>
                <p className="text-xs text-gray-400">Your build progress will appear here</p>
              </div>
            </div>
          ) : (
            messages.map((msg, index) => (
              <div 
                key={index}
                className={`flex ${msg.e === 'user_message' ? 'justify-end' : 'justify-start'}`}
              >
                <div 
                  className={`max-w-xs px-4 py-3 rounded-lg ${
                    msg.e === 'user_message'
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-100 text-gray-900'
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {msg.e !== 'user_message' && (
                      <span className="text-lg flex-shrink-0 mt-0.5">⚡</span>
                    )}
                    <div className="flex-1">
                      {msg.message && (
                        <p className="text-sm">{msg.message}</p>
                      )}
                      {msg.e && msg.e !== 'user_message' && (
                        <p className="text-xs opacity-75 mt-1">{msg.e}</p>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Error Display */}
        {error && (
          <div className="mx-4 mb-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
            {error}
          </div>
        )}

        {/* Input Area */}
        <div className="border-t border-gray-200 p-4">
          <form onSubmit={handleSendPrompt} className="flex gap-2">
            <input
              type="text"
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Ask for changes..."
              className="flex-1 px-3 py-2 border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-sm"
              disabled={!wsConnected}
            />
            <button
              type="submit"
              disabled={!wsConnected || !prompt.trim()}
              className="p-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
            >
              ➤
            </button>
          </form>
        </div>
      </div>

      {/* Right Preview Panel (70%) */}
      <div className="flex-1 bg-gradient-to-br from-gray-50 to-white flex flex-col">
        {/* Preview Header */}
        <div className="border-b border-gray-200 px-8 py-6 bg-white">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-2xl font-bold text-gray-900">Preview</h2>
              <p className="text-sm text-gray-600 mt-1">Live preview of your application</p>
            </div>
            <div className="flex items-center gap-3">
              <button className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors">
                Refresh
              </button>
              <button className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors">
                Export
              </button>
            </div>
          </div>
        </div>

        {/* Preview Content */}
        <div className="flex-1 p-8 overflow-auto">
          {isBuilding || (!appUrl && messages.length === 0) ? (
            // Loading/Building State
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 h-full p-8 flex flex-col items-center justify-center">
              <div className="text-center">
                {/* Sandbox Loading Animation */}
                <div className="mb-6">
                  <div className="w-16 h-16 mx-auto mb-4 relative">
                    <div className="absolute inset-0 bg-gradient-to-r from-blue-400 to-purple-500 rounded-lg animate-pulse"></div>
                    <div className="absolute inset-1 bg-white rounded-lg"></div>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <div className="w-8 h-8 border-4 border-blue-200 border-t-blue-600 rounded-full animate-spin"></div>
                    </div>
                  </div>
                </div>

                <h3 className="text-xl font-semibold text-gray-900 mb-2">
                  {isBuilding ? 'Building Your App' : 'Initializing Sandbox'}
                </h3>
                <p className="text-gray-600 mb-6">
                  {isBuilding 
                    ? 'Creating your application in the sandbox...' 
                    : 'Waiting for build to start...'}
                </p>

                {/* Progress Steps */}
                <div className="space-y-3 text-left max-w-sm mx-auto">
                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                      messages.some(m => m.e === 'planner_complete') 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-gray-200 text-gray-600'
                    }`}>
                      {messages.some(m => m.e === 'planner_complete') ? '✓' : '1'}
                    </div>
                    <span className="text-sm text-gray-700">Planning</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                      messages.some(m => m.e === 'builder_complete') 
                        ? 'bg-green-100 text-green-700' 
                        : messages.some(m => m.e === 'builder_started')
                        ? 'bg-blue-100 text-blue-700 animate-pulse'
                        : 'bg-gray-200 text-gray-600'
                    }`}>
                      {messages.some(m => m.e === 'builder_complete') ? '✓' : '2'}
                    </div>
                    <span className="text-sm text-gray-700">Building</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                      messages.some(m => m.e === 'code_validator_complete') 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-gray-200 text-gray-600'
                    }`}>
                      {messages.some(m => m.e === 'code_validator_complete') ? '✓' : '3'}
                    </div>
                    <span className="text-sm text-gray-700">Validating</span>
                  </div>

                  <div className="flex items-center gap-3">
                    <div className={`w-6 h-6 rounded-full flex items-center justify-center text-sm font-medium ${
                      appUrl 
                        ? 'bg-green-100 text-green-700' 
                        : 'bg-gray-200 text-gray-600'
                    }`}>
                      {appUrl ? '✓' : '4'}
                    </div>
                    <span className="text-sm text-gray-700">Launching</span>
                  </div>
                </div>

                <p className="text-xs text-gray-500 mt-6">
                  This usually takes 1-2 minutes
                </p>
              </div>
            </div>
          ) : appUrl ? (
            // App Loaded - Show iframe
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 h-full overflow-hidden">
              <iframe
                src={appUrl}
                title="Generated App Preview"
                className="w-full h-full border-0"
                sandbox="allow-same-origin allow-scripts allow-forms allow-popups allow-modals"
              />
            </div>
          ) : (
            // No URL yet - Show placeholder
            <div className="bg-white rounded-xl shadow-lg border border-gray-200 h-full p-8 flex flex-col items-center justify-center">
              <div className="text-center">
                <div className="w-12 h-12 text-gray-300 mx-auto mb-4">📱</div>
                <h3 className="text-lg font-semibold text-gray-900 mb-2">
                  No Preview Available
                </h3>
                <p className="text-gray-600">
                  Send a prompt in the chat to generate an app
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Preview Footer */}
        <div className="border-t border-gray-200 bg-white px-8 py-4 text-xs text-gray-500 text-center">
          Preview updates in real-time as your app is built
        </div>
      </div>
    </div>
  );
}
