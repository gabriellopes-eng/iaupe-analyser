import Link from "next/link";
import { Montserrat } from "next/font/google";

import { EditalDetail, formatPtBrDate } from "@/domain/edital";

const montserrat = Montserrat({ subsets: ["latin"], weight: ["400", "600", "700"] });

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

// Visual identico ao email de notificacao (ver saved_record_email_notifier.py
// e email_branding.py: mesmas cores, gradiente, fonte Montserrat e as duas
// logos lado a lado) - so recriado em HTML/CSS de pagina web, porque o HTML
// do email usa recursos (cid: de imagem, tabela de layout fixo) que so
// funcionam dentro de um cliente de email.
export default function EditalDetailView({ edital }: EditalDetailViewProps) {
  return (
    <div className={`detail-page ${montserrat.className}`}>
      <div className="detail-outer">
        <Link href="/" className="detail-back">
          ← Voltar
        </Link>

        <div className="detail-email-card">
          <div className="detail-logos">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/upe_logo_azul.png" alt="UPE" />
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/itt_logo.png" alt="IIT" />
          </div>

          <div className="detail-redbar" />

          <div className="detail-hero">
            <p className="detail-eyebrow">Plataforma de Monitoramento de Editais</p>
            <h1 className="detail-title">{edital.titulo}</h1>
          </div>

          <div className="detail-orgbar">
            <span>
              <span className="detail-orgbar-label">Orgão: </span>
              <span className="detail-orgbar-value">{edital.orgao}</span>
            </span>
            <span className="detail-ref-badge">Ref: {edital.ref}</span>
          </div>

          <div className="detail-body">
            <div className="detail-top-grid">
              <div className="detail-top-cell">
                <p className="detail-field-label">Prazo final de submissão</p>
                <p className="detail-deadline-value">{formatPtBrDate(edital.deadline)}</p>
              </div>
              <div className="detail-top-cell">
                <p className="detail-field-label">Documento oficial</p>
                <a
                  className="detail-pdf-link"
                  href={edital.urlPdf}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  → Acessar edital em PDF
                </a>
              </div>
            </div>

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

          <div className="detail-cta">
            <a
              className="detail-cta-btn"
              href={edital.urlPdf}
              target="_blank"
              rel="noopener noreferrer"
            >
              Acessar Edital Completo
            </a>
          </div>

          <div className="detail-footnote">
            <p>
              Estas informações foram extraídas automaticamente do documento oficial pela
              plataforma de monitoramento de editais.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
