"use client";

import { SOURCES, SourceKey, SourcePreferences } from "@/domain/edital";

interface FontesToggleProps {
  preferences: SourcePreferences;
  onToggle: (source: SourceKey) => void;
}

// Painel de assinatura: liga/desliga cada fonte (FACEPE/CNPq/FINEP/CAPES).
// Fonte ligada = todo edital dela entra nos lembretes de prazo por e-mail.
export default function FontesToggle({ preferences, onToggle }: FontesToggleProps) {
  return (
    <section className="sources-panel" aria-label="Fontes seguidas">
      <div className="sources-head">
        <h2>Fontes que você acompanha</h2>
        <p>
          Ligue as agências de fomento cujos editais devem gerar lembrete de prazo
          (D-30, D-15 e D-7) por e-mail. Fonte desligada não notifica.
        </p>
      </div>
      <div className="sources-list">
        {Object.values(SOURCES).map((meta) => {
          const followed = preferences[meta.key];
          return (
            <div className="source-row" key={meta.key}>
              <span className="src-chip">
                <span className="src-dot" style={{ background: meta.color }} />
                {meta.label}
              </span>
              <span className="source-org">{meta.orgao}</span>
              <div className="switch-wrap">
                <button
                  className="switch"
                  type="button"
                  role="switch"
                  aria-checked={followed}
                  aria-label={`Seguir editais da fonte ${meta.label}`}
                  onClick={() => onToggle(meta.key)}
                />
              </div>
            </div>
          );
        })}
      </div>
    </section>
  );
}
