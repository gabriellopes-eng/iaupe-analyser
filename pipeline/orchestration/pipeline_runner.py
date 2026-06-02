import json
import time

from db.mongo import already_exists, save
from emails.saved_record_email_notifier import SavedRecordEmailNotifier
from pdf_pipeline.extractor import extract_text_from_pdf_url
from .date_parser import parse_data_limit_submissao
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

        links = source["collect_links"](source["base_url"])
        found_total = len(links)
        if not links:
            print(f"Nenhum PDF encontrado para a fonte {source['label']}.")
            return

        links = links if limit is None else links[:limit]
        selected_total = len(links)

        print(
            f"Fonte: {source['label']} ({source_id}) | "
            f"Collection Mongo: {source['mongo_collection']}"
        )
        print(
            f"Encontrados: {found_total} | "
            f"Selecionados pelo limite: {selected_total} | "
            f"Email habilitado: {'sim' if email_enabled else 'nao'}"
        )
        print(f"{selected_total} PDFs para processar.\n")

        for i, link in enumerate(links, start=1):
            try:
                # evita retrabalho para documentos ja processados com sucesso
                if already_exists(link, collection_name=source["mongo_collection"]):
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
                        texto_preview="",
                        collection_name=source["mongo_collection"],
                        data_limit_submissao=None,
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
                    texto_preview=texto,
                    collection_name=source["mongo_collection"],
                    data_limit_submissao=data_limit_submissao,
                )

                if status != "disabled":
                    print(f"💾 MongoDB: {status}")

                if status == "inserted":
                    inserted_total += 1
                elif status == "updated":
                    updated_total += 1
                elif status == "disabled":
                    error_total += 1

                if status == "inserted" and not analysis_has_error:
                    try:
                        notifier.notify_saved_record(
                            source_label=source["label"],
                            source_id=source_id,
                            collection_name=source["mongo_collection"],
                            save_status=status,
                            pdf_url=link,
                            saved_json=resultado,
                        )
                        if notifier.is_enabled():
                            emails_sent_total += 1
                            print("📧 Email HTML enviado para destinatario de teste.")
                    except Exception as email_exc:
                        error_total += 1
                        print(f"Falha ao enviar email de notificacao: {email_exc}")

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
            f"emails_sent={emails_sent_total} | errors={error_total}"
        )

    except Exception as exc:
        print(f"❌ Falha geral na orquestracao da pipeline: {exc}")
        raise
