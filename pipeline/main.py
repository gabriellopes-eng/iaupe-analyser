import argparse
import os
from db.mongo import get_followed_sources, set_source_followed
from orchestration.deadline_reminder_runner import run_deadline_reminders
from orchestration.pipeline_runner import run_pipeline
from orchestration.settings import parse_limit
from orchestration.source_registry import DEFAULT_SOURCE, SOURCE_REGISTRY, get_source_config


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
    parser.add_argument(
        "--follow-source",
        metavar="FONTE",
        help="Liga uma fonte (facepe/cnpq/finep/capes): passa a receber lembretes",
    )
    parser.add_argument(
        "--unfollow-source",
        metavar="FONTE",
        help="Desliga uma fonte: deixa de receber lembretes dela",
    )
    parser.add_argument(
        "--list-sources",
        action="store_true",
        help="Lista as fontes atualmente seguidas",
    )
    return parser


if __name__ == "__main__":
    # entrypoint da pipeline de producao
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.follow_source or args.unfollow_source or args.list_sources:
            # fluxo de preferencias: ligar/desligar/listar fontes seguidas
            if args.follow_source:
                source_id, source = get_source_config(args.follow_source)
                status = set_source_followed(source_id, followed=True)
                print(f"Ligar fonte: {status} -> {source['label']} ({source_id})")

            if args.unfollow_source:
                source_id, source = get_source_config(args.unfollow_source)
                status = set_source_followed(source_id, followed=False)
                print(f"Desligar fonte: {status} -> {source['label']} ({source_id})")

            if args.list_sources:
                followed = get_followed_sources()
                print(f"Fontes seguidas ({len(followed)}):")
                for source_id, source in SOURCE_REGISTRY.items():
                    marca = "x" if source_id in followed else " "
                    print(f"[{marca}] {source_id} - {source['label']}")
        elif args.run_reminders:
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