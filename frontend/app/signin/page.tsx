"use client";

import type React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { authApi } from "@/api";

export default function SignInPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      // Call the login API
      const data = await authApi.login({ email, password });

      // Validate response data
      if (!data.access_token) {
        throw new Error("No access token received");
      }

      // Store token in localStorage
      localStorage.setItem("auth_token", data.access_token);

      // Fetch user data after login since login doesn't return it
      try {
        const userData = await authApi.getCurrentUser();
        localStorage.setItem("user_data", JSON.stringify(userData));
      } catch (err) {
        console.warn("Failed to fetch user data after login:", err);
        // Continue anyway, user data will be fetched on chat page
      }

      // Verify token was stored before redirect
      const storedToken = localStorage.getItem("auth_token");
      if (!storedToken) {
        throw new Error("Failed to store authentication token");
      }

      setIsLoading(false);
      router.push("/chat");
    } catch (error: unknown) {
      console.error("Error signing in:", error);
      setError(error instanceof Error ? error.message : "Failed to sign in");
      setIsLoading(false);
      // Clear any partial data on error
      localStorage.removeItem("auth_token");
      localStorage.removeItem("user_data");
    }
  };

  return (
    <div className="min-h-screen w-full relative bg-black">
      <div
        className="absolute inset-0 z-0"
        style={{
          background:
            "radial-gradient(ellipse 80% 60% at 50% 0%, rgba(226, 232, 240, 0.15), transparent 70%), #000000",
        }}
      />

      <nav className="relative z-20 border-b border-white/5 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <Link
            href="/chat"
            className="text-white font-semibold text-lg hover:opacity-80 transition"
          >
            WEB BUILDER
          </Link>
          <div className="flex items-center gap-2">
            <Link href="/signup">
              <Button className="bg-white text-black hover:bg-slate-100">
                Sign Up
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="relative z-10 min-h-[calc(100vh-60px)] flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-4xl font-semibold text-white mb-2">
              Welcome back
            </h1>
            <p className="text-white/60">Sign in to your account to continue</p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur-sm">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label
                  htmlFor="email"
                  className="block text-sm text-white/80 mb-2"
                >
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  disabled={isLoading}
                  className="w-full bg-white/5 border-white/10 text-white placeholder:text-white/40 focus-visible:ring-1 focus-visible:ring-white/20"
                />
              </div>

              <div>
                <label
                  htmlFor="password"
                  className="block text-sm text-white/80 mb-2"
                >
                  Password
                </label>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  minLength={6}
                  disabled={isLoading}
                  className="w-full bg-white/5 border-white/10 text-white placeholder:text-white/40 focus-visible:ring-1 focus-visible:ring-white/20"
                />
              </div>

              {error && (
                <div className="text-sm text-red-400 bg-red-400/10 border border-red-400/20 rounded-lg p-3">
                  {error}
                </div>
              )}

              <Button
                type="submit"
                disabled={isLoading}
                className="w-full bg-white text-black hover:bg-slate-100 font-medium h-12"
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Signing In...
                  </>
                ) : (
                  "Sign In"
                )}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-white/60">
              Don't have an account?{" "}
              <Link
                href="/signup"
                className="text-white hover:underline font-medium"
              >
                Sign Up
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
