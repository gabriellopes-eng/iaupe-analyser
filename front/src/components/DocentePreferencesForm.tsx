"use client";

import { useEffect, useState } from "react";

import { AREAS_INTERESSE_OPTIONS, SEGMENTOS_OPTIONS } from "@/domain/docente";

interface DocentePreferencesFormProps {
  // e-mail ja identificado pelo EmailGate na tela inicial - este componente
  // nao pede e-mail de novo, so reage a ele.
  email: string | null;
  showToast: (message: string, tone: "gold" | "muted") => void;
}

// Painel embutido na tela inicial (nao e mais uma pagina separada): deixa o
// docente marcar as areas de interesse e os segmentos que quer acompanhar,
// reaproveitando a identidade ja capturada pelo EmailGate e o toast ja
// existente na pagina - sem pedir e-mail de novo, sem navegar pra outro lugar.
export default function DocentePreferencesForm({ email, showToast }: DocentePreferencesFormProps) {
  const [loadingPrefs, setLoadingPrefs] = useState(false);
  const [areas, setAreas] = useState<Set<string>>(new Set());
  const [segmentos, setSegmentos] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!email) {
      setAreas(new Set());
      setSegmentos(new Set());
      return;
    }
    let cancelled = false;
    setLoadingPrefs(true);
    fetch(`/api/docentes?email=${encodeURIComponent(email)}`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ areasInteresse: string[]; segmentos: string[] }>;
      })
      .then((data) => {
        if (cancelled) return;
        setAreas(new Set(data.areasInteresse));
        setSegmentos(new Set(data.segmentos));
      })
      .catch((err) => {
        console.error("Falha ao carregar preferências:", err);
        if (!cancelled) showToast("Não foi possível carregar suas preferências.", "muted");
      })
      .finally(() => {
        if (!cancelled) setLoadingPrefs(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [email]);

  function toggle(set: Set<string>, setSet: (s: Set<string>) => void, value: string) {
    const next = new Set(set);
    if (next.has(value)) next.delete(value);
    else next.add(value);
    setSet(next);
  }

  async function handleSave() {
    if (!email) return;
    setSaving(true);
    try {
      const res = await fetch("/api/docentes", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          areasInteresse: Array.from(areas),
          segmentos: Array.from(segmentos),
        }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      showToast("Preferências salvas!", "gold");
    } catch (err) {
      console.error("Falha ao salvar preferências:", err);
      showToast("Não foi possível salvar. Tente novamente.", "muted");
    } finally {
      setSaving(false);
    }
  }

  if (!email) {
    return (
      <div className="preferences">
        <h2 className="preferences-title">Minhas áreas de interesse</h2>
        <p className="preferences-lead">
          Digite seu e-mail acima para configurar as áreas e os segmentos que você quer
          acompanhar.
        </p>
      </div>
    );
  }

  return (
    <div className="preferences">
      <h2 className="preferences-title">Minhas áreas de interesse</h2>
      <p className="preferences-lead">
        Escolha as áreas e os segmentos que você acompanha para receber notificações por e-mail
        quando surgir um edital novo compatível.
      </p>

      {loadingPrefs ? (
        <p className="preferences-loading">Carregando suas preferências...</p>
      ) : (
        <>
          <section className="preferences-group">
            <h3>Áreas de interesse</h3>
            <div className="chip-group" role="group" aria-label="Áreas de interesse">
              {AREAS_INTERESSE_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className="area-chip"
                  aria-pressed={areas.has(option)}
                  onClick={() => toggle(areas, setAreas, option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </section>

          <section className="preferences-group">
            <h3>Segmentos</h3>
            <div className="chip-group" role="group" aria-label="Segmentos">
              {SEGMENTOS_OPTIONS.map((option) => (
                <button
                  key={option}
                  type="button"
                  className="segmento-chip"
                  aria-pressed={segmentos.has(option)}
                  onClick={() => toggle(segmentos, setSegmentos, option)}
                >
                  {option}
                </button>
              ))}
            </div>
          </section>

          <button type="button" className="preferences-save" onClick={handleSave} disabled={saving}>
            {saving ? "Salvando..." : "Salvar preferências"}
          </button>
        </>
      )}
    </div>
  );
}
