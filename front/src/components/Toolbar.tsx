"use client";

export type ViewMode = "all" | "mine";

interface ToolbarProps {
  view: ViewMode;
  totalCount: number;
  interestCount: number;
  onViewChange: (view: ViewMode) => void;
}

// Barra de filtro: Todos os editais x apenas os marcados como interesse.
export default function Toolbar({
  view,
  totalCount,
  interestCount,
  onViewChange,
}: ToolbarProps) {
  return (
    <div className="toolbar">
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
  );
}
