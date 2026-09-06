"use client";

interface HeaderProps {
  backendStatus: { isOnline: boolean; version?: string } | null;
  onOpenMobileSidebar: () => void;
  theme: "light" | "dark";
  onToggleTheme: () => void;
}

export default function Header({
  backendStatus,
  onOpenMobileSidebar,
  theme,
  onToggleTheme,
}: HeaderProps) {
  const isOnline = backendStatus?.isOnline ?? false;

  return (
    <header className="relative w-full border-b border-slate-200/80 dark:border-slate-800 bg-white/80 dark:bg-[#0D1522]/80 backdrop-blur-md z-10 select-none overflow-hidden transition-colors">
      {/* Delicate Mosque Skyline Watermark in background */}
      <div className="absolute right-0 top-0 bottom-0 pointer-events-none opacity-[0.07] dark:opacity-[0.04] overflow-hidden w-96 flex items-end justify-end">
        <svg viewBox="0 0 500 150" className="h-full w-auto text-[#084C3E] dark:text-emerald-400" fill="currentColor">
          <path d="M420 30a10 10 0 014 19 10 10 0 00-4-19z" />
          <path d="M280 150V90l10-10 10 10v60z" />
          <path d="M300 150V70l15-15 15 15v80z" />
          <path d="M330 150V95c0-25 20-45 45-45s45 20 45 45v55z" />
          <path d="M420 150V80l12-12 12 12v70z" />
          <path d="M444 150V95l8-8 8 8v55z" />
        </svg>
      </div>

      <div className="max-w-5xl mx-auto px-4 py-3 sm:py-3.5 flex items-center justify-between gap-3 relative z-10">
        {/* Left: Mobile menu toggle */}
        <div className="flex items-center gap-2">
          <button
            onClick={onOpenMobileSidebar}
            type="button"
            className="lg:hidden p-2 rounded-lg text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-white hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer"
            aria-label="Open Navigation"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
            </svg>
          </button>
        </div>

        {/* Center: AI Powered Badge */}
        <div className="flex-1 flex justify-center">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#EAF4EE] dark:bg-emerald-950/60 border border-[#D5EADB] dark:border-emerald-800/40 text-xs text-[#084C3E] dark:text-emerald-300 font-medium shadow-2xs">
            <span className="text-xs">✦</span>
            <span className="truncate max-w-[260px] sm:max-w-none">
              AI-powered answers from the Qur&apos;an, Hadith, and trusted scholarly sources
            </span>
          </div>
        </div>

        {/* Right: Theme Toggle & User pill with connection status */}
        <div className="flex items-center gap-2.5 sm:gap-3 shrink-0">
          {/* Working Theme Toggle Button */}
          <button
            type="button"
            onClick={onToggleTheme}
            className="p-2 rounded-full text-slate-500 hover:text-slate-900 dark:text-slate-400 dark:hover:text-amber-300 hover:bg-slate-100 dark:hover:bg-slate-800 transition-all cursor-pointer shadow-2xs"
            title={theme === "light" ? "Switch to Dark Mode" : "Switch to Light Mode"}
            aria-label="Toggle theme"
          >
            {theme === "light" ? (
              /* Moon Icon for switching to Dark */
              <svg className="w-4 h-4 text-slate-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z"
                />
              </svg>
            ) : (
              /* Sun Icon for switching to Light */
              <svg className="w-4 h-4 text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z"
                />
              </svg>
            )}
          </button>

          {/* User Profile Pill with backend status */}
          <div className="flex items-center gap-2 pl-2 border-l border-slate-200 dark:border-slate-800">
            <div className="w-7 h-7 rounded-full bg-[#084C3E] dark:bg-emerald-600 text-white flex items-center justify-center text-xs font-semibold shadow-xs">
              B
            </div>
            <div className="hidden sm:flex items-center gap-1.5 text-xs font-medium text-slate-700 dark:text-slate-300">
              <span>Babar Raheem</span>
              <span
                className={`w-2 h-2 rounded-full ${
                  isOnline ? "bg-emerald-500 animate-pulse" : "bg-amber-400"
                }`}
                title={isOnline ? "FastAPI API Online" : "FastAPI Backend is offline"}
              />
            </div>
          </div>
        </div>
      </div>
    </header>
  );
}
