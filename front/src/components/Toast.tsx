"use client";

import { useState } from "react";

import { isValidEmail } from "@/domain/edital";
import { StarIcon } from "@/components/icons";

interface ToastProps {
  message: string;
  show: boolean;
  tone: "gold" | "muted";
  needsEmail: boolean;
  onSetEmail: (email: string) => void;
}

// aqui é a parte relacionada com pedir o email: se precisar, mostra o campo
// junto do toast pra já resolver na hora
export default function Toast({ message, show, tone, needsEmail, onSetEmail }: ToastProps) {
  const [draft, setDraft] = useState("");

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!isValidEmail(draft)) return;
    onSetEmail(draft.trim());
    setDraft("");
  }

  return (
    <div className={`toast${show ? " show" : ""}${needsEmail ? " toast-with-form" : ""}`} role="status" aria-live="polite">
      <div className="toast-row">
        <span style={{ color: tone === "gold" ? "var(--gold)" : "var(--muted)", width: 18, height: 18, display: "inline-flex" }}>
          <StarIcon />
        </span>
        <span>{message}</span>
      </div>
      {needsEmail && (
        <form className="toast-email-form" onSubmit={handleSubmit}>
          <input
            type="email"
            placeholder="seuemail@exemplo.com"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            aria-label="Seu e-mail"
          />
          <button type="submit">Confirmar</button>
        </form>
      )}
    </div>
  );
}
