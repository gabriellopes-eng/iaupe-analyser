from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from dotenv import load_dotenv

# Garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from pipeline.db.mongo import coll, mark_deadline_step_sent, save
from pipeline.emails.deadline_reminder_email_notifier import DeadlineReminderEmailNotifier
from pipeline.orchestration.source_registry import get_source_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Demo de producao do lembrete de prazo: persiste registro de teste no Mongo, "
            "envia email real e valida marcacao de envio."
        )
    )
    parser.add_argument(
        "--recipient",
        default="",
        help="Email de destino. Se vazio, usa RECIPIENT_EMAIL.",
    )
    parser.add_argument(
        "--source",
        default="finep",
        help="Fonte alvo (facepe, cnpq, finep, capes).",
    )
    parser.add_argument(
        "--step",
        type=int,
        default=7,
        help="Marco de lembrete em dias (ex.: 7, 15, 30).",
    )
    parser.add_argument(
        "--title",
        default="",
        help="Titulo opcional do edital demo para aparecer no email.",
    )
    parser.add_argument(
        "--url",
        default="",
        help="URL opcional do edital de teste. Se vazio, gera URL sandbox unica.",
    )
    return parser


def main() -> int:
    load_dotenv(override=True)
    args = build_parser().parse_args()

    if args.step <= 0:
        print("Erro: --step deve ser maior que zero.")
        return 1

    source_id, source = get_source_config(args.source)

    now = datetime.now(timezone.utc)
    deadline = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) + timedelta(days=args.step)

    test_url = args.url.strip() or (
        f"https://sandbox.local/{source_id}/deadline-production-demo-{args.step}d-{int(now.timestamp())}.pdf"
    )

    demo_title = args.title.strip() or f"Edital DEMO {source['label']} - Prazo em D-{args.step}"

    saved_json = {
        "titulo": demo_title,
        "descricao": (
            "Caso de teste de producao para validacao do layout e fluxo do "
            "DeadlineReminderEmailNotifier em apresentacao academica."
        ),
        "publico_alvo": "Pesquisadores, ICTs e empresas elegiveis no edital.",
    }

    status = save(
        url_pdf=test_url,
        resultado=saved_json,
        fonte=source_id,
        texto_preview="Deadline production demo",
        data_limit_submissao=deadline,
    )

    if status == "disabled":
        print("Falha ao persistir registro de teste no MongoDB.")
        return 1

    coll().update_one(
        {"url_pdf": test_url},
        {
            "$unset": {"deadline_reminder": ""},
            "$set": {"status": "ok", "data_limit_submissao": deadline},
        },
    )

    print("Registro demo preparado com sucesso.")
    print(f"- Fonte: {source['label']} ({source_id})")
    print(f"- URL: {test_url}")
    print(f"- Titulo: {demo_title}")
    print(f"- Prazo (D-{args.step}): {deadline.date().isoformat()}")

    recipient = args.recipient.strip() or (os.getenv("RECIPIENT_EMAIL") or "").strip()
    if not recipient:
        print("Erro: informe --recipient ou configure RECIPIENT_EMAIL no .env.")
        return 1

    notifier = DeadlineReminderEmailNotifier()
    if not notifier.is_smtp_configured():
        print("Erro: SMTP_USER/SMTP_PASS nao configurados no .env.")
        return 1

    print(f"Destinatario do envio: {recipient}")

    notifier.notify_deadline(
        recipient_email=recipient,
        source_label=source["label"],
        source_id=source_id,
        pdf_url=test_url,
        saved_json=saved_json,
        deadline=deadline,
        days_left=args.step,
    )
    print("Email de lembrete enviado com sucesso.")

    marked = mark_deadline_step_sent(
        url_pdf=test_url,
        step_days=args.step,
    )

    if not marked:
        print("Falha ao marcar envio no MongoDB (ou marco ja existente).")
        return 1

    updated = coll().find_one(
        {"url_pdf": test_url},
        {"_id": 0, "deadline_reminder": 1, "data_limit_submissao": 1},
    )

    sent_steps = ((updated or {}).get("deadline_reminder") or {}).get("sent_steps") or []
    if args.step not in [int(item) for item in sent_steps if str(item).isdigit()]:
        print("Falha de validacao: passo nao encontrado em deadline_reminder.sent_steps.")
        return 1

    print("Validacao concluida: persistencia Mongo + email + marcacao de prazo OK.")
    print("Pronto para demonstracao ao professor.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
