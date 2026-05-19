from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from pipeline.db.mongo import coll, mark_deadline_step_sent, save
from pipeline.emails.deadline_reminder_email_notifier import DeadlineReminderEmailNotifier
from pipeline.orchestration.source_registry import get_source_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Teste de integracao do fluxo de lembrete de prazo "
            "(Mongo + notificador + marcacao de envio)."
        )
    )
    parser.add_argument(
        "--source",
        default="cnpq",
        help="Fonte alvo (facepe, cnpq, finep, capes)",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=7,
        help="Marco de lembrete em dias (ex.: 7, 15, 30)",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Envia email real. Sem essa flag, so simula e gera preview HTML.",
    )
    parser.add_argument(
        "--recipient",
        default="",
        help="Destinatario opcional para teste (sobrescreve RECIPIENT_EMAIL).",
    )
    parser.add_argument(
        "--url",
        default="",
        help="URL de teste opcional. Se vazio, gera uma URL sandbox unica.",
    )
    return parser


def main() -> int:
    load_dotenv(override=True)
    parser = build_parser()
    args = parser.parse_args()

    if args.step <= 0:
        print("Erro: --step deve ser maior que zero.")
        return 1

    source_id, source = get_source_config(args.source)
    collection_name = source["mongo_collection"]

    now = datetime.now(timezone.utc)
    deadline = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=args.step)

    test_url = args.url.strip() or (
        f"https://sandbox.local/{source_id}/deadline-reminder-{args.step}d-{int(now.timestamp())}.pdf"
    )

    saved_json = {
        "titulo": f"Edital sandbox {source['label']} D-{args.step}",
        "descricao": "Registro de teste de integracao do lembrete de prazo.",
        "publico_alvo": "Equipe interna",
        "fonte": source_id,
    }

    status = save(
        url_pdf=test_url,
        resultado=saved_json,
        texto_preview="Sandbox integration test",
        collection_name=collection_name,
        data_limit_submissao=deadline,
    )

    if status == "disabled":
        print("Falha ao persistir registro de teste no MongoDB.")
        return 1

    # limpa marcacao de lembrete para garantir comportamento deterministico no teste
    coll(collection_name).update_one(
        {"url_pdf": test_url},
        {
            "$unset": {"deadline_reminder": ""},
            "$set": {"status": "ok", "data_limit_submissao": deadline},
        },
    )

    print(f"Registro de teste preparado: {test_url}")
    print(f"Collection: {collection_name} | Fonte: {source['label']} ({source_id}) | Marco: D-{args.step}")

    notifier = DeadlineReminderEmailNotifier(test_recipient=args.recipient.strip() or None)

    if args.send_email:
        if not notifier.is_enabled():
            print("Erro: destinatario nao configurado. Use --recipient ou RECIPIENT_EMAIL.")
            return 1

        notifier.notify_deadline(
            source_label=source["label"],
            source_id=source_id,
            pdf_url=test_url,
            saved_json=saved_json,
            deadline=deadline,
            days_left=args.step,
        )
        print("Email de lembrete enviado com sucesso.")
    else:
        preview_html = notifier.build_html(
            source_label=source["label"],
            source_id=source_id,
            pdf_url=test_url,
            saved_json=saved_json,
            deadline=deadline,
            days_left=args.step,
        )
        print("Modo simulacao: email nao enviado.")
        print(f"Preview HTML gerado ({len(preview_html)} chars).")

    marked = mark_deadline_step_sent(
        collection_name=collection_name,
        url_pdf=test_url,
        step_days=args.step,
    )

    if not marked:
        print("Falha ao marcar envio no MongoDB (ou marco ja existente).")
        return 1

    updated = coll(collection_name).find_one(
        {"url_pdf": test_url},
        {"_id": 0, "deadline_reminder": 1, "data_limit_submissao": 1},
    )

    sent_steps = ((updated or {}).get("deadline_reminder") or {}).get("sent_steps") or []
    print(f"Marcacao registrada no Mongo: sent_steps={sent_steps}")

    if args.step not in [int(item) for item in sent_steps if isinstance(item, (int, str)) and str(item).isdigit()]:
        print("Falha de validacao: passo nao encontrado em deadline_reminder.sent_steps.")
        return 1

    print("Teste de integracao concluido com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
