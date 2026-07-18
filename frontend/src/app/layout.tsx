import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Oura Dashboard",
  description: "Personal health dashboard for Oura Ring data",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-full">
      <body className="min-h-full flex flex-col" style={{ background: "var(--bg-base)", color: "var(--text-primary)" }}>
        {children}
      </body>
    </html>
  );
}
