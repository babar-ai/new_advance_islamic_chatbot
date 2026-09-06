"use client";

interface SidebarProps {
  isOpen: boolean;
  onClose: () => void;
  onNewChat: () => void;
  activeTab: string;
  setActiveTab: (tab: string) => void;
}

export default function Sidebar({
  isOpen,
  onClose,
  onNewChat,
  activeTab,
  setActiveTab,
}: SidebarProps) {
  const navItems = [
    {
      id: "chat",
      label: "New Chat",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z"
          />
        </svg>
      ),
      isAction: true,
    },
    {
      id: "history",
      label: "History",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
      ),
    },
    {
      id: "bookmarks",
      label: "Bookmarks",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
          />
        </svg>
      ),
    },
    {
      id: "topics",
      label: "Topics",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
          />
        </svg>
      ),
    },
    {
      id: "settings",
      label: "Settings",
      icon: (
        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"
          />
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      ),
    },
  ];

  return (
    <>
      {/* Mobile backdrop */}
      {isOpen && (
        <div
          onClick={onClose}
          className="fixed inset-0 bg-slate-900/40 dark:bg-slate-950/70 backdrop-blur-xs z-40 lg:hidden"
        />
      )}

      {/* Sidebar container */}
      <aside
        className={`
          fixed lg:static top-0 bottom-0 left-0 z-50
          w-64 bg-white dark:bg-[#0D1522] border-r border-slate-200/80 dark:border-slate-800
          flex flex-col justify-between p-5 select-none transition-colors duration-200
          ${isOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        {/* Top Header & Branding */}
        <div>
          <div className="flex items-center justify-between mb-8">
            <div className="flex flex-col items-center mx-auto text-center">
              {/* Mosque Dome Logo */}
              <div className="w-12 h-12 mb-2 flex items-center justify-center text-[#084C3E] dark:text-emerald-400">
                <svg viewBox="0 0 48 48" className="w-10 h-10" fill="currentColor">
                  <path d="M24 3a3.5 3.5 0 011.5 6.7 3.5 3.5 0 00-.5-6.7z" />
                  <circle cx="24" cy="7.5" r="1" />
                  <path
                    d="M24 10c-5.5 4.5-9 10-9 16.5v13.5a1 1 0 001 1h16a1 1 0 001-1V26.5c0-6.5-3.5-12-9-16.5zm-5 27v-8a5 5 0 0110 0v8h-10z"
                    fillRule="evenodd"
                  />
                  <path d="M12 22l2 2v17h-4V24l2-2zm24 0l2 2v17h-4V24l2-2z" />
                </svg>
              </div>

              <h1 className="text-base font-bold tracking-tight text-[#084C3E] dark:text-emerald-300">
                Islamic Knowledge
              </h1>
              <p className="text-[11px] text-slate-400 dark:text-slate-500 font-medium tracking-wide mt-0.5">
                Seek · Learn · Apply
              </p>
            </div>

            {/* Mobile close button */}
            <button
              onClick={onClose}
              type="button"
              className="lg:hidden p-1.5 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-lg"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Navigation Items */}
          <nav className="space-y-1.5">
            {navItems.map((item) => {
              const isActive = activeTab === item.id;
              const isNewChat = item.id === "chat";

              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => {
                    if (isNewChat) {
                      onNewChat();
                    } else {
                      setActiveTab(item.id);
                    }
                    onClose();
                  }}
                  className={`
                    w-full flex items-center gap-3 px-3.5 py-2.5 rounded-xl text-sm font-medium
                    transition-all duration-150 cursor-pointer
                    ${
                      isNewChat
                        ? "bg-[#EAF4EE] dark:bg-emerald-950/70 text-[#084C3E] dark:text-emerald-300 hover:bg-[#E0EEE5] dark:hover:bg-emerald-900/50 font-semibold"
                        : isActive
                        ? "bg-slate-100 dark:bg-slate-800 text-slate-900 dark:text-slate-100 font-semibold"
                        : "text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-50 dark:hover:bg-slate-800/60"
                    }
                  `}
                >
                  <span className={isNewChat ? "text-[#084C3E] dark:text-emerald-400" : "text-slate-500 dark:text-slate-400"}>
                    {item.icon}
                  </span>
                  <span>{item.label}</span>
                </button>
              );
            })}
          </nav>
        </div>

        {/* Bottom Card: Islamic Quote */}
        <div className="relative overflow-hidden rounded-2xl bg-[#FAF9F5] dark:bg-[#0F172A] border border-[#EBE8E0] dark:border-slate-800 p-4 text-center shadow-xs transition-colors mb-1">
          <div className="text-xl text-[#084C3E]/70 dark:text-emerald-400/80 mb-1 leading-none font-serif">
            “
          </div>
          <p className="text-xs text-slate-700 dark:text-slate-300 font-medium leading-relaxed mb-2">
            “And say, ‘My Lord, increase me in knowledge.’”
          </p>
          <p className="text-[11px] text-slate-400 dark:text-slate-500 tracking-wide font-medium">
            — Qur&apos;an 20:114
          </p>
        </div>
      </aside>
    </>
  );
}
