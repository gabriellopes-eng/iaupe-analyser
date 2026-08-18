from __future__ import annotations

import re
from typing import Iterable, NamedTuple


class DocenteMatch(NamedTuple):
    """Um docente que casa com o edital, e o motivo do casamento."""

    email: str
    areas: list[str]
    segmentos: list[str]


def normalize_option(value: object) -> str:
    """
    Normaliza um valor de catalogo (area ou segmento) para comparacao.

    Remove TODOS os espacos (inclusive internos) e baixa a caixa. Sem isso, o
    valor legado da planilha "Tecnologia da informação( TI)" nunca casaria com
    o "Tecnologia da informação(TI)" que o Gemini grava nos editais, e o docente
    simplesmente nunca receberia e-mail - falha silenciosa, sem erro nenhum no
    log. O front resolve o mesmo problema filtrando pelo catalogo atual
    (front/src/domain/docente.ts::filterKnownOptions).
    """
    return re.sub(r"\s+", "", str(value or "")).lower()


def _normalized_set(values: Iterable[object] | None) -> set[str]:
    return {norm for norm in (normalize_option(v) for v in (values or [])) if norm}


def match_docentes(
    docentes: Iterable[dict],
    areas_edital: Iterable[object] | None,
    segmentos_edital: Iterable[object] | None,
) -> list[DocenteMatch]:
    """
    Cruza a lista de docentes com as areas/segmentos classificados num edital.

    A regra e OU, nao E: basta uma area OU um segmento em comum para o docente
    entrar na lista. Se o edital nao tiver nenhuma area e nenhum segmento
    (classificacao vazia), ninguem casa - preferir nao notificar a notificar
    todo mundo por engano.

    Devolve tambem QUAIS valores casaram (rotulos do edital), usados no corpo do
    e-mail para explicar a pessoa por que ela recebeu aquela mensagem.
    """
    areas_por_norma = {normalize_option(a): str(a) for a in (areas_edital or []) if normalize_option(a)}
    segmentos_por_norma = {
        normalize_option(s): str(s) for s in (segmentos_edital or []) if normalize_option(s)
    }
    if not areas_por_norma and not segmentos_por_norma:
        return []

    matches: dict[str, DocenteMatch] = {}
    for docente in docentes or []:
        email = str(docente.get("email") or "").strip().lower()
        if not email or email in matches:
            continue

        areas_comuns = sorted(
            areas_por_norma[n] for n in _normalized_set(docente.get("areas_interesse")) & areas_por_norma.keys()
        )
        segmentos_comuns = sorted(
            segmentos_por_norma[n]
            for n in _normalized_set(docente.get("segmentos")) & segmentos_por_norma.keys()
        )

        if not areas_comuns and not segmentos_comuns:
            continue

        matches[email] = DocenteMatch(email=email, areas=areas_comuns, segmentos=segmentos_comuns)

    return sorted(matches.values(), key=lambda m: m.email)
