import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Plataforma de Monitoramento de Editais",

  description:
    "Escolha as fontes que você acompanha e receba lembretes de prazo dos editais delas.",
  icons: {
    icon: "/upe-favicon.png",
  },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR">
      <body>
        <header className="top">
          <div className="top-inner">
            <div className="emblem">
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src="/upe_logo_branco.png" alt="Universidade de Pernambuco" />
            </div>
            <div className="brand-txt">
              <p className="brand-eyebrow">Plataforma de Monitoramento de Editais</p>
              <p className="brand-name">Plataforma de Monitoramento de Editais</p>
            </div>
          </div>
        </header>
        {children}
      </body>
    </html>
  );
}
