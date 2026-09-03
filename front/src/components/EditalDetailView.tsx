import Link from "next/link";

import {
  EditalDetail,
  daysUntil,
  deadlineUrgency,
  formatPtBrDate,
} from "@/domain/edital";
import { ClockIcon } from "@/components/icons";

interface EditalDetailViewProps {
  edital: EditalDetail;
}

// Campo de texto/lista com o mesmo fallback do email (ver render_list em
// saved_record_email_notifier.py): "Nao informado." em vez de sumir ou
// quebrar o layout quando o campo vem vazio.
function DetailField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="detail-field">
      <p className="detail-field-label">{label}</p>
      {children}
    </div>
  );
}

function ListOrEmpty({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="detail-empty">Não informado.</p>;
  return (
    <ul className="detail-list">
      {items.map((item) => (
        <li key={item}>{item}</li>
      ))}
    </ul>
  );
}

function BadgesOrEmpty({ items }: { items: string[] }) {
  if (items.length === 0) return <p className="detail-empty">Não informado.</p>;
  return (
    <div className="detail-badges">
      {items.map((item) => (
        <span className="detail-badge" key={item}>
          {item}
        </span>
      ))}
    </div>
  );
}

// Pagina de detalhamento do edital. Segue a mesma linguagem visual do resto do
// site (tokens.css, cards.css): um unico cartao, sem recriar o cabecalho de
// marca do email de notificacao - o header institucional ja vem do layout
// global (app/layout.tsx). O conteudo (campos extraidos pela pipeline) e o
// mesmo que o email mostra (ver pipeline/emails/saved_record_email_notifier.py).
export default function EditalDetailView({ edital }: EditalDetailViewProps) {
  const days = daysUntil(edital.deadline);
  const urgency = deadlineUrgency(days);

  return (
    <div className="detail-page">
      <div className="detail-outer">
        <Link href="/" className="detail-back">
          ← Voltar
        </Link>

        <article className="detail-card">
          <header className="detail-head">
            <div className="detail-head-top">
              <span className="src-chip">
                <span className="src-dot" style={{ background: edital.color }} />
                {edital.sourceLabel}
              </span>
              <span className="detail-ref">Ref: {edital.ref}</span>
            </div>
            <h1 className="detail-title">{edital.titulo}</h1>
            <p className="detail-org">{edital.orgao}</p>
          </header>

          <div className="detail-meta">
            <span className={`deadline ${urgency}`}>
              <ClockIcon />
              {formatPtBrDate(edital.deadline)}
              {days !== null && (
                <>
                  {" · "}
                  <span className="days">{days}d</span>
                </>
              )}
            </span>
            <a
              className="detail-pdf-link"
              href={edital.urlPdf}
              target="_blank"
              rel="noopener noreferrer"
            >
              → Acessar edital em PDF
            </a>
          </div>

          <div className="detail-body">
            <DetailField label="Público-alvo">
              <p className="detail-text">{edital.publicoAlvo || "Não informado."}</p>
            </DetailField>

            <DetailField label="Resumo do Edital">
              <p className="detail-text">{edital.descricao || "Não informado."}</p>
            </DetailField>

            <div className="detail-two-col">
              <DetailField label="Áreas de interesse">
                <BadgesOrEmpty items={edital.areas} />
              </DetailField>
              <DetailField label="Segmentos">
                <BadgesOrEmpty items={edital.segmentos} />
              </DetailField>
            </div>

            <DetailField label="Critérios do público-alvo">
              <ListOrEmpty items={edital.criteriosPublicoAlvo} />
            </DetailField>

            <DetailField label="Quem pode submeter">
              <ListOrEmpty items={edital.criteriosProponente} />
            </DetailField>

            <DetailField label="Cronograma">
              <ListOrEmpty items={edital.cronograma} />
            </DetailField>

            <div className="detail-field detail-field-last">
              <p className="detail-field-label">Observações</p>
              <ListOrEmpty items={edital.observacoes} />
            </div>
          </div>

          <p className="detail-note">
            Estas informações foram extraídas automaticamente do documento oficial pela
            plataforma de monitoramento de editais. Consulte sempre o edital em PDF para os
            termos completos.
          </p>
        </article>
      </div>
    </div>
  );
}
