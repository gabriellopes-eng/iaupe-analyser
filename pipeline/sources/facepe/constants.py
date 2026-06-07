SOURCE_KEY = "facepe"
SOURCE_LABEL = "FACEPE"
BASE_URL = "https://www.facepe.br/editais/todos/?c=aberto"
MONGO_COLLECTION = "editais_facepe"

REQUEST_HEADERS = {"User-Agent": "Mozilla/5.0"}

ACCESSORY_KEYWORDS = (
    "enquadramento",
    "errata",
    "homologacao",
    "lista",
    "prorrogacao",
    "relacao",
    "resultado",
    "retificacao",
    "rodada",
)

MONTHS = {
    "janeiro": 1,
    "fevereiro": 2,
    "marco": 3,
    "abril": 4,
    "maio": 5,
    "junho": 6,
    "julho": 7,
    "agosto": 8,
    "setembro": 9,
    "outubro": 10,
    "novembro": 11,
    "dezembro": 12,
}
