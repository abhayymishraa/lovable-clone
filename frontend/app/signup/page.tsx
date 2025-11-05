"use client";

import type React from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Loader2 } from "lucide-react";
import Link from "next/link";
import { authApi } from "@/api";

export default function SignUpPage() {
  const [name, setName] = useState("");
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
      // Call the register API
      const data = await authApi.register({ name, email, password });

      // Validate response data
      if (!data.access_token || !data.user) {
        console.error("Invalid response:", data);
        throw new Error("Invalid response from server");
      }

      // Store token in localStorage
      localStorage.setItem("auth_token", data.access_token);

      // Store user data
      localStorage.setItem("user_data", JSON.stringify(data.user));

      // Verify token was stored before redirect
      const storedToken = localStorage.getItem("auth_token");
      if (!storedToken) {
        throw new Error("Failed to store authentication token");
      }

      setIsLoading(false);
      router.push("/chat");
    } catch (error: unknown) {
      console.error("Error signing up:", error);
      const errorMessage =
        error instanceof Error ? error.message : "Failed to sign up";

      // Handle specific error messages
      if (errorMessage.includes("Email already registered")) {
        setError("This email is already registered. Please sign in instead.");
      } else {
        setError(errorMessage);
      }

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
            <Link href="/signin">
              <Button
                variant="outline"
                className="text-white border-white/20 hover:bg-white/5 bg-transparent"
              >
                Sign In
              </Button>
            </Link>
          </div>
        </div>
      </nav>

      <div className="relative z-10 min-h-[calc(100vh-60px)] flex flex-col items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="mb-8 text-center">
            <h1 className="text-4xl font-semibold text-white mb-2">
              Create your account
            </h1>
            <p className="text-white/60">Sign up to start building with AI</p>
          </div>

          <div className="bg-white/5 border border-white/10 rounded-2xl p-8 backdrop-blur-sm">
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label
                  htmlFor="name"
                  className="block text-sm text-white/80 mb-2"
                >
                  Name
                </label>
                <Input
                  id="name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Your name"
                  required
                  disabled={isLoading}
                  className="w-full bg-white/5 border-white/10 text-white placeholder:text-white/40 focus-visible:ring-1 focus-visible:ring-white/20"
                />
              </div>

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
                <p className="text-xs text-white/40 mt-1">
                  Minimum 6 characters
                </p>
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
                    Creating Account...
                  </>
                ) : (
                  "Sign Up"
                )}
              </Button>
            </form>

            <div className="mt-6 text-center text-sm text-white/60">
              Already have an account?{" "}
              <Link
                href="/signin"
                className="text-white hover:underline font-medium"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
