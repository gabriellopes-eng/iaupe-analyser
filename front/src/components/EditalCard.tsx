"use client";

import {
  Edital,
  daysUntil,
  deadlineUrgency,
  formatPtBrDate,
} from "@/domain/edital";
import { BellIcon, ClockIcon, InfoIcon } from "@/components/icons";

interface EditalCardProps {
  edital: Edital;
  followed: boolean;
}

// Cartao de edital: somente apresentacao. Quem decide notificar ou nao e o
// toggle da fonte (FontesToggle), nao o card individual.
export default function EditalCard({ edital, followed }: EditalCardProps) {
  const days = daysUntil(edital.deadline);
  const urgency = deadlineUrgency(days);
  const daysLabel = days === null ? "-" : `${days}d`;

  return (
    <article className="card" data-followed={followed}>
      <div className="card-head">
        <div>
          <span className="src-chip">
            <span className="src-dot" style={{ background: edital.color }} />
            {edital.sourceLabel}
          </span>
          <div className="ref">Ref: {edital.ref}</div>
        </div>
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
        {followed ? (
          <>
            <BellIcon /> Você recebe lembretes de {edital.sourceLabel}
          </>
        ) : (
          <>
            <InfoIcon /> Ligue {edital.sourceLabel} no topo para receber lembretes
          </>
        )}
      </div>
    </article>
  );
}
