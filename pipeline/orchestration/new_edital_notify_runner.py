from __future__ import annotations

from datetime import datetime, timezone

from db.docentes import list_docentes_com_preferencias
from db.match_notifications import find_match_notification_candidates, get_match_sent_emails
from emails.saved_record_email_notifier import SavedRecordEmailNotifier
from emails.smtp_config import is_smtp_configured

from .docente_notification_service import (
    DEFAULT_MAX_EMAILS,
    DEFAULT_MAX_POR_DOCENTE,
    notificacao_docentes_habilitada,
    notify_docentes_for_edital,
    resolve_source_label,
)
from .source_registry import get_source_config

# Orquestracao do BACKFILL: varredura avulsa que roda sob demanda (CLI), em vez
# do disparo automatico de pipeline_runner.py. O cruzamento/envio em si (motor
# reutilizado pelos dois fluxos) mora em docente_notification_service.py.

# Palavras aceitas na CLI para "nao filtre por fonte". A collection de editais e
# unica, entao varrer tudo de uma vez e uma consulta so.
ALL_SOURCES_KEYS = {"all", "todas", "todas-as-fontes", "*"}


def run_new_edital_notifications(
    source_key: str | None = None,
    apply: bool = False,
    max_por_docente: int = DEFAULT_MAX_POR_DOCENTE,
    max_emails: int = DEFAULT_MAX_EMAILS,
) -> None:
    """
    Varredura avulsa: notifica docentes sobre editais ja salvos que ainda nao
    foram avisados (backfill).

    No dia a dia isso NAO e necessario - o pipeline_runner ja notifica assim que
    salva um edital novo. Serve para o primeiro disparo depois que a base de
    preferencias foi populada, para quando alguem cadastra preferencias depois
    do edital ja existir, e para reprocessar apos uma falha de SMTP.

    Por padrao roda em SIMULACAO (`apply=False`), igual ao script de carga da
    planilha: mostra o que sairia e nao envia nada.
    """
    fonte, escopo = _resolve_scope(source_key)

    editais = find_match_notification_candidates(fonte=fonte, now=datetime.now(timezone.utc))
    docentes = list_docentes_com_preferencias()

    # prazo mais apertado primeiro: se a trava de volume cortar a fila, a pessoa
    # recebe os editais que ela tem menos tempo para responder.
    editais.sort(
        key=lambda doc: (doc.get("data_limit_submissao") is None, doc.get("data_limit_submissao"))
    )

    print(
        f"Notificacao por area/segmento | Escopo: {escopo} | "
        f"Editais com prazo aberto: {len(editais)} | "
        f"Docentes com preferencia: {len(docentes)}"
    )
    print(
        f"Modo: {'ENVIO REAL' if apply else 'SIMULACAO (nada sera enviado)'} | "
        f"Limite por docente: {max_por_docente} | Limite total: {max_emails}"
    )

    if apply and not is_smtp_configured():
        print("Notificacao desativada: SMTP_USER/SMTP_PASS nao configurados.")
        return

    # Mesmo interruptor de emergencia do fluxo automatico (NOTIFY_DOCENTES=0):
    # se as notificacoes por area/segmento estao desligadas, o backfill tambem
    # nao dispara nada.
    if apply and not notificacao_docentes_habilitada():
        print("Notificacao desativada: NOTIFY_DOCENTES=0.")
        return

    if not docentes:
        print("Nenhum docente com area/segmento cadastrado - nada a notificar.")
        return

    resumo = _notify_all(
        editais=editais,
        docentes=docentes,
        apply=apply,
        max_por_docente=max_por_docente,
        max_emails=max_emails,
    )

    verbo = "emails_enviados" if apply else "emails_que_seriam_enviados"
    print(f"Resumo | editais={resumo['editais']} | {verbo}={resumo['emails']}")
    if not apply:
        print("Simulacao: nada foi enviado. Rode de novo com --apply para disparar.")


def _resolve_scope(source_key: str | None) -> tuple[str | None, str]:
    """Traduz --source da CLI em (fonte para filtrar, texto pra exibir)."""
    selected = (source_key or "").strip().lower()
    if selected in ALL_SOURCES_KEYS:
        return None, "todas as fontes"

    fonte, source = get_source_config(source_key)
    return fonte, f"{source['label']} ({fonte})"


def _notify_all(
    *,
    editais: list[dict],
    docentes: list[dict],
    apply: bool,
    max_por_docente: int,
    max_emails: int,
) -> dict[str, int]:
    """Percorre os editais candidatos e notifica cada um, respeitando as travas."""
    notifier = SavedRecordEmailNotifier()
    sent_per_docente: dict[str, int] = {}
    total_emails = 0
    editais_notificados = 0

    try:
        for doc in editais:
            pdf_url = str(doc.get("url_pdf") or "").strip()
            if not pdf_url:
                continue
            if total_emails >= max_emails:
                break

            fonte_doc = str(doc.get("fonte") or "").strip().lower()
            enviados = notify_docentes_for_edital(
                notifier=notifier,
                docentes=docentes,
                source_id=fonte_doc,
                source_label=resolve_source_label(fonte_doc),
                pdf_url=pdf_url,
                resultado=doc.get("resultado") or {},
                sent_per_docente=sent_per_docente,
                already_notified=get_match_sent_emails(doc),
                max_por_docente=max_por_docente,
                remaining_quota=max_emails - total_emails,
                dry_run=not apply,
            )

            if enviados:
                editais_notificados += 1
                total_emails += len(enviados)
                print(
                    f"{'Notificados' if apply else 'Notificaria'} "
                    f"{len(enviados)} docente(s): {pdf_url}"
                )
    finally:
        # Encerra a conexao SMTP reaproveitada durante o lote.
        notifier.close()

    return {"editais": editais_notificados, "emails": total_emails}
