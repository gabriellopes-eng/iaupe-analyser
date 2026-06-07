SOURCE_KEY = "capes"
SOURCE_LABEL = "CAPES"
BASE_URL = "https://www.gov.br/capes/pt-br/assuntos/editais-e-resultados-capes"
MONGO_COLLECTION = "editais_capes"

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}
REQUEST_TIMEOUT = 30
REQUEST_ATTEMPTS = 3

ACCESSORY_KEYWORDS = (
    "alteracao",
    "anexo",
    "comunicado",
    "cronograma",
    "declaracao",
    "modelo",
    "portaria",
    "resultado",
    "retificacao",
    "termo",
)
