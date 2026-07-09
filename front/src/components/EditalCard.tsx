"use client";

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

// Cartao de edital: apresenta os dados e delega a marcacao de interesse ao container.
export default function EditalCard({ edital, onToggle }: EditalCardProps) {
  const days = daysUntil(edital.deadline);
  const urgency = deadlineUrgency(days);
  const daysLabel = days === null ? "—" : `${days}d`;

  return (
    <article className="card" data-interest={edital.interesse}>
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
          aria-pressed={edital.interesse}
          aria-label={edital.interesse ? "Remover dos interesses" : "Marcar como interesse"}
          onClick={(e) => {
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

      <div className="status-line">
        {edital.interesse ? (
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
