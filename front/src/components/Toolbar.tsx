"use client";

export type ViewMode = "all" | "mine";

interface ToolbarProps {
  view: ViewMode;
  totalCount: number;
  interestCount: number;
  onlyInterest: boolean;
  onViewChange: (view: ViewMode) => void;
  onOnlyInterestChange: (value: boolean) => void;
}

// Barra de controle: filtro Todos/Meus interesses + switch de lembretes.
export default function Toolbar({
  view,
  totalCount,
  interestCount,
  onlyInterest,
  onViewChange,
  onOnlyInterestChange,
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

      <div className="switch-wrap">
        <span className="switch-label">
          <b>Lembretes só dos interesses</b>
          <br />
          filtra o envio de e-mails
        </span>
        <button
          className="switch"
          type="button"
          role="switch"
          aria-checked={onlyInterest}
          aria-label="Enviar lembretes apenas dos editais de interesse"
          onClick={() => onOnlyInterestChange(!onlyInterest)}
        />
      </div>
    </div>
  );
}
