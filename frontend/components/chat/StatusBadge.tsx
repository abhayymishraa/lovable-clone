export function StatusBadge() {
  return (
    <div className="mb-8 flex items-center gap-2 px-4 py-2 rounded-full border border-white/10 bg-white/5 backdrop-blur-sm">
      <div className="w-2 h-2 rounded-full bg-green-400"></div>
      <span className="text-sm text-white">New - Try AI Agents</span>
      <span className="text-white/40">›</span>
    </div>
  );
}
