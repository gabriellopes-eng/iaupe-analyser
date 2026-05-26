SOURCE_KEY = "finep"
SOURCE_LABEL = "FINEP"
BASE_URL = "https://www.finep.gov.br/oportunidades"
MONGO_COLLECTION = "editais_finep"

OAUTH_TOKEN_PATH = "/o/oauth2/token"
CHAMADAS_API_PATH = "/o/c/chamadapublicas?sort=dataDePublicacao:desc"
DOCUMENTOS_API_PATH_TEMPLATE = "/o/c/chamadapublicas/{chamada_id}/documentos?sort=dataDePublicacao:desc"
CHAMADA_DETAIL_PATH_TEMPLATE = "/e/chamada-publica/222684/{chamada_id}"

FIRST_PAGE = 1
MAX_CALLS_FIRST_PAGE = 8

OAUTH_CLIENT_ID = "idClientPRD"
OAUTH_CLIENT_SECRET = "secretClientPRD"