"use client";

import { useCallback, useEffect, useState } from "react";

import { Edital } from "@/domain/edital";

const EMAIL_STORAGE_KEY = "iaupe:email";
const PAGE_SIZE = 20;

export interface ToastState {
  message: string;
  tone: "gold" | "muted";
  show: boolean;
  // pediu email: mostra o campo de email junto do toast
  needsEmail: boolean;
}

interface EditaisPageResponse {
  editais: Edital[];
  nextCursor: string | null;
  hasMore: boolean;
  totalCount: number;
  interestList: Edital[];
  live: boolean;
}

async function fetchPage(email: string | null, cursor: string | null): Promise<EditaisPageResponse> {
  const params = new URLSearchParams({ limit: String(PAGE_SIZE) });
  if (email) params.set("email", email);
  if (cursor) params.set("cursor", cursor);
  const res = await fetch(`/api/editais?${params.toString()}`);
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return (await res.json()) as EditaisPageResponse;
}

interface InitialState {
  editais: Edital[];
  live: boolean;
  nextCursor: string | null;
  hasMore: boolean;
  totalCount: number;
}

// Estado e integracoes de dados do painel de editais: identificacao por
// e-mail (sem autenticacao - so o endereco digitado, guardado no navegador),
// paginacao por cursor da lista "Todos" (20 em 20, com scroll infinito), e
// marcacao de interesse com atualizacao otimista.
// "Meus interesses" (interestList) NAO e paginado - vem sempre completo do
// servidor (ver /api/editais), porque e uma lista pequena (so do proprio
// usuario) e alimenta contadores que precisam estar corretos mesmo antes do
// usuario rolar a pagina inteira.
// A view (EditaisView.tsx) so consome o que este hook devolve.
export function useEditaisState(initial: InitialState) {
  const [editais, setEditais] = useState<Edital[]>(initial.editais);
  const [interestList, setInterestList] = useState<Edital[]>([]);
  const [totalCount, setTotalCount] = useState<number>(initial.totalCount);
  const [nextCursor, setNextCursor] = useState<string | null>(initial.nextCursor);
  const [hasMore, setHasMore] = useState<boolean>(initial.hasMore);
  const [loadingMore, setLoadingMore] = useState(false);
  const [live, setLive] = useState<boolean>(initial.live);
  const [email, setEmail] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastState>({
    message: "",
    tone: "gold",
    show: false,
    needsEmail: false,
  });

  // le o e-mail salvo no navegador e re-consulta a primeira pagina com o
  // interesse correto (o carregamento inicial no servidor nao tem acesso ao
  // localStorage, entao sempre vem com interested: false)
  useEffect(() => {
    const saved = window.localStorage.getItem(EMAIL_STORAGE_KEY);
    if (saved) {
      setEmail(saved);
      resetAndFetch(saved);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // se precisa de email, nao some sozinho (senao a pessoa nem da tempo de digitar)
  function showToast(message: string, tone: ToastState["tone"], needsEmail = false) {
    setToast({ message, tone, show: true, needsEmail });
    if (!needsEmail) {
      window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
    }
  }

  // recomeca a paginacao do zero (cursor null) - usado quando o e-mail muda,
  // ja que o campo `interested` de cada edital depende de quem esta pedindo
  async function resetAndFetch(currentEmail: string) {
    try {
      const data = await fetchPage(currentEmail, null);
      setEditais(data.editais);
      setInterestList(data.interestList);
      setTotalCount(data.totalCount);
      setNextCursor(data.nextCursor);
      setHasMore(data.hasMore);
      setLive(data.live);
    } catch (err) {
      console.error("Falha ao recarregar editais com e-mail:", err);
      setLive(false);
    }
  }

  // busca a proxima pagina (scroll infinito) e acrescenta ao final da lista ja carregada.
  // useCallback com essas dependencias mantem a identidade da funcao estavel entre
  // renders que nao mudam esses valores - o observer de scroll infinito na
  // EditaisView depende disso pra nao recriar a cada render.
  const loadMore = useCallback(async () => {
    if (loadingMore || !hasMore) return;
    setLoadingMore(true);
    try {
      const data = await fetchPage(email, nextCursor);
      setEditais((prev) => [...prev, ...data.editais]);
      setNextCursor(data.nextCursor);
      setHasMore(data.hasMore);
      setLive(data.live);
    } catch (err) {
      console.error("Falha ao carregar mais editais:", err);
    } finally {
      setLoadingMore(false);
    }
  }, [loadingMore, hasMore, email, nextCursor]);

  function handleSetEmail(newEmail: string) {
    window.localStorage.setItem(EMAIL_STORAGE_KEY, newEmail);
    setEmail(newEmail);
    resetAndFetch(newEmail);
    showToast(`Identificado como ${newEmail}`, "gold");
  }

  function handleClearEmail() {
    window.localStorage.removeItem(EMAIL_STORAGE_KEY);
    setEmail(null);
    setEditais((prev) => prev.map((e) => ({ ...e, interested: false })));
    setInterestList([]);
  }

  async function toggleInterest(edital: Edital) {
    if (!email) {
      showToast("Digite seu e-mail para marcar interesse.", "muted", true);
      return;
    }

    const nextValue = !edital.interested;

    // atualizacao otimista: a UI responde na hora, nos dois lugares onde o
    // edital pode aparecer (a pagina carregada de "Todos" e "Meus interesses")
    setEditais((prev) =>
      prev.map((e) => (e.id === edital.id ? { ...e, interested: nextValue } : e)),
    );
    setInterestList((prev) => {
      if (nextValue) {
        if (prev.some((e) => e.id === edital.id)) return prev;
        return [...prev, { ...edital, interested: true }];
      }
      return prev.filter((e) => e.id !== edital.id);
    });
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
      setInterestList((prev) => {
        if (!nextValue) {
          if (prev.some((e) => e.id === edital.id)) return prev;
          return [...prev, { ...edital, interested: true }];
        }
        return prev.filter((e) => e.id !== edital.id);
      });
      showToast("Não foi possível salvar. Tente novamente.", "muted");
    }
  }

  return {
    editais,
    interestList,
    totalCount,
    hasMore,
    loadingMore,
    loadMore,
    live,
    email,
    toast,
    handleSetEmail,
    handleClearEmail,
    toggleInterest,
  };
}
