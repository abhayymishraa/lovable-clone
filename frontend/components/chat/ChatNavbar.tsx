import { Button } from "@/components/ui/button";
import Link from "next/link";
import type { UserData } from "@/api";

interface ChatNavbarProps {
  isAuthenticated: boolean;
  userData: UserData | null;
  onSignOut: () => void;
}

export function ChatNavbar({ isAuthenticated, userData, onSignOut }: ChatNavbarProps) {
  return (
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
            {isAuthenticated ? (
              <>
                <div className="hidden md:flex items-center gap-2 px-3 py-2 rounded-lg bg-white/5 border border-white/10">
                  <span className="text-sm text-white/60">{userData?.email}</span>
                  <span className="text-xs text-white/40">•</span>
                  <span className="text-sm text-white font-medium">{userData?.tokens_remaining} tokens</span>
                </div>
                <Button 
                  variant="outline" 
                  className="text-white border-white/20 hover:bg-white/5 bg-transparent"
                  onClick={onSignOut}
                >
                  Sign Out
                </Button>
              </>
            ) : (
              <>
                <Link href="/signin">
                  <Button variant="outline" className="text-white border-white/20 hover:bg-white/5 bg-transparent">
                    Sign In
                  </Button>
                </Link>
                <Link href="/signup">
                  <Button className="bg-white text-black hover:bg-slate-100">Sign Up</Button>
                </Link>
              </>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
