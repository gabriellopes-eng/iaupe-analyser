"""
Script one-shot (mas seguro de rodar mais de uma vez): le a planilha exportada
do formulario "Experiencia Profissional Docentes e Servidores da UPE", limpa
os dados e carrega na collection MongoDB `docentes`.

Cada docente fica identificado pelo e-mail (normalizado/unico) e guarda suas
`areas_interesse` e `segmentos` de interesse, usados futuramente para
notificar por e-mail sobre novos editais compativeis (task 2 e 3).

As AREAS DE INTERESSE da planilha usam o mesmo catalogo fixo de 8 valores que
o Gemini usa para classificar editais (`pipeline.pdf_pipeline.analyzer.AREAS_INTERESSE`),
entao reaproveitamos essa lista aqui para garantir que os textos fiquem
identicos aos gravados em `editais.resultado.areas_interesse`.

Uso (dentro da pasta sandbox/, com o venv ativado):
    python import_docentes_interesse.py                 # dry-run: so mostra o resumo
    python import_docentes_interesse.py --apply          # grava de verdade no MongoDB
    python import_docentes_interesse.py --input caminho.xlsx --apply
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

import certifi
import openpyxl
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError

# garante que a raiz do projeto esteja no PYTHONPATH (para importar "pipeline")
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from pipeline.pdf_pipeline.analyzer import AREAS_INTERESSE  # noqa: E402

DEFAULT_INPUT_PATH = (
    PROJECT_ROOT
    / "TRATADO - Experiência Profissional Docentes e Servidores da UPE (respostas).xlsx"
)
DOCENTES_COLLECTION = "docentes"
ORIGEM = "planilha_docentes_2026"

EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_email(raw: str | None) -> str:
    """Remove espacos (inclusive internos, tipo 'luis. barros@upe.br') e baixa a caixa."""
    return re.sub(r"\s+", "", (raw or "")).strip().lower()


def split_areas(raw: str | None, catalog: list[str]) -> list[str]:
    """
    Separa a celula de AREAS DE INTERESSE nos valores atomicos do catalogo fixo.

    Nao da pra usar split(",") direto: alguns valores atomicos ja tem virgula
    dentro (ex.: "Empreendedorismo (apoio a startups, spin-offs)"). Em vez
    disso, casamos por prefixo contra o catalogo conhecido (do maior pro
    menor, pra evitar ambiguidade) e consumimos a string aos poucos.
    """
    text = (raw or "").strip()
    if not text:
        return []

    sorted_catalog = sorted(catalog, key=len, reverse=True)
    result: list[str] = []
    remaining = text
    while remaining:
        remaining = remaining.strip().lstrip(",").strip()
        if not remaining:
            break
        matched = next((c for c in sorted_catalog if remaining.startswith(c)), None)
        if matched is None:
            # valor fora do catalogo conhecido - guarda como veio pra revisao manual
            # em vez de descartar silenciosamente
            result.append(remaining)
            break
        result.append(matched)
        remaining = remaining[len(matched):]

    seen: set[str] = set()
    return [item for item in result if not (item in seen or seen.add(item))]


def split_segmentos(raw: str | None) -> list[str]:
    """Separa a celula de SEGMENTOS por virgula (valores atomicos nao tem virgula interna)."""
    text = (raw or "").strip()
    if not text:
        return []
    parts = [p.strip() for p in text.split(",")]
    seen: set[str] = set()
    return [p for p in parts if p and not (p in seen or seen.add(p))]


def read_rows(path: Path):
    """Le (email, areas_raw, segmentos_raw) de cada linha de dados da planilha."""
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    next(rows, None)  # cabecalho
    for row in rows:
        email = row[0] if len(row) > 0 else None
        areas = row[1] if len(row) > 1 else None
        segmentos = row[2] if len(row) > 2 else None
        yield (str(email) if email is not None else ""), \
              (str(areas) if areas is not None else ""), \
              (str(segmentos) if segmentos is not None else "")


def build_docentes(path: Path, catalog_areas: list[str]):
    stats = defaultdict(int)
    by_email: dict[str, dict] = {}
    unknown_areas: set[str] = set()

    for email_raw, areas_raw, segmentos_raw in read_rows(path):
        stats["total_rows"] += 1

        email = normalize_email(email_raw)
        if not email:
            stats["sem_email"] += 1
            continue
        if not EMAIL_REGEX.match(email):
            stats["email_invalido"] += 1
            print(f"[aviso] e-mail invalido ignorado: {email_raw!r}")
            continue

        areas = split_areas(areas_raw, catalog_areas)
        for area in areas:
            if area not in catalog_areas:
                unknown_areas.add(area)
        segmentos = split_segmentos(segmentos_raw)

        existing = by_email.get(email)
        if existing is not None:
            stats["linhas_duplicadas"] += 1
            # une valores caso as duplicatas divirjam (nao esperado, mas seguro)
            existing["areas_interesse"] = sorted(set(existing["areas_interesse"]) | set(areas))
            existing["segmentos"] = sorted(set(existing["segmentos"]) | set(segmentos))
            continue

        by_email[email] = {"email": email, "areas_interesse": areas, "segmentos": segmentos}
        stats["docentes_unicos"] += 1

    return by_email, stats, unknown_areas


def get_mongo_collection():
    uri = (os.getenv("MONGODB_URI") or "").strip()
    if not uri:
        raise RuntimeError("MONGODB_URI nao definido no .env")
    db_name = (os.getenv("MONGODB_DB") or "iaupe-analyser").strip()

    client = MongoClient(uri, tlsCAFile=certifi.where())
    collection = client[db_name][DOCENTES_COLLECTION]
    collection.create_index([("email", ASCENDING)], unique=True)
    return collection


def print_summary(by_email: dict, stats: dict, unknown_areas: set[str]) -> None:
    print("=== Resumo da limpeza ===")
    print(f"Linhas na planilha (sem cabecalho):   {stats['total_rows']}")
    print(f"  sem e-mail (descartadas):           {stats['sem_email']}")
    print(f"  e-mail invalido (descartadas):      {stats['email_invalido']}")
    print(f"  linhas duplicadas (mesmo e-mail):   {stats['linhas_duplicadas']}")
    print(f"Docentes unicos a importar:           {len(by_email)}")

    if unknown_areas:
        print(f"\n[aviso] valores de AREAS DE INTERESSE fora do catalogo conhecido ({len(unknown_areas)}):")
        for area in sorted(unknown_areas):
            print("   -", area)

    sem_area = sum(1 for d in by_email.values() if not d["areas_interesse"])
    sem_segmento = sum(1 for d in by_email.values() if not d["segmentos"])
    print(f"\nDocentes sem nenhuma area de interesse marcada: {sem_area}")
    print(f"Docentes sem nenhum segmento marcado:            {sem_segmento}")

    print("\n=== Amostra (5 primeiros) ===")
    for doc in list(by_email.values())[:5]:
        print(f" - {doc['email']}")
        print(f"     areas: {doc['areas_interesse']}")
        print(f"     segmentos: {doc['segmentos']}")


def main() -> None:
    # console do Windows costuma usar codepage legado; forca UTF-8 pra nao
    # embaralhar acentos na saida (nao afeta o que e gravado no MongoDB)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description='Limpa a planilha de docentes e carrega na collection MongoDB "docentes".'
    )
    parser.add_argument("--input", default=str(DEFAULT_INPUT_PATH), help="Caminho do arquivo .xlsx")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Executa de fato a gravacao no MongoDB (sem essa flag, roda em modo dry-run)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Arquivo nao encontrado: {input_path}")
        return

    by_email, stats, unknown_areas = build_docentes(input_path, AREAS_INTERESSE)
    print_summary(by_email, stats, unknown_areas)

    if not args.apply:
        print("\n[dry-run] Nenhuma gravacao feita no MongoDB. Rode novamente com --apply para gravar de verdade.")
        return

    load_dotenv(override=True)
    try:
        collection = get_mongo_collection()
    except (RuntimeError, PyMongoError) as exc:
        print(f"\n[MongoDB] Nao foi possivel conectar: {exc}")
        return

    now = datetime.now(timezone.utc)
    inserted = 0
    updated = 0
    for doc in by_email.values():
        result = collection.update_one(
            {"email": doc["email"]},
            {
                "$set": {
                    "areas_interesse": doc["areas_interesse"],
                    "segmentos": doc["segmentos"],
                    "updated_at": now,
                },
                "$setOnInsert": {
                    "email": doc["email"],
                    "origem": ORIGEM,
                    "created_at": now,
                },
            },
            upsert=True,
        )
        if result.upserted_id is not None:
            inserted += 1
        else:
            updated += 1

    print(f"\nGravacao concluida: {inserted} inseridos, {updated} atualizados.")
    print(f"Total agora em '{DOCENTES_COLLECTION}': {collection.count_documents({})}")


if __name__ == "__main__":
    main()
