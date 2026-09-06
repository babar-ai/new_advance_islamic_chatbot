"use client";

interface WelcomeScreenProps {
  onSelectSuggestion: (question: string) => void;
}

export default function WelcomeScreen({ onSelectSuggestion }: WelcomeScreenProps) {
  const topicCards = [
    {
      id: "quran",
      title: "Qur'an",
      description: "Explore meanings and context",
      prompt: "What does the Qur'an say about patience (Sabr)?",
      icon: (
        <svg className="w-6 h-6 text-[#084C3E] dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      id: "hadith",
      title: "Hadith",
      description: "Authentic sayings and explanations",
      prompt: "What are the recorded Hadiths about honesty and truthfulness in daily conduct?",
      icon: (
        <svg className="w-6 h-6 text-[#084C3E] dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <rect x="5" y="4" width="14" height="4" rx="2" strokeWidth={1.8} />
          <rect x="5" y="10" width="14" height="4" rx="2" strokeWidth={1.8} />
          <rect x="5" y="16" width="14" height="4" rx="2" strokeWidth={1.8} />
        </svg>
      ),
    },
    {
      id: "fiqh",
      title: "Fiqh",
      description: "Practical guidance for daily life",
      prompt: "What are the essential requirements and virtues of Salah in Islam?",
      icon: (
        <svg className="w-6 h-6 text-[#084C3E] dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.8}
            d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"
          />
        </svg>
      ),
    },
    {
      id: "seerah",
      title: "Seerah",
      description: "Learn from the life of the Prophet ﷺ",
      prompt: "Tell me about the character and compassion of the Prophet Muhammad ﷺ.",
      icon: (
        <svg className="w-6 h-6 text-[#084C3E] dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <circle cx="12" cy="12" r="9" strokeWidth={1.8} />
          <polygon points="12 8, 15 15, 8 13" fill="currentColor" strokeWidth={1.2} />
        </svg>
      ),
    },
  ];

  return (
    <div className="flex-1 flex flex-col items-center justify-center px-4 py-8 max-w-4xl mx-auto w-full text-center select-none">
      {/* Hero Headline */}
      <div className="mb-10">
        <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-slate-900 dark:text-slate-100">
          Ask. Learn. Grow.
        </h2>
        <p className="text-sm sm:text-base text-slate-500 dark:text-slate-400 font-normal mt-2.5 max-w-md mx-auto">
          Your trusted companion for Islamic knowledge
        </p>
      </div>

      {/* 4 Topic Cards matching reference */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3.5 sm:gap-4 w-full text-center">
        {topicCards.map((topic) => (
          <button
            key={topic.id}
            type="button"
            onClick={() => onSelectSuggestion(topic.prompt)}
            className="
              flex flex-col items-center p-5 rounded-2xl bg-white dark:bg-[#0F172A]
              border border-slate-200/90 dark:border-slate-800
              shadow-2xs hover:shadow-md hover:border-[#084C3E]/40 dark:hover:border-emerald-500/40 hover:-translate-y-0.5
              transition-all duration-200 cursor-pointer group
            "
          >
            {/* Topic Icon */}
            <div className="w-10 h-10 mb-3 rounded-xl flex items-center justify-center group-hover:scale-105 transition-transform">
              {topic.icon}
            </div>

            {/* Topic Title */}
            <h3 className="text-sm font-bold text-slate-900 dark:text-slate-100 group-hover:text-[#084C3E] dark:group-hover:text-emerald-400 transition-colors">
              {topic.title}
            </h3>

            {/* Topic Description */}
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-snug">
              {topic.description}
            </p>
          </button>
        ))}
      </div>
    </div>
  );
}
