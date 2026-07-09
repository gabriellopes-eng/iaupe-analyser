import type { Metadata } from "next";

import ThemeToggle from "@/components/ThemeToggle";
import "./globals.css";

export const metadata: Metadata = {
  title: "Editais de Interesse — IAUPE Analyzer",
  description:
    "Selecione os editais que você acompanha e receba lembretes de prazo apenas dos selecionados.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="top">
          <div className="top-inner">
            <div className="emblem" aria-hidden="true">
              <svg viewBox="0 0 24 24" fill="none" stroke="#fff" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" width="24" height="24">
                <path d="M6 3h9l4 4v14H6z" />
                <path d="M14 3v5h5" />
                <path
                  d="M12 11.5l1.2 2.5 2.8.4-2 2 .5 2.7-2.5-1.3-2.5 1.3.5-2.7-2-2 2.8-.4z"
                  fill="#d99a1f"
                  stroke="#d99a1f"
                  strokeWidth="0.6"
                />
              </svg>
            </div>
            <div className="brand-txt">
              <p className="brand-eyebrow">Plataforma de Monitoramento de Editais</p>
              <p className="brand-name">IAUPE Analyzer</p>
            </div>
            <ThemeToggle />
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
