"""
Ferramenta de conferencia da notificacao por area/segmento ("caixinha B").

Por padrao NAO envia nada: conecta no Mongo, cruza os docentes cadastrados com
os editais com prazo aberto e imprime quem receberia o que. Serve para revisar a
regra antes de disparar de verdade e para mostrar o funcionamento em apresentacao.

Uso (dentro da pasta sandbox/, com o venv ativado):
    python test_new_edital_notification.py                      # simulacao geral
    python test_new_edital_notification.py --email fulano@upe.br  # simula so 1 docente
    python test_new_edital_notification.py --url <url_do_pdf>     # simula so 1 edital
    python test_new_edital_notification.py --send-preview meu@email.com
        -> envia UM e-mail real (o primeiro par edital/docente encontrado) para
           o endereco informado, so para ver o layout. Nao marca nada no banco.

Diferenca para `main.py --notify-editais` (que tambem simula por padrao): la a
simulacao mostra o que a PROXIMA execucao faria, ja com as travas de volume
aplicadas. Aqui a lista e completa, sem travas - serve para revisar a regra de
casamento em si.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

# Garante que a raiz do projeto esteja no pythonpath para importar "pipeline"
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "pipeline"))

from pipeline.db.docentes import list_docentes_com_preferencias
from pipeline.db.match_notifications import (
    find_match_notification_candidates,
    get_match_sent_emails,
)
from pipeline.emails.saved_record_email_notifier import SavedRecordEmailNotifier
from pipeline.emails.smtp_config import is_smtp_configured
from pipeline.orchestration.docente_match import match_docentes
from pipeline.orchestration.docente_notification_service import resolve_source_label, select_recipients


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Simula (sem enviar) a notificacao de editais novos por area/segmento."
    )
    parser.add_argument("--source", default="", help="Filtra por fonte (facepe, cnpq, finep, capes).")
    parser.add_argument("--email", default="", help="Simula so este docente.")
    parser.add_argument("--url", default="", help="Simula so este edital (url_pdf).")
    parser.add_argument(
        "--send-preview",
        default="",
        metavar="EMAIL",
        help="Envia UM e-mail real de amostra para este endereco (nao marca no banco).",
    )
    return parser


def main() -> int:
    load_dotenv(override=True)
    args = build_parser().parse_args()

    docentes = list_docentes_com_preferencias()
    if args.email:
        alvo = args.email.strip().lower()
        docentes = [d for d in docentes if str(d.get("email") or "").strip().lower() == alvo]

    editais = find_match_notification_candidates(
        fonte=(args.source.strip().lower() or None),
        now=datetime.now(timezone.utc),
    )
    if args.url:
        editais = [e for e in editais if str(e.get("url_pdf") or "") == args.url.strip()]

    print(f"Docentes com preferencia: {len(docentes)}")
    print(f"Editais com prazo aberto: {len(editais)}")
    print("-" * 60)

    total_envios = 0
    total_ja_avisados = 0
    por_docente: dict[str, int] = {}
    primeiro_par: tuple[dict, object] | None = None

    for edital in editais:
        resultado = edital.get("resultado") or {}
        matches = match_docentes(
            docentes,
            resultado.get("areas_interesse"),
            resultado.get("segmentos"),
        )
        if not matches:
            continue

        # mesma funcao que decide quem recebe no envio de verdade, mas com o
        # limite por docente escancarado: aqui a lista e a fila INTEIRA (sem as
        # travas de volume), pra revisar a regra de casamento em si - quem
        # aplica a trava de verdade e o backfill (main.py --notify-editais).
        pendentes = select_recipients(
            matches, already_notified=get_match_sent_emails(edital), max_por_docente=10**9
        )
        total_ja_avisados += len(matches) - len(pendentes)
        if not pendentes:
            continue

        if primeiro_par is None:
            primeiro_par = (edital, pendentes[0])

        titulo = str(resultado.get("titulo") or resultado.get("descricao") or "(sem titulo)")[:80]
        print(f"[{edital.get('fonte')}] {titulo}")
        print(f"  areas do edital....: {resultado.get('areas_interesse')}")
        print(f"  segmentos do edital: {resultado.get('segmentos')}")
        for match in pendentes:
            total_envios += 1
            por_docente[match.email] = por_docente.get(match.email, 0) + 1
            motivos = ", ".join(match.areas + match.segmentos)
            print(f"  -> {match.email} (casou em: {motivos})")
        print()

    print("-" * 60)
    print(f"E-mails que SERIAM enviados agora: {total_envios}")
    print(f"Pares edital/docente ja avisados antes (nao reenviam): {total_ja_avisados}")
    if por_docente:
        print("Top destinatarios nesta simulacao:")
        for email, qtd in sorted(por_docente.items(), key=lambda kv: (-kv[1], kv[0]))[:10]:
            print(f"  {qtd:>3} edital(is) -> {email}")

    if args.send_preview:
        if primeiro_par is None:
            print("\nNada para enviar de amostra: nenhum par edital/docente pendente.")
            return 0

        edital, _match = primeiro_par
        if not is_smtp_configured():
            print("\nSMTP_USER/SMTP_PASS nao configurados - amostra nao enviada.")
            return 1

        fonte = str(edital.get("fonte") or "")
        SavedRecordEmailNotifier().notify_saved_record(
            recipient_email=args.send_preview.strip(),
            source_label=resolve_source_label(fonte),
            source_id=fonte,
            pdf_url=str(edital.get("url_pdf") or ""),
            saved_json=edital.get("resultado") or {},
        )
        print(f"\nAmostra enviada para {args.send_preview.strip()} (nada foi marcado no banco).")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
