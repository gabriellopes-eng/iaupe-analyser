"use client";

import { useState } from "react";

import { isValidEmail } from "@/domain/edital";
import { AlertIcon, OutlineStarIcon } from "@/components/icons";

interface EditaisEmptyStateProps {
  live: boolean;
  hasEmail: boolean;
  onSetEmail: (email: string) => void;
}

// Estado vazio da vitrine: sistema fora do ar, ou nenhum edital marcado ainda.
// Quando ainda nao tem e-mail, mostra o campo aqui tambem (igual o toast da
// estrela) - a pessoa nao precisa rolar ate o EmailGate la em cima.
export default function EditaisEmptyState({ live, hasEmail, onSetEmail }: EditaisEmptyStateProps) {
  const [draft, setDraft] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValidEmail(draft)) return;
    onSetEmail(draft.trim());
    setDraft("");
  }

  if (!live) {
    return (
      <div className="empty empty-error">
        <AlertIcon />
        <p>
          O sistema está fora do ar no momento, não foi possível carregar os editais. Tente
          novamente em alguns instantes.
        </p>
      </div>
    );
  }

  if (!hasEmail) {
    return (
      <div className="empty">
        <OutlineStarIcon />
        <p>Digite seu e-mail e toque na estrela de um edital para começar a receber lembretes.</p>
        <form className="empty-email-form" onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="seuemail@exemplo.com"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            aria-label="Seu e-mail"
          />
          <button type="submit">Confirmar</button>
        </form>
      </div>
    );
  }

  return (
    <div className="empty">
      <OutlineStarIcon />
      <p>
        Você ainda não marcou nenhum edital. Toque na estrela de um edital para começar a receber
        os lembretes dele.
      </p>
    </div>
  );
}
