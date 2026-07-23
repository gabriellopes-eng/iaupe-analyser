import { AlertIcon, OutlineStarIcon } from "@/components/icons";

interface EditaisEmptyStateProps {
  live: boolean;
  hasEmail: boolean;
}

// Estado vazio da vitrine: sistema fora do ar, ou nenhum edital marcado ainda.
export default function EditaisEmptyState({ live, hasEmail }: EditaisEmptyStateProps) {
  if (!live) {
    return (
      <div className="empty empty-error">
        <AlertIcon />
        <p>
          O sistema está fora do ar no momento - não foi possível carregar os editais. Tente
          novamente em alguns instantes.
        </p>
      </div>
    );
  }

  return (
    <div className="empty">
      <OutlineStarIcon />
      <p>
        {hasEmail
          ? "Você ainda não marcou nenhum edital. Toque na estrela de um edital para começar a receber os lembretes dele."
          : "Digite seu e-mail acima e toque na estrela de um edital para começar a receber lembretes."}
      </p>
    </div>
  );
}
