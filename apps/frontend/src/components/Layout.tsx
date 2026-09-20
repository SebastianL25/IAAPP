import type { ReactNode } from "react";
import { Link } from "react-router-dom";

export default function Layout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex flex-col">
      <header className="h-14 flex items-center px-4 border-b border-surface-border bg-surface-raised shrink-0">
        <Link to="/" className="flex items-center gap-2 font-semibold text-lg">
          <span className="text-accent">xSlou</span>
          <span className="text-slate-300">Clips AI</span>
        </Link>
        <span className="ml-3 text-xs text-slate-500 border border-surface-border rounded px-2 py-0.5">
          local · localhost:3000
        </span>
      </header>
      <main className="flex-1 overflow-y-auto">{children}</main>
    </div>
  );
}
