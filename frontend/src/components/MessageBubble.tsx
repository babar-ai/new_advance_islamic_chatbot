"use client";

import React, { useState, useMemo } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Message } from "@/lib/types";

interface MessageBubbleProps {
  message: Message;
  onToggleSave?: (id: string) => void;
  onFeedback?: (id: string, feedback: "like" | "dislike") => void;
}

// Helper to extract text content recursively from React children
function getNodeText(node: React.ReactNode): string {
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(getNodeText).join("");
  }
  if (node && typeof node === "object" && "props" in node) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return getNodeText((node as any).props?.children);
  }
  return "";
}

// Helper to strip leading "Source:" label while preserving React nodes (like <a> links)
function stripSourceLabel(children: React.ReactNode): React.ReactNode {
  if (typeof children === "string") {
    return children
      .replace(
        /^(?:\*{0,2}(?:Source|Sources|Reference|References|Tafsir Source|Tafseer Source|Tafsir|Tafseer)\*{0,2}\s*:|—|–|-)\s*/i,
        ""
      )
      .trim();
  }
  if (Array.isArray(children)) {
    return React.Children.map(children, (child, idx) => {
      if (idx === 0 && typeof child === "string") {
        const cleaned = child
          .replace(
            /^(?:\*{0,2}(?:Source|Sources|Reference|References|Tafsir Source|Tafseer Source|Tafsir|Tafseer)\*{0,2}\s*:|—|–|-)\s*/i,
            ""
          )
          .trim();
        return cleaned || null;
      }
      return child;
    });
  }
  return children;
}

// Helper to determine if a line or block is a source citation
function isSourceCitation(text: string): boolean {
  const trimmed = text.trim();
  if (!trimmed) return false;

  // Never match markdown horizontal rules, dividers, or pure dash lines
  if (/^[-—–*_]{2,}\s*$/.test(trimmed)) {
    return false;
  }

  // Must contain letters or numbers
  if (!/[A-Za-z0-9]/.test(trimmed)) {
    return false;
  }

  // Normalized version stripping outer parentheses, markdown bold/italic, dashes:
  // e.g. "(Surah Al-Baqarah (2:153))" -> "Surah Al-Baqarah (2:153)"
  // e.g. "**(Surah Az-Zumar (39:10))**" -> "Surah Az-Zumar (39:10)"
  const normalized = trimmed
    .replace(/^[\s—\-–*_\(\[]+/, "")
    .replace(/[\s*_\)\]]+$/, "");

  // Pattern 1: Explicit labels like Source:, Reference:, Tafsir Source:, etc.
  if (
    /^(?:\*{0,2}(?:Source|Sources|Reference|References|Tafsir Source|Tafseer Source|Tafsir|Tafseer)\*{0,2}\s*:)\s*(?:[A-Za-z0-9(\[].+)/i.test(
      trimmed
    ) ||
    /^(?:Source|Sources|Reference|References|Tafsir Source|Tafseer Source|Tafsir|Tafseer)\s*:/i.test(
      normalized
    )
  ) {
    return true;
  }

  // Pattern 1b: Em-dash followed by an authentic Islamic source or parenthetical
  if (
    /^[—\-–]\s*(?:\((?:Quran|Qur['’]?an|Surah|Sahih|Sunan|Jami|Musnad|Muwatta|Ibn|Tirmidhi|Abu Dawood|Tafsir)[^)]*\)|(?:Surah|Qur['’]?an|Sahih|Sunan|Tafsir)\s+[A-Za-z0-9])/i.test(
      trimmed
    )
  ) {
    return true;
  }

  // Pattern 2: Quran / Surah references with chapter:verse (including transliterations)
  // e.g. "Surah Az-Zumar (39:10)", "Surah Al-Baqarah (2:153)", "Surah Āl-‘Imrān (3:200)", "Surah Al-Ma'ārij (70:5)", "Quran (2:153)"
  if (
    /^(?:Surah|Qur['’]?an|Quran)\s+[A-Za-z\s'’\u0100-\u024F\-]+(?:\(?\d+:\d+(?:-\d+)?\)?|\d+:\d+)/i.test(
      normalized
    )
  ) {
    return true;
  }

  // Pattern 3: Hadith collections with volume, book, or number
  // e.g. "Sahih al-Bukhari 5027", "Sahih Muslim 2999", "Sunan Abu Dawood 4607", "Jami at-Tirmidhi 1987"
  if (
    /^(?:Sahih|Sunan|Jami['’]?|Musnad|Muwatta|Riyad as-Salihin)\s+(?:al-)?[A-Za-z\s'’\u0100-\u024F\-]+(?:\(?\d+(?:-\d+)?\)?|\d+|Book|\()/i.test(
      normalized
    )
  ) {
    return true;
  }

  // Pattern 4: Standalone parenthetical citation
  // e.g. "(Quran 2:153)", "(Surah Al-Baqarah 2:153)", "(Sahih Bukhari 5027)", "(39:10)"
  if (
    /^(?:(?:Quran|Qur['’]?an|Surah|Sahih|Sunan|Jami|Musnad|Muwatta|Al-Bukhari|Bukhari|Muslim|Tirmidhi|Abu Dawood|Ibn Majah|An-Nasa['’]?i|Nasa['’]?i|Tafsir|Ibn Kathir|Jalalayn|Al-Tabari|Riyad as-Salihin)[^)]*|\d+:\d+(?:-\d+)?)$/i.test(
      normalized
    )
  ) {
    return true;
  }

  // Pattern 5: Tafsir commentary attribution
  // e.g. "Tafsir Ibn Kathir", "Tafsir Jalalayn (2:153)"
  if (
    /^Tafsir\s+(?:Ibn Kathir|Jalalayn|al-Qurtubi|al-Tabari|as-Sa['’]?di|Ibn Abbas)/i.test(
      normalized
    )
  ) {
    return true;
  }

  return false;
}

export default function MessageBubble({
  message,
  onToggleSave,
  onFeedback,
}: MessageBubbleProps) {
  const isUser = message.role === "user";
  const [copied, setCopied] = useState(false);
  const [showSources, setShowSources] = useState(false);
  const [isSaved, setIsSaved] = useState(message.isSaved ?? false);
  const [feedback, setFeedback] = useState<"like" | "dislike" | null>(message.feedback ?? null);

  // Pre-process content line-by-line to strictly decouple citations from quotes into distinct blocks
  const processedContent = useMemo(() => {
    if (isUser) return message.content;
    const lines = message.content.split(/\r?\n/);
    const newLines: string[] = [];

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const trimmed = line.trim();

      // Strip leading blockquote marker for citation check
      const withoutQuote = trimmed.replace(/^>\s*/, "").trim();

      // Skip horizontal rules
      const isDivider = /^[-—–*_]{2,}\s*$/.test(withoutQuote);

      // Check if this line is predominantly Arabic text (Quranic ayah or Hadith in Arabic)
      const arabicMatches = withoutQuote.match(/[\u0600-\u06FF]/g) || [];
      const latinMatches = withoutQuote.match(/[a-zA-Z]/g) || [];
      const isArabicVerse =
        arabicMatches.length >= 3 && arabicMatches.length > latinMatches.length;

      if (isArabicVerse) {
        // Isolate Arabic verses onto their own standalone line with padding
        newLines.push("");
        newLines.push(withoutQuote);
        newLines.push("");
        continue;
      }

      // Check if this entire line is a citation
      if (!isDivider && isSourceCitation(withoutQuote)) {
        let cite = withoutQuote.replace(/^[—\-–]\s*/, "").trim();
        if (/[A-Za-z0-9]/.test(cite)) {
          if (!/^Source:\s*/i.test(cite)) {
            cite = `Source: ${cite}`;
          }
          // Isolate on its own distinct paragraph outside of any blockquote
          newLines.push("");
          newLines.push(cite);
          newLines.push("");
        } else {
          newLines.push(line);
        }
      } else {
        // Check if a citation is appended at the very end of a quote line
        // e.g. > "quote text" Surah Az-Zumar (39:10)
        const trailingMatch = line.match(
          /^(>\s*["'“].*?["'”])\s*(?:—|–|-)?\s*((?:Surah|Qur['’]?an|Sahih|Sunan)\s+[A-Za-z\s'’\u0100-\u024F\-]+(?:\(?\d+:\d+(?:-\d+)?\)?|\d+:\d+)|\((?:Quran|Qur['’]?an|Surah|Sahih|Sunan|Jami|Musnad|Muwatta|Ibn|Tirmidhi|Abu Dawood|Nasa['’]?i|Tafsir)[^)]*\))\s*$/i
        );

        if (trailingMatch) {
          newLines.push(trailingMatch[1]);
          newLines.push("");
          newLines.push(`Source: ${trailingMatch[2]}`);
          newLines.push("");
        } else {
          newLines.push(line);
        }
      }
    }

    return newLines.join("\n");
  }, [message.content, isUser]);

  // Automatically detect cited Islamic sources from message text for the drawer
  const detectedSources = useMemo(() => {
    if (isUser) return [];
    const sources: { name: string; url?: string }[] = [];
    const seenNames = new Set<string>();

    const addSource = (name: string, url?: string) => {
      const trimmedName = name
        .trim()
        .replace(/^[\s*_\(\[]+/, "")
        .replace(/[\s*_\)\]]+$/, "");
      if (!trimmedName || seenNames.has(trimmedName.toLowerCase())) return;
      seenNames.add(trimmedName.toLowerCase());
      sources.push({ name: trimmedName, url });
    };

    // 1. Detect Markdown links: [Title](URL)
    const linkMatches = Array.from(
      message.content.matchAll(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g)
    );
    for (const match of linkMatches) {
      addSource(match[1], match[2]);
    }

    // 2. Extract parenthesized citations
    const matches1 =
      message.content.match(
        /\((?:Quran|Qur'an|Surah|Sahih|Sunan|Jami|Musnad|Muwatta|Ibn|Tirmidhi|Abu Dawood|Tafsir|Tirmizi)[^)]*\)/gi
      ) || [];
    matches1.forEach((m) => {
      const cleaned = m.replace(/^[—\-\s(]+|[)\s]+$/g, "").trim();
      if (cleaned) addSource(cleaned);
    });

    // 3. Extract Surah name + verse citations (including transliterated names)
    const matches2 =
      message.content.match(
        /(?:Surah|Qur['’]?an)\s+[A-Za-z\s'’\u0100-\u024F\-]+(?:\(?\d+:\d+(?:-\d+)?\)?|\d+:\d+)/gi
      ) || [];
    matches2.forEach((m) => {
      const cleaned = m.replace(/^[—\-\s(]+|[)\s]+$/g, "").trim();
      if (cleaned) addSource(cleaned);
    });

    // 4. Extract Hadith collection citations
    const matches3 =
      message.content.match(
        /(?:Sahih|Sunan|Jami['’]?|Musnad|Muwatta)\s+(?:al-)?[A-Za-z\s'’\u0100-\u024F\-]+(?:\d+|Book|\([^\)]+\))/gi
      ) || [];
    matches3.forEach((m) => {
      const cleaned = m.replace(/^[—\-\s(]+|[)\s]+$/g, "").trim();
      if (cleaned) addSource(cleaned);
    });

    // 5. Extract Source: ... lines
    const matches4 =
      message.content.match(/(?:Source|Reference):\s*([^\n\r]+)/gi) || [];
    matches4.forEach((m) => {
      const cleaned = m
        .replace(/^(?:Source|Reference):\s*/i, "")
        .replace(/^[—\-\s(]+|[)\s]+$/g, "")
        .trim();
      const linkMatch = cleaned.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
      if (linkMatch) {
        addSource(linkMatch[1], linkMatch[2]);
      } else if (cleaned) {
        addSource(cleaned);
      }
    });

    // Post-process: auto-fill missing URLs
    const HADITH_URLS: Record<string, string> = {
      "Sahih al-Bukhari": "https://archive.org/details/sahih-al-bukhari-vol.-3-1773-2737_202111/Sahih%20al%20Bukhari%20Vol.%201%20-%201-875/",
      "Sahih Muslim": "https://archive.org/details/sahih-muslim-arabic-english-full/sahih-muslim-english-vol-1/",
      "Sunan Abu Dawood": "https://archive.org/details/sunan-abu-dawud-vol.-1-1160_202111/Sunan%20Abu%20Dawud%20Vol.%201%20-%201-1160/",
      "Sunan Abu Dawud": "https://archive.org/details/sunan-abu-dawud-vol.-1-1160_202111/Sunan%20Abu%20Dawud%20Vol.%201%20-%201-1160/",
      "Jami at-Tirmidhi": "https://archive.org/details/jami-at-tirmidhi-vol.-6-3291-3956_202111/Jami%20at%20Tirmidhi%20Vol.%201%20-%201-543/",
      "Jami' at-Tirmidhi": "https://archive.org/details/jami-at-tirmidhi-vol.-6-3291-3956_202111/Jami%20at%20Tirmidhi%20Vol.%201%20-%201-543/",
      "Sunan ibn Majah": "https://archive.org/details/sunan-ibn-majah-arabic-english-full/sunan-ibn-majah-english-vol-1/",
      "Sunan Ibn Majah": "https://archive.org/details/sunan-ibn-majah-arabic-english-full/sunan-ibn-majah-english-vol-1/",
      "Sunan al-Nasa'i": "https://archive.org/details/sunan-nasai-arabic-english-full/sunan-nasai-english-vol-1/page/n3/mode/2up",
      "Sunan an-Nasa'i": "https://archive.org/details/sunan-nasai-arabic-english-full/sunan-nasai-english-vol-1/page/n3/mode/2up",
    };

    return sources.map((src) => {
      if (src.url) {
        // Remove any stale shorturl.at links
        if (src.url.includes("shorturl.at")) {
          return { ...src, url: "https://www.altafsir.com" };
        }
        return src;
      }
      // Auto-generate quran.com URL from Surah citation
      const verseMatch = src.name.match(/\((\d+:\d+(?:-\d+)?)\)/);
      if (verseMatch && /surah|qur['']?an|quran/i.test(src.name)) {
        return { ...src, url: `https://quran.com/${verseMatch[1]}` };
      }
      // Also match bare verse like "2:153" without Surah prefix
      const bareVerseMatch = src.name.match(/^(\d+:\d+(?:-\d+)?)$/);
      if (bareVerseMatch) {
        return { ...src, url: `https://quran.com/${bareVerseMatch[1]}` };
      }
      // Map Hadith collection name to archive.org URL
      for (const [key, url] of Object.entries(HADITH_URLS)) {
        if (src.name.toLowerCase().includes(key.toLowerCase())) {
          return { ...src, url };
        }
      }
      return src;
    });

  }, [message.content, isUser]);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
    }
  };

  const handleSave = () => {
    const nextSaved = !isSaved;
    setIsSaved(nextSaved);
    if (onToggleSave) onToggleSave(message.id);
  };

  const handleFeedback = (type: "like" | "dislike") => {
    const next = feedback === type ? null : type;
    setFeedback(next);
    if (next && onFeedback) onFeedback(message.id, next);
  };

  const timeString = new Date(message.timestamp).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });

  // User Message
  if (isUser) {
    return (
      <div className="flex flex-col items-end w-full space-y-1">
        <div className="flex items-center gap-2.5 max-w-[85%] sm:max-w-[75%]">
          {/* User message bubble */}
          <div className="bg-[#EAF4EE] dark:bg-emerald-950/80 text-[#084C3E] dark:text-emerald-200 border border-transparent dark:border-emerald-800/40 rounded-2xl px-4 py-2.5 text-sm sm:text-base font-medium shadow-2xs">
            {message.content}
          </div>

          {/* User avatar circle */}
          <div className="w-8 h-8 rounded-full bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-300 flex items-center justify-center shrink-0 shadow-2xs">
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path
                fillRule="evenodd"
                d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z"
                clipRule="evenodd"
              />
            </svg>
          </div>
        </div>

        {/* Timestamp */}
        <span className="text-[11px] text-slate-400 dark:text-slate-500 mr-10 select-none">
          {timeString}
        </span>
      </div>
    );
  }

  // If this is an assistant message that is still streaming and has no content yet,
  // do not render an empty bubble (TypingIndicator handles the waiting state)
  if (!isUser && message.isStreaming && !message.content.trim()) {
    return null;
  }

  // Assistant Message
  return (
    <div className="flex items-start gap-3 w-full group">
      {/* Mosque Avatar on Left */}
      <div className="w-9 h-9 rounded-full bg-[#084C3E] dark:bg-emerald-600 text-white flex items-center justify-center shrink-0 shadow-2xs mt-0.5">
        <svg viewBox="0 0 48 48" className="w-5 h-5" fill="currentColor">
          <path d="M24 3a3.5 3.5 0 011.5 6.7 3.5 3.5 0 00-.5-6.7z" />
          <path
            d="M24 10c-5.5 4.5-9 10-9 16.5v13.5a1 1 0 001 1h16a1 1 0 001-1V26.5c0-6.5-3.5-12-9-16.5zm-5 27v-8a5 5 0 0110 0v8h-10z"
            fillRule="evenodd"
          />
        </svg>
      </div>

      {/* Main Assistant Card */}
      <div className="flex-1 max-w-[94%] sm:max-w-[88%] bg-white dark:bg-[#0F172A] border border-slate-200/90 dark:border-slate-800 rounded-2xl p-5 sm:p-6 shadow-2xs text-slate-800 dark:text-slate-100 transition-colors">
        {/* Markdown content with spacious typography and Arabic clarity */}
        <div className="prose-islamic">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Dedicated treatment for paragraphs, Arabic verses, and citations
              p: ({ children }) => {
                const text = getNodeText(children);
                const arabicMatches = text.match(/[\u0600-\u06FF]/g) || [];
                const latinMatches = text.match(/[a-zA-Z]/g) || [];
                const isPredominantlyArabic =
                  arabicMatches.length > latinMatches.length && arabicMatches.length >= 3;

                // 1. Standalone Arabic Verse Box (Amiri Naskh font, large, calligraphic)
                if (isPredominantlyArabic) {
                  return (
                    <div className="arabic-verse-box my-4 text-center">
                      <p
                        className="font-arabic text-2xl sm:text-3xl text-[#084C3E] dark:text-emerald-300 font-bold leading-[2.3] tracking-wide"
                        dir="rtl"
                      >
                        {children}
                      </p>
                    </div>
                  );
                }

                // 2. Dedicated Source Citation Badge - clickable link if URL present
                if (isSourceCitation(text)) {
                  let cleanSource = text
                    .trim()
                    .replace(
                      /^(?:\*{0,2}(?:Source|Sources|Reference|References|Tafsir Source|Tafseer Source|Tafsir|Tafseer)\*{0,2}\s*:|—|–|-)?\s*/i,
                      ""
                    )
                    .replace(/^(?:Source|Sources|Reference|References)\s*:\s*/i, "")
                    .replace(/^[\s*_\(\[]+/, "")
                    .replace(/[\s*_\)\]]+$/, "")
                    .replace(/[\s\-–—]*(?:Arabic|Translation)\s*:?\s*$/i, "")
                    .trim();

                  if (!/[A-Za-z0-9\u0600-\u06FF]/.test(cleanSource)) {
                    return (
                      <p className="mb-4 text-slate-700 dark:text-slate-300 leading-relaxed text-sm sm:text-base">
                        {children}
                      </p>
                    );
                  }

                  // Extract URL from markdown link pattern [Label](URL) in cleanSource
                  let sourceUrl: string | null = null;
                  let sourceLabel: React.ReactNode = stripSourceLabel(children);

                  const mdLinkMatch = cleanSource.match(/^\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)$/);
                  if (mdLinkMatch) {
                    sourceLabel = mdLinkMatch[1];
                    sourceUrl = mdLinkMatch[2];
                  } else {
                    // Also check the raw text children for a markdown link
                    const rawText = typeof children === "string"
                      ? children
                      : getNodeText(children);
                    const rawMdMatch = rawText.match(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/);
                    if (rawMdMatch) {
                      sourceLabel = rawMdMatch[1];
                      sourceUrl = rawMdMatch[2];
                    } else {
                      // Auto-generate quran.com link from "Surah Name (X:Y)" pattern
                      const versePattern = cleanSource.match(/\((\d+:\d+(?:-\d+)?)\)/);
                      if (versePattern && /surah|qur['']?an|quran/i.test(cleanSource)) {
                        sourceUrl = `https://quran.com/${versePattern[1]}`;
                      }
                      // Fix any remaining shorturl.at links — replace with altafsir.com
                      if (sourceUrl && sourceUrl.includes("shorturl.at")) {
                        sourceUrl = "https://www.altafsir.com";
                      }
                    }
                  }

                  const badgeContent = (
                    <>
                      <svg
                        className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400 shrink-0"
                        fill="none"
                        stroke="currentColor"
                        viewBox="0 0 24 24"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                        />
                      </svg>
                      <span className="text-[10px] font-bold uppercase tracking-widest text-emerald-700/80 dark:text-emerald-400/80">
                        Source:
                      </span>
                      <span className="font-semibold text-slate-800 dark:text-emerald-200">
                        {sourceLabel}
                      </span>
                      {sourceUrl && (
                        <svg
                          className="w-3 h-3 opacity-60 shrink-0"
                          fill="none"
                          stroke="currentColor"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                          />
                        </svg>
                      )}
                    </>
                  );

                  return (
                    <div className="my-2.5 not-prose block">
                      {sourceUrl ? (
                        <a
                          href={sourceUrl}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="source-citation-badge inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/80 dark:border-emerald-800/70 text-[#084C3E] dark:text-emerald-300 font-sans not-italic text-xs sm:text-[13px] font-semibold tracking-wide shadow-2xs hover:border-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/50 transition-colors cursor-pointer"
                        >
                          {badgeContent}
                        </a>
                      ) : (
                        <div className="source-citation-badge inline-flex items-center gap-2 px-3 py-1.5 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200/80 dark:border-emerald-800/70 text-[#084C3E] dark:text-emerald-300 font-sans not-italic text-xs sm:text-[13px] font-semibold tracking-wide shadow-2xs">
                          {badgeContent}
                        </div>
                      )}
                    </div>
                  );
                }

                // 3. Standard English Paragraph with generous spacing
                return (
                  <p className="mb-4 text-slate-700 dark:text-slate-300 leading-relaxed text-sm sm:text-base">
                    {children}
                  </p>
                );
              },

              // Dedicated, reflective blockquotes for Quran & Hadith Translations (Lora serif italic)
              blockquote: ({ children }) => (
                <blockquote className="my-4 border-l-4 border-[#084C3E] dark:border-emerald-500 bg-[#F7FAF8] dark:bg-emerald-950/20 px-5 py-3.5 rounded-r-xl shadow-2xs font-verse italic text-slate-800 dark:text-slate-200 text-[15px] sm:text-base leading-relaxed tracking-normal">
                  {children}
                </blockquote>
              ),

              // List items with native support for clickable source links
              li: ({ children }) => (
                <li className="mb-1.5 text-slate-700 dark:text-slate-300 leading-relaxed text-sm sm:text-base">
                  {children}
                </li>
              ),

              // Clickable external links with modern emerald aesthetic and external link icon
              a: ({ href, children }) => (
                <a
                  href={href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 font-semibold text-emerald-700 hover:text-emerald-800 dark:text-emerald-400 dark:hover:text-emerald-300 underline underline-offset-2 decoration-emerald-500/40 hover:decoration-emerald-500 transition-colors"
                >
                  <span>{children}</span>
                  <svg
                    className="w-3.5 h-3.5 inline-block opacity-70"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </a>
              ),

              // Headers with clear hierarchy
              h1: ({ children }) => (
                <h1 className="text-base sm:text-lg font-bold text-[#084C3E] dark:text-emerald-400 mt-6 mb-2 pb-1.5 border-b border-slate-100 dark:border-slate-800">
                  {children}
                </h1>
              ),
              h2: ({ children }) => (
                <h2 className="text-sm sm:text-base font-bold text-[#084C3E] dark:text-emerald-400 mt-5 mb-2 pb-1 border-b border-slate-100 dark:border-slate-800">
                  {children}
                </h2>
              ),
              h3: ({ children }) => (
                <h3 className="text-sm sm:text-base font-bold text-[#084C3E] dark:text-emerald-400 mt-4 mb-2">
                  {children}
                </h3>
              ),

              strong: ({ children }) => (
                <strong className="font-bold text-slate-900 dark:text-white">
                  {children}
                </strong>
              ),
            }}
          >
            {processedContent}
          </ReactMarkdown>
        </div>

        {/* Blinking streaming cursor */}
        {message.isStreaming && (
          <span className="inline-block w-2 h-4 bg-[#084C3E] dark:bg-emerald-400 rounded-sm animate-pulse ml-1 align-text-bottom" />
        )}

        {/* Show sources drawer and action bar only after streaming is complete */}
        {!message.isStreaming && (
          <>
            {/* Enhanced Collapsible Sources Drawer */}
            {showSources && (
              <div className="mt-5 pt-4 border-t border-slate-100 dark:border-slate-800 bg-[#FAFBF9] dark:bg-slate-900/90 rounded-xl p-4 text-xs animate-fade-in space-y-3">
                <div className="flex items-center justify-between">
                  <p className="font-bold text-[#084C3E] dark:text-emerald-400 flex items-center gap-1.5 text-sm">
                    <span>📖</span>
                    <span>Authentic Sources &amp; Citations</span>
                  </p>
                  <span className="text-[11px] text-slate-400">
                    Verified Knowledgebase
                  </span>
                </div>

                {/* Extracted Citations Cards */}
                {detectedSources.length > 0 ? (
                  <div>
                    <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mb-1.5">
                      Specific Verses &amp; Collections Referenced:
                    </p>
                    <div className="flex flex-wrap gap-2">
                      {detectedSources.map((src, idx) =>
                        src.url ? (
                          <a
                            key={idx}
                            href={src.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-emerald-50 dark:bg-emerald-950/60 border border-emerald-200 dark:border-emerald-800 text-xs font-semibold text-[#084C3E] dark:text-emerald-300 hover:border-emerald-400 hover:text-emerald-700 shadow-2xs transition-colors"
                          >
                            <span className="text-amber-500">۞</span>
                            <span>{src.name}</span>
                            <svg
                              className="w-3 h-3 opacity-60"
                              fill="none"
                              stroke="currentColor"
                              viewBox="0 0 24 24"
                            >
                              <path
                                strokeLinecap="round"
                                strokeLinejoin="round"
                                strokeWidth={2}
                                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                              />
                            </svg>
                          </a>
                        ) : (
                          <span
                            key={idx}
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-lg bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-xs font-semibold text-[#084C3E] dark:text-emerald-300 shadow-2xs"
                          >
                            <span className="text-amber-500">۞</span>
                            <span>{src.name}</span>
                          </span>
                        )
                      )}
                    </div>
                  </div>
                ) : null}

                {/* Core RAG Collections */}
                <div className="pt-2 border-t border-slate-200/60 dark:border-slate-800/80">
                  <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium mb-1">
                    Grounded Across Islamic Knowledge Collections:
                  </p>
                  <ul className="grid grid-cols-1 sm:grid-cols-2 gap-1.5 text-slate-600 dark:text-slate-400">
                    <li className="flex items-center gap-1.5">
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓</span>
                      <span>Holy Qur&apos;an (with Arabic text &amp; translations)</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓</span>
                      <span>Sahih Hadith Collections (Bukhari, Muslim, Sunan)</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓</span>
                      <span>Classical Tafsir Commentary (Ibn Kathir, Jalalayn)</span>
                    </li>
                    <li className="flex items-center gap-1.5">
                      <span className="text-emerald-600 dark:text-emerald-400 font-bold">✓</span>
                      <span>Verified Qdrant Vector Embeddings</span>
                    </li>
                  </ul>
                </div>
              </div>
            )}

            {/* Bottom Actions Bar */}
            <div className="flex items-center justify-between mt-6 pt-3.5 border-t border-slate-100 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 select-none">
              {/* Left Actions: Sources, Copy, Save */}
              <div className="flex items-center gap-3">
                {/* Sources Button */}
                <button
                  type="button"
                  onClick={() => setShowSources(!showSources)}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${showSources
                      ? "text-[#084C3E] dark:text-emerald-400 bg-slate-100 dark:bg-slate-800 font-medium"
                      : "text-slate-500 dark:text-slate-400"
                    }`}
                >
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"
                    />
                  </svg>
                  <span>Sources {detectedSources.length > 0 ? `(${detectedSources.length})` : ""}</span>
                </button>

                {/* Copy Button */}
                <button
                  type="button"
                  onClick={handleCopy}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                >
                  {copied ? (
                    <>
                      <svg className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                      <span className="text-emerald-600 dark:text-emerald-400 font-medium">Copied</span>
                    </>
                  ) : (
                    <>
                      <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={1.8}
                          d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
                        />
                      </svg>
                      <span>Copy</span>
                    </>
                  )}
                </button>

                {/* Save / Bookmark Button */}
                <button
                  type="button"
                  onClick={handleSave}
                  className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${isSaved
                      ? "text-[#084C3E] dark:text-emerald-400 bg-slate-100 dark:bg-slate-800 font-medium"
                      : "text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200"
                    }`}
                >
                  <svg
                    className="w-3.5 h-3.5"
                    fill={isSaved ? "currentColor" : "none"}
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.8}
                      d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z"
                    />
                  </svg>
                  <span>{isSaved ? "Saved" : "Save"}</span>
                </button>
              </div>

              {/* Right Actions: Like/Dislike & Timestamp */}
              <div className="flex items-center gap-2">
                {/* Like */}
                <button
                  type="button"
                  onClick={() => handleFeedback("like")}
                  className={`p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${feedback === "like" ? "text-[#084C3E] dark:text-emerald-400" : "text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                    }`}
                  title="Helpful"
                >
                  <svg className="w-3.5 h-3.5" fill={feedback === "like" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M14 10h4.764a2 2 0 011.789 2.894l-3.5 7A2 2 0 0115.263 21h-4.017c-.163 0-.326-.02-.485-.06L7 20m7-10V5a2 2 0 00-2-2h-.095c-.5 0-.905.405-.905.905 0 .714-.211 1.412-.608 2.006L7 11v9m7-10h-2M7 20H5a2 2 0 01-2-2v-6a2 2 0 012-2h2.5" />
                  </svg>
                </button>

                {/* Dislike */}
                <button
                  type="button"
                  onClick={() => handleFeedback("dislike")}
                  className={`p-1.5 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors cursor-pointer ${feedback === "dislike" ? "text-red-500" : "text-slate-400 hover:text-slate-700 dark:hover:text-slate-200"
                    }`}
                  title="Not helpful"
                >
                  <svg className="w-3.5 h-3.5" fill={feedback === "dislike" ? "currentColor" : "none"} stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.8} d="M10 14H5.236a2 2 0 01-1.789-2.894l3.5-7A2 2 0 018.736 3h4.018a2 2 0 01.485.06l3.761.94m-7 10v5a2 2 0 002 2h.096c.5 0 .905-.405.905-.904 0-.715.211-1.413.608-2.008L17 13V4m-7 10h2m5-10h2a2 2 0 012 2v6a2 2 0 01-2 2h-2.5" />
                  </svg>
                </button>

                {/* Timestamp */}
                <span className="text-[11px] text-slate-400 dark:text-slate-500 pl-1">
                  {timeString}
                </span>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
