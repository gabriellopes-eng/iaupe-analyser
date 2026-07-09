"use client";

import { useMemo, useState } from "react";

import { Edital, daysUntil } from "@/domain/edital";
import EditalCard from "@/components/EditalCard";
import StatTile from "@/components/StatTile";
import Toast from "@/components/Toast";
import Toolbar, { ViewMode } from "@/components/Toolbar";
import { InfoIcon, OutlineStarIcon } from "@/components/icons";

interface EditaisViewProps {
  initialEditais: Edital[];
  live: boolean;
}

interface ToastState {
  message: string;
  tone: "gold" | "muted";
  show: boolean;
}

// Container interativo: mantem o estado dos editais, aplica o filtro e
// persiste a marcacao de interesse via API (com atualizacao otimista).
export default function EditaisView({ initialEditais, live }: EditaisViewProps) {
  const [editais, setEditais] = useState<Edital[]>(initialEditais);
  const [view, setView] = useState<ViewMode>("all");
  const [onlyInterest, setOnlyInterest] = useState(true);
  const [toast, setToast] = useState<ToastState>({ message: "", tone: "gold", show: false });

  const interestList = useMemo(() => editais.filter((e) => e.interesse), [editais]);
  const urgentInterest = useMemo(
    () => interestList.filter((e) => {
      const d = daysUntil(e.deadline);
      return d !== null && d >= 0 && d <= 7;
    }).length,
    [interestList],
  );

  const visible = view === "mine" ? interestList : editais;

  async function toggle(edital: Edital) {
    const nextValue = !edital.interesse;

    // atualizacao otimista: a UI responde na hora
    setEditais((prev) =>
      prev.map((e) => (e.id === edital.id ? { ...e, interesse: nextValue } : e)),
    );
    flashToast(edital.sourceLabel, nextValue);

    try {
      const res = await fetch(`/api/editais/${edital.id}/interest`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ interested: nextValue }),
      });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
    } catch (err) {
      // reverte em caso de falha na persistencia
      console.error("Falha ao salvar interesse:", err);
      setEditais((prev) =>
        prev.map((e) => (e.id === edital.id ? { ...e, interesse: !nextValue } : e)),
      );
      setToast({ message: "Não foi possível salvar. Tente novamente.", tone: "muted", show: true });
      window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
    }
  }

  function flashToast(sourceLabel: string, added: boolean) {
    setToast({
      message: added
        ? `${sourceLabel} adicionado — você receberá os lembretes de prazo`
        : `${sourceLabel} removido dos seus interesses`,
      tone: added ? "gold" : "muted",
      show: true,
    });
    window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
  }

  return (
    <div className="wrap">
      <section className="intro">
        <h1>
          Seus editais de interesse
          <span className={`badge-live ${live ? "on" : "off"}`}>{live ? "AO VIVO" : "DEMO"}</span>
        </h1>
        <p>
          Marque os editais que você acompanha. Os lembretes de prazo (D-30, D-15 e D-7) chegam por
          e-mail <b>somente para os selecionados</b> — sem o ruído de todas as chamadas abertas.
        </p>
      </section>

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
        onlyInterest={onlyInterest}
        onViewChange={setView}
        onOnlyInterestChange={setOnlyInterest}
      />

      {visible.length === 0 ? (
        <div className="empty">
          <OutlineStarIcon />
          <p>
            Você ainda não marcou nenhum edital. Toque na estrela de um edital para começar a receber
            os lembretes dele.
          </p>
        </div>
      ) : (
        <div className="grid">
          {visible.map((edital) => (
            <EditalCard key={edital.id} edital={edital} onToggle={toggle} />
          ))}
        </div>
      )}

      <footer className="note">
        <InfoIcon />
        <span>
          {live ? (
            <>
              <b>Conectado ao MongoDB.</b> A marcação grava o campo <code>interesse</code> no
              documento do edital; os lembretes usam a flag <code>--only-interest</code> da pipeline.
            </>
          ) : (
            <>
              <b>Modo demonstração (mock).</b> Sem <code>MONGODB_URI</code> configurado, os dados são
              ilustrativos. Com o banco conectado, a marcação grava o campo <code>interesse</code>{" "}
              usado pelos lembretes <code>--only-interest</code>.
            </>
          )}
        </span>
      </footer>

      <Toast message={toast.message} show={toast.show} tone={toast.tone} />
    </div>
  );
}
