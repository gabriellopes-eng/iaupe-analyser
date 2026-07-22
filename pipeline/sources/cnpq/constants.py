import re

SOURCE_KEY = "cnpq"
SOURCE_LABEL = "CNPq"
BASE_URL = (
    "http://memoria2.cnpq.br/web/guest/chamadas-publicas"
    "?p_p_id=resultadosportlet_WAR_resultadoscnpqportlet_INSTANCE_0ZaM"
    "&filtro=abertas"
)

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
DATE_REGEX = re.compile(r"\b(\d{2}/\d{2}/\d{4})\b")
URL_REGEX = re.compile(r"https?://[^\s'\"<>]+", re.IGNORECASE)
