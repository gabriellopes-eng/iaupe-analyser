# <img width="30" height="30" alt="image" src="https://github.com/user-attachments/assets/f0b62fea-7617-4b5f-b298-4446b3995eff" /> IAUPE Analyzer - Pipeline de Editais Multi-Fonte

## Visao Geral

O IAUPE Analyzer e um pipeline Python para:

1. Coletar links de editais por fonte.
2. Extrair texto dos documentos PDF ou paginas HTML.
3. Analisar conteudo com IA (Gemini).
4. Salvar resultados estruturados no MongoDB.
5. Enviar notificacoes por email para editais novos e lembretes de prazo.

O pipeline de producao esta organizado em modulos por responsabilidade, com orquestracao central e fontes plugaveis.

## Fontes Suportadas

| Fonte  | Chave (`--source`) | Collection Mongo |
|--------|---------------------|------------------|
| FACEPE | `facepe`            | `editais_facepe` |
| CNPq   | `cnpq`              | `editais_cnpq`   |
| FINEP  | `finep`             | `editais_finep`  |
| CAPES  | `capes`             | `editais_capes`  |

## Arquitetura da Pipeline

Fluxo principal:

```text
Fonte selecionada (--source)
-> collect_links (scraper da fonte)
-> extractor (texto do PDF/HTML)
-> analyzer (JSON estruturado via Gemini)
-> save (MongoDB na collection da fonte)
-> email (quando o registro e novo e valido)
```

Estrutura de producao:

```text
pipeline/
|-- main.py                         # entrypoint da CLI
|-- orchestration/
|   |-- pipeline_runner.py           # fluxo completo da pipeline
|   |-- deadline_reminder_runner.py  # fluxo de lembretes (D-30, D-15, D-7)
|   |-- source_registry.py           # registro e resolucao de fontes
|   |-- settings.py                  # configs de execucao (env/limites/sleeps)
|   |-- retry_policy.py              # retry de erros temporarios do Gemini
|   `-- date_parser.py               # parse da data_limit_submissao
|-- sources/
|   |-- facepe/                      # scraper modularizado da FACEPE
|   |-- cnpq/                        # scraper modularizado do CNPq
|   |-- finep/                       # scraper modularizado da FINEP
|   |-- capes/                       # scraper modularizado da CAPES
|   |-- scraper_facepe.py            # wrapper de compatibilidade
|   |-- scraper_cnpq.py              # wrapper de compatibilidade
|   `-- scraper_capes.py             # wrapper de compatibilidade
|-- pdf_pipeline/
|   |-- extractor.py                 # extracao de texto de PDF/HTML
|   `-- analyzer.py                  # analise via Gemini
|-- db/
|   `-- mongo.py                     # persistencia e cache de conexao MongoDB
`-- emails/
    |-- email.py
    |-- emails_service.py
    |-- smtp_email_service.py
    |-- send_email_use_case.py
    |-- saved_record_email_notifier.py
    `-- deadline_reminder_email_notifier.py
```

## Fontes Modularizadas

As fontes principais ficam em pacotes dentro de `pipeline/sources/`. Cada pacote expoe uma API publica pelo `__init__.py`, usada pelo `source_registry`.

Estrutura padrao dos pacotes:

- `constants.py`: chave da fonte, label, URL base, collection Mongo e constantes de coleta.
- `client.py`: comunicacao HTTP/API da fonte.
- `models.py`: objetos internos usados para ordenar e filtrar documentos.
- `parser.py`: leitura do HTML/API e transformacao em objetos estruturados.
- `policy.py`: regras de negocio da fonte, como ano-alvo e filtro de edital principal.
- `scraper.py`: orquestracao final e funcao `collect_links()`.
- `__init__.py`: API publica do pacote.

Os arquivos `scraper_facepe.py`, `scraper_cnpq.py` e `scraper_capes.py` existem apenas como wrappers de compatibilidade para imports antigos.

## Regras de Coleta Recente

A pipeline envia email quando um link novo e salvo no MongoDB com status `inserted` e sem erro de analise. Portanto, "novo" significa "ainda nao processado com sucesso no banco".

Regras por fonte:

- FACEPE: coleta somente editais principais do ano-alvo, remove documentos acessorios como resultado, errata, enquadramento e prorrogacao, e ordena por data de publicacao mais recente.
- CNPq: coleta chamadas abertas, le a data inicial de inscricao quando disponivel e prioriza chamadas com inscricao mais recente.
- FINEP: usa a API da FINEP com `sort=dataDePublicacao:desc`, filtra chamadas abertas e limita as 8 chamadas mais recentes.
- CAPES: segue a ordem oficial da secao "Editais Abertos" no site da CAPES, filtra apenas editais principais do ano-alvo e ignora anexos, termos, modelos, portarias, alteracoes e documentos auxiliares.

Variaveis opcionais para testes ou execucoes controladas:

```env
FACEPE_TARGET_YEAR=2026
CAPES_TARGET_YEAR=2026
```

## Requisitos

- Python 3.10+
- Ambiente virtual
- Dependencias em `requirements.txt`
- Chave Gemini valida
- MongoDB (local ou Atlas)

## Instalacao

1. Criar ambiente virtual:

```powershell
python -m venv .venv
```

2. Ativar ambiente virtual (PowerShell):

```powershell
.\.venv\Scripts\Activate.ps1
```

3. Instalar dependencias:

```powershell
pip install -r requirements.txt
```

## Configuracao (.env)

Exemplo:

```env
GEMINI_API_KEY=sua_chave_aqui

MONGODB_URI=mongodb+srv://...
MONGODB_DB=iaupe-analyser

PIPELINE_SOURCE=facepe
PIPELINE_LIMIT=all

SLEEP_ALREADY_EXISTS=5
SLEEP_NEW_PROCESS=60
SLEEP_EMPTY_TEXT=5
MAX_RETRIES_GEMINI=3

MONGODB_SERVER_SELECTION_TIMEOUT_MS=30000
MONGODB_CONNECT_TIMEOUT_MS=30000
MONGODB_SOCKET_TIMEOUT_MS=30000

SMTP_HOST=sandbox.smtp.mailtrap.io
SMTP_PORT=2525
SMTP_USER=seu_usuario_mailtrap
SMTP_PASS=sua_senha_mailtrap
SENDER_EMAIL=from@example.com
RECIPIENT_EMAIL=to@example.com
```

Observacoes:

- A collection no Mongo e definida pela fonte selecionada.
- `MONGODB_COLLECTION` funciona como fallback interno quando nenhuma collection e informada na chamada.
- Para desativar persistencia mesmo com URI definida, use `MONGODB_ENABLED=0`.
- O remetente do email e definido por `SENDER_EMAIL`.
- `RECIPIENT_EMAIL` aceita um ou varios emails separados por virgula.
- Quando houver varios destinatarios, o sistema envia um email unico com todos em copia (Cc).

## Execucao da Pipeline

Na raiz do projeto:

```powershell
python .\pipeline\main.py --source facepe --limit 10
```

Ou dentro da pasta `pipeline`:

```powershell
python .\main.py --source facepe --limit 10
```

Exemplos:

```powershell
python .\pipeline\main.py --source cnpq
python .\pipeline\main.py --source finep --limit 5
python .\pipeline\main.py --source capes
```

Sem `--source`, o padrao e `facepe`.

## Automacao no GitHub Actions

Workflow principal:

- `.github/workflows/pipeline_runner_daily.yml`
- Agendado diariamente.
- Roda as fontes configuradas em `PIPELINE_SOURCES`.
- Por padrao processa `1` edital por fonte por dia (`PIPELINE_LIMIT_PER_SOURCE=1`) para reduzir risco de estourar quota do Gemini.

Fluxo de envio:

1. O scraper devolve links ordenados conforme a regra da fonte.
2. A pipeline pula links ja salvos com `status=ok`.
3. O primeiro link pendente dentro do limite e processado.
4. Se o registro for `inserted` e a analise nao tiver erro, o email HTML e enviado.

## Lembretes de Prazo (D-30, D-15, D-7)

O projeto possui um fluxo dedicado para notificacoes de prazo de submissao.

Como funciona:

1. Busca editais com `status=ok` e `data_limit_submissao` na janela dos marcos configurados.
2. Calcula os dias restantes para o prazo.
3. Envia email quando o prazo bater com um marco (ex.: 30, 15, 7).
4. Marca no MongoDB em `deadline_reminder.sent_steps` para evitar reenvio duplicado.

Execucao local dos lembretes:

```powershell
python .\pipeline\main.py --source cnpq --run-reminders --reminder-steps 30,15,7
```

Exemplo para somente D-7:

```powershell
python .\pipeline\main.py --source cnpq --run-reminders --reminder-steps 7
```

Automacao dos lembretes:

- Workflow: `.github/workflows/deadline-reminders.yml`
- Agendado diariamente e com suporte a disparo manual (`workflow_dispatch`).

## Tratamento de Erros

- Retry de IA para `429` (respeita tempo sugerido na mensagem).
- Retry de IA para `503` (backoff progressivo).
- Falha de Mongo pode desabilitar persistencia sem derrubar toda a execucao.
- Persistencia com insert/update por `url_pdf` (indice unico).
- Falhas em subpaginas de fontes externas podem ser ignoradas com log quando nao impedem a coleta dos demais editais.

## Como Adicionar Nova Fonte

1. Criar um pacote em `pipeline/sources/nova_fonte/`.
2. Definir pelo menos:
   - `SOURCE_KEY`
   - `SOURCE_LABEL`
   - `BASE_URL`
   - `MONGO_COLLECTION`
   - `collect_links(url_lista: str) -> list[str]`
3. Expor a API publica em `pipeline/sources/nova_fonte/__init__.py`.
4. Registrar a fonte em `pipeline/orchestration/source_registry.py`.

## Sandbox (Area de Teste de Desenvolvimento)

A pasta `sandbox/` e uma area de teste de desenvolvimento.

Ela existe para validar experimentos sem acoplar direto na pipeline de producao, por exemplo:

- teste de conexao com MongoDB
- teste de Gemini
- teste de envio SMTP (Mailtrap)
- teste de integracao do fluxo de lembrete

Scripts atuais no sandbox:

- `sandbox/test_atlas.py`
- `sandbox/test_gemini.py`
- `sandbox/test_email_mailtrap.py`
- `sandbox/check_mongo_coverage.py`
- `sandbox/test_deadline_reminder_integration.py`

Teste de integracao de lembrete (sem pipeline de producao):

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7
```

Modo real (envia email):

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7 --send-email
```

## Boas Praticas

- Nao versionar `.env`.
- Nao expor credenciais em commits, logs ou README.
- Rotacionar chaves caso alguma seja exposta.

## Como Trocar o Modelo de IA

O pipeline atualmente esta integrado ao Google Gemini via SDK `google.genai`.

Para trocar apenas o modelo Gemini, altere a constante `MODEL` em `pipeline/pdf_pipeline/analyzer.py`:

```python
MODEL = "gemini-2.5-pro"
```

Para usar outro provedor/modelo, nao basta trocar o nome do modelo. Sera necessario:

- instalar o SDK ou biblioteca do novo provedor;
- implementar uma funcao de chamada especifica;
- adaptar autenticacao, envio de prompt e parsing da resposta;
- manter uma interface semelhante a `call_gemini` para facilitar manutencao.
