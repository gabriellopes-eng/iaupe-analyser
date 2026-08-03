"use client";

import { useRouter } from "next/navigation";

import {
  Edital,
  daysUntil,
  deadlineUrgency,
  formatPtBrDate,
} from "@/domain/edital";
import { BellIcon, ClockIcon, OutlineStarIcon, StarIcon } from "@/components/icons";

interface EditalCardProps {
  edital: Edital;
  onToggle: (edital: Edital) => void;
}

// Cartao de edital: apresenta os dados e delega a marcacao de interesse (por
// e-mail, sem autenticacao) ao container. O card inteiro navega pra pagina de
// detalhamento (/editais/[id]) ao clicar - exceto a estrela e o link "Acessar
// Edital", que tem sua propria acao e por isso interrompem a propagacao do
// clique (senao os dois cliques disparariam juntos).
export default function EditalCard({ edital, onToggle }: EditalCardProps) {
  const router = useRouter();
  const days = daysUntil(edital.deadline);
  const urgency = deadlineUrgency(days);
  const daysLabel = days === null ? "-" : `${days}d`;

  function goToDetail() {
    router.push(`/editais/${edital.id}`);
  }

  return (
    <article
      className="card"
      data-interest={edital.interested}
      role="link"
      tabIndex={0}
      onClick={goToDetail}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          goToDetail();
        }
      }}
    >
      <div className="card-head">
        <div>
          <span className="src-chip">
            <span className="src-dot" style={{ background: edital.color }} />
            {edital.sourceLabel}
          </span>
          <div className="ref">Ref: {edital.ref}</div>
        </div>
        <button
          className="star"
          type="button"
          aria-pressed={edital.interested}
          aria-label={edital.interested ? "Remover dos interesses" : "Marcar como interesse"}
          onClick={(e) => {
            e.stopPropagation();
            const btn = e.currentTarget;
            btn.classList.remove("pop");
            void btn.offsetWidth;
            btn.classList.add("pop");
            onToggle(edital);
          }}
        >
          <StarIcon />
        </button>
      </div>

      <h3 className="title">{edital.titulo}</h3>
      <p className="org">{edital.orgao}</p>

      <div className="meta-row">
        <span className={`deadline ${urgency}`}>
          <ClockIcon />
          {formatPtBrDate(edital.deadline)}
          {days !== null && (
            <>
              {" · "}
              <span className="days">{daysLabel}</span>
            </>
          )}
        </span>
        {edital.areas.map((area) => (
          <span className="area-tag" key={area}>
            {area}
          </span>
        ))}
      </div>

      <a
        className="card-link"
        href={edital.urlPdf}
        target="_blank"
        rel="noopener noreferrer"
        onClick={(e) => e.stopPropagation()}
      >
        Acessar Edital
      </a>

      <div className="status-line">
        {edital.interested ? (
          <>
            <BellIcon /> Você recebe os lembretes deste edital
          </>
        ) : (
          <>
            <OutlineStarIcon /> Marque para receber lembretes de prazo
          </>
        )}
      </div>
    </article>
  );
}
