import type { Metadata } from "next";
import { Sidebar } from "../components/Sidebar";
import { Header } from "../components/Header";
import "./globals.css";

export const metadata: Metadata = {
  title: "INCIDENTX AI — Autonomous Reliability Intelligence System",
  description: "Autonomous AI Incident Investigation, Causal Reasoning, and Self-Healing Platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#090d16] text-slate-100 flex font-sans antialiased">
        <Sidebar />
        <div className="flex-1 flex flex-col min-w-0">
          <Header />
          <main className="flex-1 p-6 overflow-y-auto bg-enterprise-grid">
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
