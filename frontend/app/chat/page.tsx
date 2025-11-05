'use client';

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { v4 } from 'uuid';
import { authApi, chatApi, type UserData } from "@/api";
import { ChatNavbar, ChatInputBox, StatusBadge, PromotionBanner } from "@/components/chat";

export default function ChatPage() {
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [userData, setUserData] = useState<UserData | null>(null);
  const router = useRouter();

  useEffect(() => {
    // Check if user is authenticated
    const token = localStorage.getItem("auth_token");
    const user = localStorage.getItem("user_data");

    if (!token) {
      router.push("/signin");
      return;
    }

    setIsAuthenticated(true);

    if (user) {
      try {
        const parsed: UserData = JSON.parse(user);
        setUserData(parsed);
        
        // Fetch fresh user data from API to get updated token count
        authApi.getCurrentUser()
          .then(freshData => {
            console.log('🔄 Refreshed user data:', freshData);
            const updatedUser = { ...parsed, ...freshData };
            localStorage.setItem("user_data", JSON.stringify(updatedUser));
            setUserData(updatedUser);
          })
          .catch(err => {
            console.error('Failed to fetch fresh user data:', err);
          });
      } catch (err) {
        console.warn("Invalid user_data in localStorage, clearing.", err);
        localStorage.removeItem("user_data");
        // Don't clear token here as it might still be valid
      }
    }
  }, [router]);

  const handleSignOut = () => {
    localStorage.removeItem("auth_token");
    localStorage.removeItem("user_data");
    setIsAuthenticated(false);
    setUserData(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const token = localStorage.getItem("auth_token");
    if (!token) {
      router.push("/signin");
      return;
    }

    setIsLoading(true);
    try {
      const chatId = v4();
      
      // Call the createChat API with the user's prompt
      await chatApi.createChat(chatId, input.trim());

      router.push(`/chat/${chatId}`);
    } catch (error: unknown) {
      console.error("Error creating chat:", error);
      alert(error instanceof Error ? error.message : "Failed to create chat");
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen w-full relative bg-black">
      <div
        className="absolute inset-0 z-0"
        style={{
          background: "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(226, 232, 240, 0.15), transparent 70%), #000000",
        }}
      />

      <ChatNavbar 
        isAuthenticated={isAuthenticated}
        userData={userData}
        onSignOut={handleSignOut}
      />

      <div className="relative z-10 min-h-[calc(100vh-60px)] flex flex-col items-center justify-center px-4">
        <StatusBadge />

        <div className="mb-12">
          <h1 className="text-5xl font-semibold text-white text-center tracking-tight">WEB BUILDER AI</h1>
        </div>

        <div className="w-full max-w-2xl">
          <ChatInputBox 
            input={input}
            isLoading={isLoading}
            onInputChange={setInput}
            onSubmit={handleSubmit}
          />

          <div className="mt-6 text-center">
            <p className="text-sm text-white/50">
              Get access to the best AI Agent. +30M users choose WEB BUILDER.
              <a href="#" className="text-blue-400 hover:text-blue-300 ml-2">
                Upgrade plan
              </a>
            </p>
          </div>
        </div>

        <PromotionBanner />
      </div>
    </div>
  );
}
