"use client";

import { useEffect, useMemo, useState } from "react";

import { Edital, daysUntil } from "@/domain/edital";
import EditalCard from "@/components/EditalCard";
import EmailGate from "@/components/EmailGate";
import StatTile from "@/components/StatTile";
import Toast from "@/components/Toast";
import Toolbar, { ViewMode } from "@/components/Toolbar";
import { InfoIcon, OutlineStarIcon } from "@/components/icons";

const EMAIL_STORAGE_KEY = "iaupe:email";

interface EditaisViewProps {
  initialEditais: Edital[];
  live: boolean;
}

interface ToastState {
  message: string;
  tone: "gold" | "muted";
  show: boolean;
}

// Container interativo: mantem o estado dos editais e a identificacao por
// e-mail (sem autenticacao - so o endereco digitado, guardado no navegador),
// e persiste a marcacao de interesse via API (com atualizacao otimista).
export default function EditaisView({ initialEditais, live }: EditaisViewProps) {
  const [editais, setEditais] = useState<Edital[]>(initialEditais);
  const [email, setEmail] = useState<string | null>(null);
  const [view, setView] = useState<ViewMode>("all");
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

  async function refetchEditais(currentEmail: string) {
    try {
      const res = await fetch(`/api/editais?email=${encodeURIComponent(currentEmail)}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = (await res.json()) as { editais: Edital[] };
      setEditais(data.editais);
    } catch (err) {
      console.error("Falha ao recarregar editais com e-mail:", err);
    }
  }

  const interestList = useMemo(() => editais.filter((e) => e.interested), [editais]);
  const urgentInterest = useMemo(
    () => interestList.filter((e) => {
      const d = daysUntil(e.deadline);
      return d !== null && d >= 0 && d <= 7;
    }).length,
    [interestList],
  );

  const visible = view === "mine" ? interestList : editais;

  function handleSetEmail(newEmail: string) {
    window.localStorage.setItem(EMAIL_STORAGE_KEY, newEmail);
    setEmail(newEmail);
    refetchEditais(newEmail);
    setToast({ message: `Identificado como ${newEmail}`, tone: "gold", show: true });
    window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
  }

  function handleClearEmail() {
    window.localStorage.removeItem(EMAIL_STORAGE_KEY);
    setEmail(null);
    setEditais((prev) => prev.map((e) => ({ ...e, interested: false })));
  }

  async function toggle(edital: Edital) {
    if (!email) {
      setToast({ message: "Digite seu e-mail para marcar interesse.", tone: "muted", show: true });
      window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
      return;
    }

    const nextValue = !edital.interested;

    // atualizacao otimista: a UI responde na hora
    setEditais((prev) =>
      prev.map((e) => (e.id === edital.id ? { ...e, interested: nextValue } : e)),
    );
    flashToast(edital.titulo, nextValue);

    try {
      const res = await fetch(`/api/editais/${edital.id}/interest`, { //
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
      setToast({ message: "Não foi possível salvar. Tente novamente.", tone: "muted", show: true });
      window.setTimeout(() => setToast((t) => ({ ...t, show: false })), 2600);
    }
  }

  function flashToast(titulo: string, added: boolean) {
    const short = titulo.length > 40 ? `${titulo.slice(0, 37)}...` : titulo;
    setToast({
      message: added
        ? `Marcado: ${short}. Você receberá os lembretes`
        : `Removido: ${short}`,
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
          Marque os editais específicos que você acompanha. Os lembretes de prazo (D-30, D-15 e
          D-7) chegam por e-mail <b>somente para os selecionados</b>, sem o ruído de todas as
          chamadas abertas.
        </p>
      </section>

      <EmailGate email={email} onSetEmail={handleSetEmail} onClearEmail={handleClearEmail} />

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
      />

      {visible.length === 0 ? (
        <div className="empty">
          <OutlineStarIcon />
          <p>
            {email
              ? "Você ainda não marcou nenhum edital. Toque na estrela de um edital para começar a receber os lembretes dele."
              : "Digite seu e-mail acima e toque na estrela de um edital para começar a receber lembretes."}
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
              <b>Conectado ao MongoDB.</b> A marcação grava seu e-mail na lista{" "}
              <code>interessados</code> do edital; os lembretes de prazo avisam cada pessoa
              individualmente, sem expor o e-mail de ninguém.
            </>
          ) : (
            <>
              <b>Modo demonstração (mock).</b> Sem <code>MONGODB_URI</code> configurado, os dados
              são ilustrativos. Com o banco conectado, a marcação grava seu e-mail na lista{" "}
              <code>interessados</code> daquele edital específico.
            </>
          )}
        </span>
      </footer>

      <Toast message={toast.message} show={toast.show} tone={toast.tone} />
    </div>
  );
}
