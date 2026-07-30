"use client";

import { useMemo, useState } from "react";

import { Edital, SourceKey, daysUntil } from "@/domain/edital";
import { useEditaisState } from "@/hooks/useEditaisState";
import ConnectionNote from "@/components/ConnectionNote";
import EditalCard from "@/components/EditalCard";
import EditaisEmptyState from "@/components/EditaisEmptyState";
import EmailGate from "@/components/EmailGate";
import StatTile from "@/components/StatTile";
import Toast from "@/components/Toast";
import Toolbar, { ViewMode } from "@/components/Toolbar";

interface EditaisViewProps {
  initialEditais: Edital[];
  live: boolean;
}

// Container interativo: o estado e as chamadas de API ficam no hook
// useEditaisState; aqui so entra a apresentacao (JSX) do painel de editais.
// Sem dado fake: se o Mongo estiver fora do ar, mostra isso claramente em vez
// de uma demonstracao ilustrativa.
export default function EditaisView({ initialEditais, live: initialLive }: EditaisViewProps) {
  const { editais, live, email, toast, handleSetEmail, handleClearEmail, toggleInterest } =
    useEditaisState(initialEditais, initialLive);
  const [view, setView] = useState<ViewMode>("all");
  const [selectedSources, setSelectedSources] = useState<SourceKey[]>([]);
  const [query, setQuery] = useState("");

  function toggleSource(source: SourceKey) {
    setSelectedSources((prev) =>
      prev.includes(source) ? prev.filter((s) => s !== source) : [...prev, source],
    );
  }

  const interestList = useMemo(() => editais.filter((e) => e.interested), [editais]);
  const urgentInterest = useMemo(
    () => interestList.filter((e) => {
      const d = daysUntil(e.deadline);
      return d !== null && d >= 0 && d <= 7;
    }).length,
    [interestList],
  );

  const byView = view === "mine" ? interestList : editais;
  const bySource = selectedSources.length
    ? byView.filter((e) => selectedSources.includes(e.source))
    : byView;
  const q = query.trim().toLowerCase();
  const visible = q ? bySource.filter((e) => e.titulo.toLowerCase().includes(q)) : bySource;

  return (
    <div className="wrap">
      <section className="intro">
        <h1>
          Seus editais de interesse
          <span className={`badge-live ${live ? "on" : "off"}`}>
            {live ? "AO VIVO" : "FORA DO AR"}
          </span>
        </h1>
        <p>
          Marque os editais específicos que você acompanha. Os lembretes de prazo (D-30, D-15 e
          D-7) chegam por e-mail <b>somente para os selecionados</b>, sem o ruído de todas as
          chamadas abertas.
        </p>
      </section>

      {live && <EmailGate email={email} onSetEmail={handleSetEmail} onClearEmail={handleClearEmail} />}

      <section className="stats" aria-label="Resumo">
        <StatTile label="Editais monitorados" value={editais.length} sub="FACEPE · CNPq · FINEP · CAPES" />
        <StatTile
          label="De interesse"
          value={interestList.length}
          sub={interestList.length === 0 ? "nenhum selecionado" : "recebendo lembretes"}
          variant="gold"
        />
        <StatTile
          label="Prazo em ≤ 7 dias"
          value={urgentInterest}
          sub={urgentInterest === 0 ? "nada urgente selecionado" : "entre os seus selecionados"}
          variant="red"
        />
      </section>

      <Toolbar
        view={view}
        totalCount={editais.length}
        interestCount={interestList.length}
        onViewChange={setView}
        selectedSources={selectedSources}
        onToggleSource={toggleSource}
        query={query}
        onQueryChange={setQuery}
      />

      {!live || visible.length === 0 ? (
        <EditaisEmptyState live={live} hasEmail={Boolean(email)} />
      ) : (
        <div className="grid">
          {visible.map((edital) => (
            <EditalCard key={edital.id} edital={edital} onToggle={toggleInterest} />
          ))}
        </div>
      )}

      <ConnectionNote live={live} />

      <Toast message={toast.message} show={toast.show} tone={toast.tone} />
    </div>
  );
}
