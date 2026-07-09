interface StatTileProps {
  label: string;
  value: number;
  sub: string;
  variant?: "blue" | "gold" | "red";
}

// Bloco de resumo (KPI). Componente apresentacional puro.
export default function StatTile({ label, value, sub, variant = "blue" }: StatTileProps) {
  const cls = variant === "gold" ? "tile gold" : variant === "red" ? "tile red" : "tile";
  return (
    <div className={cls}>
      <p className="tile-label">{label}</p>
      <div className="tile-num">{value}</div>
      <p className="tile-sub">{sub}</p>
    </div>
  );
}
