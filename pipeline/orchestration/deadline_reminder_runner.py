from __future__ import annotations

from datetime import datetime, timedelta, timezone

from db.mongo import find_deadline_candidates, mark_deadline_step_sent
from emails.deadline_reminder_email_notifier import DeadlineReminderEmailNotifier

from .source_registry import get_source_config

DEFAULT_REMINDER_STEPS = [30, 15, 7]


def parse_reminder_steps(raw: str) -> list[int]:
    steps: list[int] = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue

        try:
            value = int(part)
        except ValueError:
            continue

        if value > 0:
            steps.append(value)

    unique = sorted(set(steps), reverse=True)
    return unique or DEFAULT_REMINDER_STEPS


def run_deadline_reminders(
    source_key: str | None,
    steps_raw: str,
) -> None:
    source_id, source = get_source_config(source_key)

    notifier = DeadlineReminderEmailNotifier()
    steps = parse_reminder_steps(steps_raw)

    now = datetime.now(timezone.utc)
    today_start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
    window_end = today_start + timedelta(days=max(steps))

    docs = find_deadline_candidates(
        collection_name=source["mongo_collection"],
        start_at=today_start,
        end_at=window_end,
    )

    print(
        f"Lembretes | Fonte: {source['label']} ({source_id}) | "
        f"Janela: {today_start.date()} ate {window_end.date()} | "
        f"Candidatos: {len(docs)}"
    )

    if not notifier.is_smtp_configured():
        print("Lembretes desativados: SMTP_USER/SMTP_PASS nao configurados.")
        return

    sent_count = 0
    for doc in docs:
        deadline = doc.get("data_limit_submissao")
        if not isinstance(deadline, datetime):
            continue

        if deadline.tzinfo is None:
            deadline = deadline.replace(tzinfo=timezone.utc)

        days_left = (deadline.date() - today_start.date()).days
        if days_left not in steps:
            continue

        reminder_info = doc.get("deadline_reminder") or {}
        sent_steps_raw = reminder_info.get("sent_steps") or []

        sent_steps: set[int] = set()
        for item in sent_steps_raw:
            try:
                sent_steps.add(int(item))
            except (TypeError, ValueError):
                continue

        if days_left in sent_steps:
            continue

        pdf_url = str(doc.get("url_pdf") or "").strip()
        if not pdf_url:
            continue

        # cada edital tem sua propria lista de interessados (e-mails que marcaram
        # aquele edital especifico); sem ninguem inscrito, nao ha o que notificar.
        interessados = [str(e).strip() for e in (doc.get("interessados") or []) if str(e).strip()]
        if not interessados:
            continue

        resultado = doc.get("resultado") or {}

        try:
            # um e-mail por vez, endereçado individualmente: uma pessoa que
            # acompanha este edital nao deve ver o endereco de outra.
            for recipient_email in interessados:
                notifier.notify_deadline(
                    recipient_email=recipient_email,
                    source_label=source["label"],
                    source_id=source_id,
                    pdf_url=pdf_url,
                    saved_json=resultado,
                    deadline=deadline,
                    days_left=days_left,
                )

            marked = mark_deadline_step_sent(
                collection_name=source["mongo_collection"],
                url_pdf=pdf_url,
                step_days=days_left,
            )
            if marked:
                sent_count += 1

            print(f"Lembrete enviado D-{days_left} para {len(interessados)} interessado(s): {pdf_url}")

        except Exception as exc:
            print(f"Falha no lembrete D-{days_left} para {pdf_url}: {exc}")

    print(f"Total de editais notificados: {sent_count}")
