"use client";

import { useEffect, useRef } from "react";

// Mecanismo generico de scroll infinito: observa um elemento sentinela (o
// `ref` devolvido) e chama `onLoadMore` quando ele entra na tela. Nao sabe
// nada sobre editais, paginacao ou cursor - so "avisa quando chegou perto do
// fim". Quem usa decide o que "carregar mais" significa.
// `enabled` desliga o observer quando nao faz sentido chamar onLoadMore
// (ex: a lista acabou, ou a visao atual nem e paginada).
export function useInfiniteScroll(enabled: boolean, onLoadMore: () => void) {
  const sentinelRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!enabled) return;
    const node = sentinelRef.current;
    if (!node) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0]?.isIntersecting) onLoadMore();
      },
      { rootMargin: "200px" },
    );
    observer.observe(node);
    return () => observer.disconnect();
  }, [enabled, onLoadMore]);

  return sentinelRef;
}
