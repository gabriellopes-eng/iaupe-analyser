"use client";

import { StarIcon } from "@/components/icons";

interface ToastProps {
  message: string;
  show: boolean;
  tone: "gold" | "muted";
}

// Notificacao transitoria de confirmacao da acao.
export default function Toast({ message, show, tone }: ToastProps) {
  return (
    <div className={`toast${show ? " show" : ""}`} role="status" aria-live="polite">
      <span style={{ color: tone === "gold" ? "var(--gold)" : "var(--muted)", width: 18, height: 18, display: "inline-flex" }}>
        <StarIcon />
      </span>
      <span>{message}</span>
    </div>
  );
}
