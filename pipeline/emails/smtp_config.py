from __future__ import annotations

import os

from dotenv import load_dotenv


def is_smtp_configured() -> bool:
    """
    Diz se ha credencial de SMTP para enviar e-mail.

    Estava repetido dentro de cada notifier; ficou aqui para existir uma unica
    resposta para "da pra enviar e-mail agora?" em todo o projeto.
    """
    load_dotenv(override=True)
    return bool((os.getenv("SMTP_USER") or "").strip()) and bool(
        (os.getenv("SMTP_PASS") or "").strip()
    )
