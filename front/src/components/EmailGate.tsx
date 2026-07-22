"use client";

import { useState } from "react";

import { isValidEmail } from "@/domain/edital";

interface EmailGateProps {
  email: string | null;
  onSetEmail: (email: string) => void;
  onClearEmail: () => void;
}

// Identificacao sem autenticacao: a pessoa so digita o e-mail (sem senha, sem
// cadastro) para poder marcar interesse em editais especificos. O navegador
// guarda esse e-mail (localStorage) para as proximas visitas.
export default function EmailGate({ email, onSetEmail, onClearEmail }: EmailGateProps) {
  const [draft, setDraft] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValidEmail(draft)) {
      setError("Digite um e-mail válido.");
      return;
    }
    setError("");
    onSetEmail(draft.trim());
    setDraft("");
  }

  if (email) {
    return (
      <div className="email-gate email-gate-set">
        <span>
          Marcando interesse como <b>{email}</b>
        </span>
        <button type="button" className="email-gate-change" onClick={onClearEmail}>
          trocar e-mail
        </button>
      </div>
    );
  }

  return (
    <form className="email-gate" onSubmit={handleSubmit}>
      <span>Digite seu e-mail para escolher os editais que quer acompanhar:</span>
      <div className="email-gate-input-row">
        <input
          type="email"
          placeholder="seuemail@exemplo.com"
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          aria-label="Seu e-mail"
        />
        <button type="submit">Confirmar</button>
      </div>
      {error && <span className="email-gate-error">{error}</span>}
    </form>
  );
}
