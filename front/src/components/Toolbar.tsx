"use client";

export type ViewMode = "all" | "mine";

interface ToolbarProps {
  view: ViewMode;
  totalCount: number;
  followedCount: number;
  onViewChange: (view: ViewMode) => void;
}

// Barra de filtro: Todos os editais x apenas os das fontes seguidas.
export default function Toolbar({
  view,
  totalCount,
  followedCount,
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
          Minhas fontes <span className="count">{followedCount}</span>
        </button>
      </div>
    </div>
  );
}
