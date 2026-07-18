import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oura Fun",
  description: "Your Oura Ring data — locally hosted dashboard and AI chat",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-bg-base text-ink-primary antialiased">
        {children}
      </body>
    </html>
  );
}
