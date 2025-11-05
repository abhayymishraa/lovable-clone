import { Button } from "@/components/ui/button";

export function PromotionBanner() {
  return (
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
  );
}
