# IAUPE Analyzer - Pipeline de Editais Multi-Fonte

## Visao Geral

O IAUPE Analyzer e um pipeline Python para:

1. Coletar links de editais por fonte.
2. Extrair texto dos documentos PDF.
3. Analisar conteudo com IA (Gemini).
4. Salvar resultados estruturados no MongoDB.

O pipeline de producao esta organizado em modulos por responsabilidade, com orquestracao central e componentes desacoplados.

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
-> extractor (texto do PDF)
-> analyzer (JSON estruturado)
-> save (MongoDB na collection da fonte)
```

Estrutura de producao:

```text
pipeline/
├── main.py                      # entrypoint da CLI
├── orchestration/
│   ├── pipeline_runner.py       # fluxo completo da pipeline
│   ├── deadline_reminder_runner.py # fluxo de lembretes (D-30, D-15, D-7)
│   ├── source_registry.py       # registro e resolucao de fontes
│   ├── settings.py              # configs de execucao (env/limites/sleeps)
│   ├── retry_policy.py          # retry de erros temporarios do Gemini
│   └── date_parser.py           # parse da data_limit_submissao
├── sources/
│   ├── scraper_facepe.py
│   ├── scraper_cnpq.py
│   ├── finep/
│   │   ├── __init__.py
│   │   ├── constants.py
│   │   ├── client.py
│   │   └── scraper.py
│   └── scraper_capes.py
├── pdf_pipeline/
│   ├── extractor.py             # extracao de texto de PDF
│   └── analyzer.py              # analise via Gemini
├── db/
│   └── mongo.py                 # persistencia e cache de conexao MongoDB
└── emails/
   ├── email.py
   ├── emails_service.py
   ├── smtp_email_service.py
   ├── send_email_use_case.py
   ├── saved_record_email_notifier.py
   └── deadline_reminder_email_notifier.py
```

## Estrutura da FINEP (Atualizada)

A fonte FINEP foi modularizada em pacote proprio para facilitar manutencao e testes.

- `pipeline/sources/finep/constants.py`: constantes da fonte (rotas, collection, credenciais publicas de client).
- `pipeline/sources/finep/client.py`: comunicacao HTTP com endpoints da FINEP (token, chamadas e documentos).
- `pipeline/sources/finep/scraper.py`: regra de coleta e filtro dos PDFs prioritarios.
- `pipeline/sources/finep/__init__.py`: API publica do pacote para uso no `source_registry`.

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

# SMTP (para testes com Mailtrap ou outro servidor SMTP)
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
- O remetente do e-mail é definido por `SENDER_EMAIL` e o destinatário por `RECIPIENT_EMAIL`.

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

## Lembretes de Prazo (D-30, D-15, D-7)

O projeto agora possui um fluxo dedicado para notificacoes de prazo de submissao.

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

Automacao no GitHub Actions:

- Workflow: `.github/workflows/deadline-reminders.yml`
- Agendado diariamente e com suporte a disparo manual (`workflow_dispatch`).

## Tratamento de Erros

- Retry de IA para `429` (respeita tempo sugerido na mensagem).
- Retry de IA para `503` (backoff progressivo).
- Falha de Mongo pode desabilitar persistencia sem derrubar toda a execucao.
- Persistencia com insert/update por `url_pdf` (indice unico).

## Como Adicionar Nova Fonte

1. Criar arquivo em `pipeline/sources/`, por exemplo `scraper_nova_fonte.py`.
2. Definir:
   - `SOURCE_KEY`
   - `SOURCE_LABEL`
   - `BASE_URL`
   - `MONGO_COLLECTION`
   - `collect_links(url_lista: str) -> list[str]`
3. Registrar a fonte em `pipeline/orchestration/source_registry.py`.

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

Modo simulacao (nao envia email):

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7
```

Modo real (envia email):

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7 --send-email
```

Opcional para forcar destinatario:

```powershell
python .\sandbox\test_deadline_reminder_integration.py --source cnpq --step 7 --send-email --recipient seu_email@dominio.com
```

## Boas Praticas

- Nao versionar `.env`.
- Nao expor credenciais em commits, logs ou README.
- Rotacionar chaves caso alguma seja exposta.

# Como trocar o modelo de IA (Gemini) ou usar outro agente

O pipeline foi projetado para ser flexível, mas atualmente está integrado ao Google Gemini (via SDK `google.genai`).

Se você quiser usar outro modelo de IA (como Qwen, Haama, GPT, etc.), siga estas orientações:

### 1. Trocar apenas o modelo Gemini (ex: de `gemini-2.5-flash` para outro Gemini ou agente)

- Basta alterar a constante `MODEL` em `pipeline/pdf_pipeline/analyzer.py`:
   ```python
   MODEL = "gemini-2.5-pro"  # ou outro modelo Gemini disponível
   # ou
   MODEL = "agente"  # se o backend/SDK suportar esse nome
   ```
- **Limite:** O modelo precisa ser suportado pelo Google GenAI SDK ou pelo backend configurado.

### 2. Usar outro provedor/modelo (Qwen, Haama, GPT, etc.)

- **Não basta trocar o nome do modelo.**
- Você precisará:
   - Instalar o SDK ou biblioteca do novo provedor (ex: `pip install dashscope` para Qwen, `openai` para GPT, etc.).
   - Implementar uma função de chamada específica para o novo modelo (ex: `call_qwen`, `call_gpt`).
   - Adaptar a autenticação, o envio do prompt e o parsing da resposta conforme a documentação do novo SDK/API.
   - Substituir a chamada a `call_gemini` por sua nova função no fluxo de análise.

#### Exemplo de pontos a adaptar:
- **Autenticação:** cada provedor usa um método diferente (API key, token, etc.).
- **Limite de tokens:** cada modelo tem limites próprios para prompt e resposta.
- **Formato de resposta:** pode ser texto puro, JSON, ou outro formato — ajuste o parsing conforme necessário.
- **Desempenho:** a qualidade e velocidade variam entre modelos; recomenda-se testar antes de migrar em produção.

### 3. Recomendações

- Sempre consulte a documentação oficial do modelo/SDK que deseja usar.
- Teste localmente em uma cópia da pipeline antes de migrar para produção.
- Se criar uma nova função de chamada, mantenha a interface semelhante à de `call_gemini` para facilitar a troca.