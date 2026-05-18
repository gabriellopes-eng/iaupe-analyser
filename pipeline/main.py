import argparse
import os
from orchestration.deadline_reminder_runner import run_deadline_reminders
from orchestration.pipeline_runner import run_pipeline
from orchestration.settings import parse_limit
from orchestration.source_registry import DEFAULT_SOURCE, SOURCE_REGISTRY


def build_parser() -> argparse.ArgumentParser:
    """
    Monta o parser da CLI principal da pipeline.

    Parametros:
    - --source: fonte de editais (facepe, cnpq, finep, capes)
    - --limit: limite de PDFs processados na execucao
    """
    parser = argparse.ArgumentParser(
        description="Pipeline de analise de editais com fontes plugaveis"
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help=f"Fonte alvo ({', '.join(sorted(SOURCE_REGISTRY))})",
    )
    parser.add_argument(
        "--limit",
        default=os.getenv("PIPELINE_LIMIT") or "all",
        help="Limite de PDFs (all, 0, none ou numero inteiro)",
    )
    parser.add_argument(
        "--run-reminders",
        action="store_true",
        help="Executa somente notificacoes de prazo (D-30, D-15, D-7)",
    )
    parser.add_argument(
        "--reminder-steps",
        default=os.getenv("DEADLINE_REMINDER_STEPS") or "30,15,7",
        help="Marcos de lembrete separados por virgula. Ex: 30,15,7",
    )
    return parser


if __name__ == "__main__":
    # entrypoint da pipeline de producao
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.run_reminders:
            run_deadline_reminders(
                source_key=args.source,
                steps_raw=args.reminder_steps,
            )
        else:
            # delega a orquestracao para o runner
            run_pipeline(source_key=args.source, limit=parse_limit(args.limit))
    except ValueError as exc:
        # erros de validacao de parametros/fonte
        print(exc)
    except Exception as exc:
        # erros inesperados da execucao da pipeline
        print(f"Erro inesperado na execucao da pipeline: {exc}")