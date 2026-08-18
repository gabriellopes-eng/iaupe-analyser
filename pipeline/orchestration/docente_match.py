from __future__ import annotations

import re
from typing import Iterable, NamedTuple

# ============================================================================
# CORACAO DO ALGORITMO DESTA SPRINT (Task 2 - notificar por area/segmento)
#
# Esta funcao (match_docentes, mais abaixo) responde UMA pergunta: pra um
# edital que acabou de ser salvo, QUAIS docentes devem ser avisados?
#
# A regra, em uma frase: se o docente marcou pelo menos UMA area OU UM
# segmento que tambem esta no edital, ele entra na lista. Caso contrario, fica
# de fora. E so isso - o resto do sistema (docente_notification_service.py)
# so decide COMO enviar; QUEM recebe e decidido aqui.
# ============================================================================


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
    # PASSO 1 - pega o lado do EDITAL: as areas/segmentos que o Gemini
    # classificou nele, normalizados (sem espaco, sem maiuscula) pra servirem
    # de "chave de busca". Guarda tambem o texto original (str(a)/str(s)) pra
    # poder mostrar no e-mail o nome bonito, com acento e caixa corretos.
    areas_por_norma = {normalize_option(a): str(a) for a in (areas_edital or []) if normalize_option(a)}
    segmentos_por_norma = {
        normalize_option(s): str(s) for s in (segmentos_edital or []) if normalize_option(s)
    }

    # Edital sem NENHUMA classificacao (Gemini nao identificou area/segmento)
    # -> ninguem casa. Preferir nao notificar a notificar todo mundo por engano.
    if not areas_por_norma and not segmentos_por_norma:
        return []

    matches: dict[str, DocenteMatch] = {}

    # PASSO 2 - agora pega o lado do DOCENTE, um de cada vez, e compara.
    for docente in docentes or []:
        email = str(docente.get("email") or "").strip().lower()
        if not email or email in matches:
            continue

        # A COMPARACAO em si: intersecao de conjuntos. "& areas_por_norma.keys()"
        # e a pergunta "quais areas do docente TAMBEM estao no edital?" - se a
        # resposta for vazia, essa metade nao casou.
        areas_comuns = sorted(
            areas_por_norma[n] for n in _normalized_set(docente.get("areas_interesse")) & areas_por_norma.keys()
        )
        segmentos_comuns = sorted(
            segmentos_por_norma[n]
            for n in _normalized_set(docente.get("segmentos")) & segmentos_por_norma.keys()
        )

        # PASSO 3 - a regra de decisao: e "OU", nao "E". Uma area em comum OU
        # um segmento em comum ja basta pra entrar na lista. So fica de fora
        # quem nao teve NENHUM dos dois em comum.
        if not areas_comuns and not segmentos_comuns:
            continue

        # Docente aprovado: guarda tambem QUAIS valores casaram (usado no corpo
        # do e-mail, pra explicar pra pessoa por que ela recebeu essa mensagem).
        matches[email] = DocenteMatch(email=email, areas=areas_comuns, segmentos=segmentos_comuns)

    # Fim do algoritmo: devolve so quem casou. A partir daqui, quem decide COMO
    # enviar (limite por pessoa, quem ja recebeu antes, envio de fato) e outro
    # arquivo: orchestration/docente_notification_service.py.
    return sorted(matches.values(), key=lambda m: m.email)
