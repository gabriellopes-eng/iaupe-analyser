from __future__ import annotations

from dataclasses import dataclass

# Esta entidade representa um email pronto para envio.
# A ideia aqui e centralizar a validacao minima antes de chegar no servico SMTP.


def _normalize_recipient_list(raw: object) -> tuple[str, ...]:
    """
    Normaliza uma lista de destinatarios (para o campo `bcc`).

    Aceita lista/tupla de strings OU uma string separada por virgula. Remove
    espacos das bordas, descarta vazios e faz dedupe sem diferenciar maiuscula
    de minuscula, preservando a ordem da primeira ocorrencia.
    """
    if raw is None:
        return ()

    if isinstance(raw, str):
        parts = raw.split(",")
    else:
        parts = list(raw)

    resultado: list[str] = []
    vistos: set[str] = set()
    for part in parts:
        endereco = str(part or "").strip()
        if not endereco:
            continue
        chave = endereco.lower()
        if chave in vistos:
            continue
        vistos.add(chave)
        resultado.append(endereco)

    return tuple(resultado)


@dataclass(frozen=True)
class Email:
    """Entidade de email com validacao minima para envio seguro."""
    to: str
    subject: str
    text: str | None = None
    html: str | None = None
    # Destinatarios em copia oculta. Usado quando um mesmo e-mail vai para varias
    # pessoas que NAO devem ver o endereco umas das outras (ex.: notificacao de
    # edital novo para todos os docentes que casam). Tupla (nao lista) para
    # combinar com frozen=True e nao ter default mutavel.
    bcc: tuple[str, ...] = ()

    @staticmethod
    def create(data: dict) -> "Email":
        """Fabrica de Email a partir de dict com validacao de campos obrigatorios."""
        # A pipeline monta payloads simples em dict.
        # Este metodo converte esse payload para um objeto de dominio validado.
        to = (data.get("to") or "").strip()
        subject = (data.get("subject") or "").strip()
        text = data.get("text")
        html = data.get("html")
        bcc = _normalize_recipient_list(data.get("bcc"))

        # Precisa de pelo menos um destino: `to` (envio comum/Cc) ou `bcc`
        # (envio em copia oculta). O servico SMTP sintetiza um `To` visivel
        # quando so ha `bcc`.
        if not to and not bcc:
            raise ValueError("Email precisa de 'to' ou 'bcc'")
        if not subject:
            raise ValueError("Email.subject e obrigatorio")
        if not (text or html):
            raise ValueError("Informe ao menos text ou html")

        # Se passou pela validacao, o restante do fluxo trabalha com um objeto consistente.
        return Email(to=to, subject=subject, text=text, html=html, bcc=bcc)
