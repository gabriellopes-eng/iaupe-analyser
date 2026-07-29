"use client";

import { SOURCES, SourceKey } from "@/domain/edital";

export type ViewMode = "all" | "mine";

interface ToolbarProps {
  view: ViewMode;
  totalCount: number;
  interestCount: number;
  onViewChange: (view: ViewMode) => void;
  selectedSources: SourceKey[];
  onToggleSource: (source: SourceKey) => void;
}

// Barra de filtro: Todos os editais x apenas os marcados como interesse,
// mais o filtro por fonte (Facepe/CNPq/Finep/Capes, varias ao mesmo tempo).
export default function Toolbar({
  view,
  totalCount,
  interestCount,
  onViewChange,
  selectedSources,
  onToggleSource,
}: ToolbarProps) {
  return (
    <div className="toolbar">
      <div className="toolbar-row">
        <div className="segmented" role="tablist" aria-label="Filtro de editais">
          <button
            className="seg"
            role="tab"
            aria-selected={view === "all"}
            type="button"
            onClick={() => onViewChange("all")}
          >
            Todos <span className="count">{totalCount}</span>
          </button>
          <button
            className="seg"
            role="tab"
            aria-selected={view === "mine"}
            type="button"
            onClick={() => onViewChange("mine")}
          >
            Meus interesses <span className="count">{interestCount}</span>
          </button>
        </div>
      </div>
      <div className="toolbar-row toolbar-row-sources">
        <span className="toolbar-label">Fonte</span>
        <div className="source-filter" role="group" aria-label="Filtro por fonte">
          {(Object.keys(SOURCES) as SourceKey[]).map((key) => {
            const meta = SOURCES[key];
            const active = selectedSources.includes(key);
            return (
              <button
                key={key}
                className="source-chip"
                aria-pressed={active}
                type="button"
                onClick={() => onToggleSource(key)}
              >
                <span className="src-dot" style={{ background: meta.color }} />
                {meta.label}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
