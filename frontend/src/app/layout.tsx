// src/app/layout.tsx
// src/app/layout.tsx
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import AppShell from "./AppShell";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "DevOS Jarvis Web",
  description: "Next.js frontend for DevOS Jarvis Web",
};

import { Toaster } from "../components/ui/sonner"; // Assuming sonner installed
import AppProviders from "./providers"; // Это твой providers.tsx (в котором уже есть AuthProvider, QueryProvider и т.д.)

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} ${geistMono.variable} antialiased bg-zinc-950 text-white min-h-screen`}>
        <AppProviders>
          <AppShell>{children}</AppShell>
        </AppProviders>
        <Toaster richColors position="top-right" />
      </body>
    </html>
  );
}
