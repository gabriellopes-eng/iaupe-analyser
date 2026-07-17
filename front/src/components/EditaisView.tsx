"use client";

import { useMemo, useState } from "react";

import { Edital, SourceKey, SourcePreferences, daysUntil } from "@/domain/edital";
import EditalCard from "@/components/EditalCard";
import FontesToggle from "@/components/FontesToggle";
import StatTile from "@/components/StatTile";
import Toast from "@/components/Toast";
import Toolbar, { ViewMode } from "@/components/Toolbar";
import { BellIcon, InfoIcon } from "@/components/icons";

interface EditaisViewProps {
  initialEditais: Edital[];
  initialPreferences: SourcePreferences;
  live: boolean;
}

interface ToastState {
  message: string;
  tone: "gold" | "muted";
  show: boolean;
}

// Container interativo: mantem a lista de editais e as preferencias de fonte,
// e persiste o toggle de fonte via API (com atualizacao otimista).
export default function EditaisView({ initialEditais, initialPreferences, live }: EditaisViewProps) {
  const [editais] = useState<Edital[]>(initialEditais);
  const [preferences, setPreferences] = useState<SourcePreferences>(initialPreferences);
  const [view, setView] = useState<ViewMode>("all");
  const [toast, setToast] = useState<ToastState>({ message: "", tone: "gold", show: false });

  const followedList = useMemo(
    () => editais.filter((e) => preferences[e.source]),
    [editais, preferences],
  );
  const followedSourcesCount = useMemo(
    () => Object.values(preferences).filter(Boolean).length,
    [preferences],
  );
  const urgentFollowed = useMemo(
    () => followedList.filter((e) => {
      const d = daysUntil(e.deadline);
      return d !== null && d >= 0 && d <= 7;
    }).length,
    [followedList],
  );

  const visible = view === "mine" ? followedList : editais;

  async function toggleSource(source: SourceKey) {
    const nextValue = !preferences[source];

    // atualizacao otimista: a UI responde na hora
    setPreferences((prev) => ({ ...prev, [source]: nextValue }));
    flashToast(source, nextValue);

    try {
      const res = await fetch("/api/preferencias", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source, followed: nextValue }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { preferences?: SourcePreferences };
      if (data.preferences) setPreferences(data.preferences);
    } catch (err) {
      // reverte em caso de falha na persistencia
      console.error("Falha ao salvar preferencia de fonte:", err);
      setPreferences((prev) => ({ ...prev, [source]: !nextValue }));
      setToast({ message: "Não foi possível salvar. Tente novamente.", tone: "muted", show: true });
      window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
    }
  }

  function flashToast(source: SourceKey, added: boolean) {
    const label = source.toUpperCase();
    setToast({
      message: added
        ? `${label} ligada — você receberá os lembretes de prazo dela`
        : `${label} desligada — sem mais lembretes dela`,
      tone: added ? "gold" : "muted",
      show: true,
    });
    window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
  }

  return (
    <div className="wrap">
      <section className="intro">
        <h1>
          Editais por fonte
          <span className={`badge-live ${live ? "on" : "off"}`}>{live ? "AO VIVO" : "DEMO"}</span>
        </h1>
        <p>
          Escolha as fontes que você acompanha. Os lembretes de prazo (D-30, D-15 e D-7) chegam por
          e-mail <b>de todo edital das fontes ligadas</b> — sem precisar marcar edital por edital.
        </p>
      </section>

      <FontesToggle preferences={preferences} onToggle={toggleSource} />

      <section className="stats" aria-label="Resumo">
        <StatTile label="Editais monitorados" value={editais.length} sub="FACEPE · CNPq · FINEP · CAPES" />
        <StatTile
          label="Fontes seguidas"
          value={followedSourcesCount}
          sub={followedSourcesCount === 0 ? "nenhuma ligada" : `de 4 fontes · ${followedList.length} editais`}
          variant="gold"
        />
        <StatTile
          label="Prazo em ≤ 7 dias"
          value={urgentFollowed}
          sub={urgentFollowed === 0 ? "nada urgente nas suas fontes" : "entre as suas fontes seguidas"}
          variant="red"
        />
      </section>

      <Toolbar
        view={view}
        totalCount={editais.length}
        followedCount={followedList.length}
        onViewChange={setView}
      />

      {visible.length === 0 ? (
        <div className="empty">
          {view === "mine" ? <BellIcon /> : <InfoIcon />}
          <p>
            {view === "mine"
              ? "Nenhuma fonte ligada ainda. Ligue ao menos uma fonte no topo para começar a receber lembretes."
              : "Nenhum edital encontrado no momento."}
          </p>
        </div>
      ) : (
        <div className="grid">
          {visible.map((edital) => (
            <EditalCard key={edital.id} edital={edital} followed={preferences[edital.source]} />
          ))}
        </div>
      )}

      <footer className="note">
        <InfoIcon />
        <span>
          {live ? (
            <>
              <b>Conectado ao MongoDB.</b> O toggle de fonte grava a lista de fontes seguidas em{" "}
              <code>preferencias_usuario</code>; os lembretes só disparam para fontes nessa lista.
            </>
          ) : (
            <>
              <b>Modo demonstração (mock).</b> Sem <code>MONGODB_URI</code> configurado, os dados são
              ilustrativos. Com o banco conectado, o toggle grava a fonte seguida em{" "}
              <code>preferencias_usuario</code>, usada pelos lembretes de prazo.
            </>
          )}
        </span>
      </footer>

      <Toast message={toast.message} show={toast.show} tone={toast.tone} />
    </div>
  );
}
