import type { Metadata, Viewport } from "next";
import { Inter, Amiri, Lora } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

const lora = Lora({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
  variable: "--font-lora",
  display: "swap",
});

const amiri = Amiri({
  subsets: ["arabic"],
  weight: ["400", "700"],
  variable: "--font-amiri",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Islamic Knowledge — Seek · Learn · Apply",
  description:
    "Your trusted AI companion for Islamic knowledge using Qur'an, Hadith, Tafsir, and authentic Islamic sources.",
  keywords: [
    "Islamic Knowledge",
    "Quran AI",
    "Hadith Search",
    "Islamic Chatbot",
    "Fiqh",
    "Seerah",
    "Tafsir",
  ],
};

export const viewport: Viewport = {
  themeColor: "#084c3e",
  width: "device-width",
  initialScale: 1,
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${inter.variable} ${amiri.variable} ${lora.variable} h-full`}
      suppressHydrationWarning
    >
      <body className="h-full bg-[#fbfbf9] dark:bg-[#090d16] text-slate-800 dark:text-slate-100 antialiased transition-colors duration-200">
        {children}
      </body>
    </html>
  );
}
