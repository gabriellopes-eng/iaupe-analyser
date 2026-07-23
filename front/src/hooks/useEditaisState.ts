"use client";

import { useEffect, useState } from "react";

import { Edital } from "@/domain/edital";

const EMAIL_STORAGE_KEY = "iaupe:email";

export interface ToastState {
  message: string;
  tone: "gold" | "muted";
  show: boolean;
}

// Estado e integracoes de dados do painel de editais: identificacao por
// e-mail (sem autenticacao - so o endereco digitado, guardado no navegador),
// busca/recarga da lista, e marcacao de interesse com atualizacao otimista.
// A view (EditaisView.tsx) so consome o que este hook devolve.
export function useEditaisState(initialEditais: Edital[], initialLive: boolean) {
  const [editais, setEditais] = useState<Edital[]>(initialEditais);
  const [live, setLive] = useState<boolean>(initialLive);
  const [email, setEmail] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState>({ message: "", tone: "gold", show: false });

  // le o e-mail salvo no navegador e re-consulta os editais com o interesse
  // correto (o carregamento inicial no servidor nao tem acesso ao localStorage)
  useEffect(() => {
    const saved = window.localStorage.getItem(EMAIL_STORAGE_KEY);
    if (saved) {
      setEmail(saved);
      refetchEditais(saved);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function showToast(message: string, tone: ToastState["tone"]) {
    setToast({ message, tone, show: true });
    window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
  }

  async function refetchEditais(currentEmail: string) {
    try {
      const res = await fetch(`/api/editais?email=${encodeURIComponent(currentEmail)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { editais: Edital[]; live: boolean };
      setEditais(data.editais);
      setLive(data.live);
    } catch (err) {
      console.error("Falha ao recarregar editais com e-mail:", err);
      setLive(false);
    }
  }

  function handleSetEmail(newEmail: string) {
    window.localStorage.setItem(EMAIL_STORAGE_KEY, newEmail);
    setEmail(newEmail);
    refetchEditais(newEmail);
    showToast(`Identificado como ${newEmail}`, "gold");
  }

  function handleClearEmail() {
    window.localStorage.removeItem(EMAIL_STORAGE_KEY);
    setEmail(null);
    setEditais((prev) => prev.map((e) => ({ ...e, interested: false })));
  }

  async function toggleInterest(edital: Edital) {
    if (!email) {
      showToast("Digite seu e-mail para marcar interesse.", "muted");
      return;
    }

    const nextValue = !edital.interested;

    // atualizacao otimista: a UI responde na hora
    setEditais((prev) =>
      prev.map((e) => (e.id === edital.id ? { ...e, interested: nextValue } : e)),
    );
    const short = edital.titulo.length > 40 ? `${edital.titulo.slice(0, 37)}...` : edital.titulo;
    showToast(
      nextValue ? `Marcado: ${short}. Você receberá os lembretes` : `Removido: ${short}`,
      nextValue ? "gold" : "muted",
    );

    try {
      const res = await fetch(`/api/editais/${edital.id}/interest`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, interested: nextValue }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      // reverte em caso de falha na persistencia
      console.error("Falha ao salvar interesse:", err);
      setEditais((prev) =>
        prev.map((e) => (e.id === edital.id ? { ...e, interested: !nextValue } : e)),
      );
      showToast("Não foi possível salvar. Tente novamente.", "muted");
    }
  }

  return { editais, live, email, toast, handleSetEmail, handleClearEmail, toggleInterest };
}
