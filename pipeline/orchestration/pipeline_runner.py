import json
import time
from datetime import datetime, timezone

from db.docentes import list_docentes_com_preferencias
from db.editais import already_exists, save
from emails.saved_record_email_notifier import SavedRecordEmailNotifier
from emails.smtp_config import is_smtp_configured
from pdf_pipeline.extractor import extract_text_from_pdf_url
from .date_parser import parse_data_limit_submissao
from .docente_notification_service import (
    notificacao_docentes_habilitada,
    notify_docentes_for_edital,
)
from .retry_policy import retry_analyze_text
from .settings import LIMIT, SLEEP_ALREADY_EXISTS, SLEEP_EMPTY_TEXT, SLEEP_NEW_PROCESS
from .source_registry import get_source_config


def is_gemini_quota_exceeded(resultado: dict) -> bool:
    raw = str((resultado or {}).get("raw") or "").lower()
    erro = str((resultado or {}).get("erro") or "").lower()
    return (
        "resource_exhausted" in raw
        or "quota exceeded" in raw
        or ("429" in raw and "quota" in raw)
        or "quota" in erro
    )


def run_pipeline(source_key: str | None = None, limit: int | None = LIMIT) -> None:
    """
    Orquestra o fluxo completo da pipeline para uma fonte:
    coletar links, extrair texto, analisar com IA e persistir no MongoDB.
    """
    try:
        source_id, source = get_source_config(source_key)
        notifier = SavedRecordEmailNotifier()
        email_enabled = notifier.is_enabled()

        # Notificacao por preferencia: o MESMO e-mail e o MESMO notifier acima,
        # so que enderecado a cada docente cujas areas/segmentos casam com o
        # edital, em vez do endereco institucional que recebe tudo.
        match_enabled = is_smtp_configured() and notificacao_docentes_habilitada()
        docentes_com_preferencia: list[dict] = []

        # Contador da execucao, usado pela trava de volume: numa rodada em que a
        # fonte publica varios editais de uma vez, ninguem recebe mais que o
        # limite por pessoa. O que sobra nao e marcado como enviado, entao o
        # backfill (`main.py --notify-editais`) cobre o restante depois.
        match_enviados_por_docente: dict[str, int] = {}

        found_total = 0
        selected_total = 0
        already_saved_total = 0
        inserted_total = 0
        updated_total = 0
        empty_text_total = 0
        analysis_error_total = 0
        quota_exceeded_total = 0
        error_total = 0
        emails_sent_total = 0
        match_emails_sent_total = 0
        
        #Aqui eu apliquei o filtro de limite antes de processar os documentos, para evitar gastar recursos de IA e MongoDB com documentos que nao serao processados nessa execucao devido ao limite definido. Assim, priorizo os documentos mais recentes (assumindo que os links sao retornados em ordem do mais recente para o mais antigo) e evito retrabalho desnecessario.

        # collect_calls devolve (url_pdf, data_publicacao). A data serve para
        # ordenar a vitrine do front pela publicacao real da fonte, em vez do
        # created_at (que depende de quando a pipeline alcancou o edital). CNPq
        # nao expoe data de publicacao, entao vem None.
        calls = source["collect_calls"](source["base_url"])
        links = [url for url, _ in calls]
        data_publicacao_por_url: dict[str, datetime | None] = dict(calls)
        found_total = len(links)
        if not links:
            print(f"Nenhum PDF encontrado para a fonte {source['label']}.")
            return
        # aplica filtro para limitar quantidade de documentos processados por execucao, priorizando os mais recentes

        pending_links: list[str] = []
        for link in links:
            if already_exists(link):
                already_saved_total += 1
                continue

            pending_links.append(link)
            if limit is not None and len(pending_links) >= limit:
                break

        links = pending_links
        selected_total = len(links)

        if not links:
            print(f"Fonte: {source['label']} ({source_id})")
            print(
                f"Encontrados: {found_total} | "
                f"Pendentes selecionados pelo limite: {selected_total} | "
                f"Ja salvos ignorados: {already_saved_total}"
            )
            print("Nenhum novo PDF pendente para processar.")
            return

        print(f"Fonte: {source['label']} ({source_id})")
        print(
            f"Encontrados: {found_total} | "
            f"Pendentes selecionados pelo limite: {selected_total} | "
            f"Ja salvos ignorados: {already_saved_total} | "
            f"Email habilitado: {'sim' if email_enabled else 'nao'}"
        )
        # a lista de docentes e carregada UMA vez por execucao (a base tem
        # centenas de registros) e reaproveitada para todos os editais do lote.
        if match_enabled:
            docentes_com_preferencia = list_docentes_com_preferencias()

        print(
            f"{selected_total} PDFs para processar. "
            f"Docentes com preferencia cadastrada: {len(docentes_com_preferencia)}\n"
        )

        for i, link in enumerate(links, start=1):
            try:
                # evita retrabalho para documentos ja processados com sucesso
                if already_exists(link):
                    print(f"[{i}/{len(links)}] ✅ Já salvo no MongoDB (status=ok): {link}")
                    already_saved_total += 1
                    if i < len(links):
                        time.sleep(SLEEP_ALREADY_EXISTS)
                    continue

                print(f"[{i}/{len(links)}] 📄 {link}")
                texto = extract_text_from_pdf_url(link)

                if not texto:
                    # persiste erro controlado quando nao foi possivel extrair texto
                    print("Texto vazio.\n")
                    empty_text_total += 1
                    status = save(
                        link,
                        {"erro": "Texto vazio"},
                        fonte=source_id,
                        texto_preview="",
                        data_limit_submissao=None,
                        data_publicacao=data_publicacao_por_url.get(link),
                    )
                    if status != "disabled":
                        print(f"💾 MongoDB: {status}")
                    if i < len(links):
                        time.sleep(SLEEP_EMPTY_TEXT)
                    continue

                # analisa com politica de retry para erros temporarios da IA
                resultado = retry_analyze_text(texto, link)
                analysis_has_error = bool((resultado or {}).get("erro"))
                should_stop_for_quota = analysis_has_error and is_gemini_quota_exceeded(resultado)
                if analysis_has_error:
                    analysis_error_total += 1
                if should_stop_for_quota:
                    quota_exceeded_total += 1

                data_limit_submissao = parse_data_limit_submissao(
                    resultado.get("data_limit_submissao")
                )

                status = save(
                    link,
                    resultado,
                    fonte=source_id,
                    texto_preview=texto,
                    data_limit_submissao=data_limit_submissao,
                    data_publicacao=data_publicacao_por_url.get(link),
                )

                if status != "disabled":
                    print(f"💾 MongoDB: {status}")

                if status == "inserted":
                    inserted_total += 1
                elif status == "updated":
                    updated_total += 1
                elif status == "disabled":
                    error_total += 1

                deadline_passed = (
                    data_limit_submissao is not None
                    and data_limit_submissao < datetime.now(timezone.utc)
                )

                # "updated" tambem conta como novidade aqui: already_exists() so deixa
                # chegar neste ponto quando o status anterior nao era "ok" (documento
                # inexistente ou salvo antes com erro), entao mesmo em "updated" e a
                # primeira vez que esse edital fica valido para notificar.
                if status in ("inserted", "updated") and not analysis_has_error:
                    if deadline_passed:
                        print("📭 Email não enviado: prazo de submissão já expirado.")
                    else:
                        try:
                            notifier.notify_saved_record(
                                source_label=source["label"],
                                source_id=source_id,
                                pdf_url=link,
                                saved_json=resultado,
                            )
                            if notifier.is_enabled():
                                emails_sent_total += 1
                                print("📧 Email HTML enviado para destinatario de teste.")
                        except Exception as email_exc:
                            error_total += 1
                            print(f"Falha ao enviar email de notificacao: {email_exc}")

                        # Nao precisa passar `already_notified` aqui: so chegamos
                        # neste ponto quando already_exists() era falso, ou seja, o
                        # edital nunca esteve com status ok antes e ninguem foi
                        # avisado dele ainda.
                        if match_enabled:
                            enviados = notify_docentes_for_edital(
                                notifier=notifier,
                                docentes=docentes_com_preferencia,
                                source_id=source_id,
                                source_label=source["label"],
                                pdf_url=link,
                                resultado=resultado,
                                sent_per_docente=match_enviados_por_docente,
                            )
                            if enviados:
                                match_emails_sent_total += len(enviados)
                                print(
                                    f"📧 {len(enviados)} docente(s) notificado(s) por area/segmento."
                                )

                if status == "inserted" and analysis_has_error:
                    print("📭 Email nao enviado: analise com erro (registro salvo para auditoria).")

                print(json.dumps(resultado, ensure_ascii=False, indent=2))
                print("\n" + "-" * 60 + "\n")

                if should_stop_for_quota:
                    print("⛔ Execucao da fonte encerrada: quota do Gemini esgotada.")
                    break

                # controla ritmo para evitar sobrecarga em APIs externas
                if i < len(links):
                    time.sleep(SLEEP_NEW_PROCESS)

            except Exception as exc:
                error_total += 1
                print(f"[{i}/{len(links)}] ❌ Erro ao processar link {link}: {exc}")
                if i < len(links):
                    time.sleep(SLEEP_EMPTY_TEXT)
                continue

        print(
            "Resumo da fonte | "
            f"found={found_total} | selected={selected_total} | "
            f"already_saved={already_saved_total} | inserted={inserted_total} | "
            f"updated={updated_total} | empty_text={empty_text_total} | "
            f"analysis_errors={analysis_error_total} | "
            f"quota_exceeded={quota_exceeded_total} | "
            f"emails_sent={emails_sent_total} | "
            f"emails_docentes={match_emails_sent_total} | errors={error_total}"
        )

    except Exception as exc:
        print(f"❌ Falha geral na orquestracao da pipeline: {exc}")
        raise

    finally:
        # Encerra a conexao SMTP reaproveitada durante o lote de notificacoes.
        notifier = locals().get("notifier")
        if notifier is not None:
            notifier.close()
