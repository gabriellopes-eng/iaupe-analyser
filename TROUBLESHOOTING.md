# Guia de Operação e Solução de Problemas

Este documento complementa o [README.md](README.md). Enquanto o README explica a arquitetura e como rodar o projeto, este arquivo registra **como o sistema roda em produção de fato**, partes que não são óbvias lendo o código, e os problemas reais que já apareceram (com a causa e a correção).

## 1. Onde cada coisa roda de verdade

Um ponto que gerou confusão: existem **dois lugares de configuração diferentes**, e eles não se sincronizam sozinhos.

| | `.env` local | Secrets do GitHub (`Settings -> Secrets and variables -> Actions`) |
|---|---|---|
| Usado por | Execução manual na sua máquina (`python main.py ...`) | Os workflows agendados (`pipeline_runner_daily.yml`, `deadline-reminders.yml`) |
| Onde vive | Só no seu computador, nunca commitado (está no `.gitignore`) | Na nuvem, no repositório do GitHub |
| Como ver o valor atual | Abrindo o arquivo | **Não dá.** O GitHub esconde o valor depois de salvo — só dá pra sobrescrever |

**Implicação prática:** se você mudar uma credencial no `.env` local (ex: trocar a senha do SMTP), isso **não** atualiza o Secret do GitHub. São dois lugares independentes que só coincidem se você atualizar os dois manualmente. Foi exatamente isso que causou o incidente de "editais não chegam por email" (seção 4.1).

A produção **não depende da sua máquina estar ligada**. O cron do GitHub Actions dispara sozinho, lê o código do branch `main`, e usa os Secrets — nada local é necessário no dia a dia.

## 2. Fluxo de email e identidade visual

- `pipeline/emails/smtp_email_service.py`: monta a mensagem como `multipart/related` e embute os logos institucionais (UPE/IIT) como imagens **inline** (`cid:`), lidos de `pipeline/emails/assets/`. Isso é mais confiável do que linkar uma URL externa, que muitos clientes de email bloqueiam por padrão.
- `pipeline/emails/email_branding.py`: HTML compartilhado da faixa de logos, usado pelos dois templates (`saved_record_email_notifier.py` e `deadline_reminder_email_notifier.py`) pra não duplicar o cabeçalho.
- Paleta oficial usada nos templates: vermelho UPE `#db261d` (variante clara `#e2382d`) e azul IIT `#164072` (variante clara `#2160ab`) — extraída diretamente dos arquivos de logo, não são cores "genéricas".
- O email só é enviado quando o formulário de destinatário (`RECIPIENT_EMAIL` no `.env`/Secret) está preenchido. Sem isso, `notifier.is_enabled()` retorna `False` e a notificação é pulada silenciosamente (é esperado, não é erro).

## 3. Extração de PDF e o fallback de OCR

`pipeline/pdf_pipeline/extractor.py` tenta extrair texto de duas formas, em ordem:

1. **`pdfplumber`** (rápido, cobre a maioria dos PDFs — documentos gerados direto de Word/LibreOffice, etc.)
2. **OCR via Tesseract** (fallback, só roda quando o passo 1 retorna vazio)

### Quando o passo 1 falha

PDFs podem não ter nenhum caractere extraível em dois cenários:

- **Scan/foto real** de um documento físico.
- **PDF "impresso" como vetor**: cada letra é desenhada como forma geométrica (retângulos/curvas) em vez de caractere de fonte. Acontece quando alguém abre um documento num visualizador que bloqueia cópia/seleção de texto (comum em sistemas protegidos) e usa "Imprimir para PDF". Visualmente parece um PDF normal e nítido — a diferença só aparece tecnicamente (`page.chars` vazio, mas `page.rects`/`page.curves` com centenas de itens).

Nos dois casos, a única forma de "ler" o conteúdo é renderizar a página como imagem e rodar reconhecimento de caracteres (OCR) em cima dela — por isso o fallback funciona igual para ambos os cenários.

### Dependências do OCR

- Lib Python: `pytesseract` + `pypdfium2` (em `requirements.txt`).
- Binário do sistema: `tesseract-ocr` + pacote de idioma `tesseract-ocr-por`, instalados via `apt-get` no workflow (`pipeline_runner_daily.yml`, passo "Install Tesseract OCR"). **Isso não é uma lib Python comum — é um programa externo.** Se você rodar localmente no Windows sem instalar o Tesseract separadamente (`winget install UB-Mannheim.TesseractOCR` + baixar `por.traineddata`), o OCR falha silenciosamente e a função retorna string vazia (não quebra a pipeline, só não extrai nada).
- Limite de 20 páginas por padrão no OCR (`OCR_MAX_PAGES_DEFAULT`), porque é bem mais lento que extração direta — evita estourar tempo em documentos enormes sem texto.

## 4. Problemas reais já encontrados

### 4.1 Emails pararam de chegar (SMTP_PASS desatualizado)

**Sintoma:** pipeline rodava com sucesso (verde no Actions), mas nenhum email chegava.

**Causa:** o Secret `SMTP_USER`/`SENDER_EMAIL`/`RECIPIENT_EMAIL` foi atualizado no GitHub (troca de conta de email), mas o Secret `SMTP_PASS` continuou com o valor antigo. Senha de app do Gmail é vinculada à conta — trocar a conta sem trocar a senha junto quebra a autenticação.

**Como diagnosticar:** na tela de Secrets do GitHub, comparar a data de "last updated" de `SMTP_USER`/`SENDER_EMAIL` com a de `SMTP_PASS`. Se a senha for mais antiga que o usuário, é esse o problema.

**Correção:** gerar uma nova senha de app na conta do Gmail (`myaccount.google.com` -> Segurança -> Senhas de app, exige verificação em duas etapas ativada) e atualizar o Secret `SMTP_PASS`.

### 4.2 Edital com "Texto vazio" nunca processa (PDF vetorial/escaneado)

**Sintoma:** log mostra `Texto vazio.` pra um PDF específico, e ele fica salvo no Mongo com `status: "erro"`, sem nunca virar um registro válido.

**Causa:** ver seção 3 — PDF sem camada de texto real.

**Correção:** implementado o fallback de OCR (ver seção 3). Editais que caírem nesse caso agora são reprocessados com OCR automaticamente na próxima execução, já que `already_exists()` só ignora documentos com `status="ok"` — um documento com `status="erro"` é tentado de novo a cada rodada.

### 4.3 Edital corrigido (erro -> ok) não dispara email

**Sintoma:** um edital que falhou uma vez (ex: por causa do 4.2) e depois foi reprocessado com sucesso não gerava nenhum email de notificação, mesmo sendo a primeira vez que ficou válido.

**Causa:** em `pipeline_runner.py`, o envio de email só acontecia quando `save()` retornava `"inserted"` (documento totalmente novo no Mongo). Quando o `url_pdf` já existia (mesmo que com `status="erro"`), `save()` retorna `"updated"`, e essa condição não cobria o caso.

**Correção:** a condição de envio agora aceita tanto `"inserted"` quanto `"updated"`. Isso é seguro porque `already_exists()` só deixa o código chegar nesse ponto quando o status anterior **não** era `"ok"` — ou seja, qualquer resultado válido que chegue até ali é, por definição, a primeira vez que aquele edital vira um registro utilizável.

### 4.4 CAPES falha com "Network is unreachable" (em aberto)

**Sintoma:** no log do workflow, a fonte CAPES falha com:
```
Erro ao acessar CAPES: HTTPSConnectionPool(host='gov.br', port=443): ... Failed to establish a new connection: [Errno 101] Network is unreachable
```

**Causa provável:** o runner hospedado do GitHub Actions não está conseguindo estabelecer conexão de rede com `gov.br` (pode ser bloqueio de IPv6, firewall do lado do gov.br pro range de IP do datacenter do GitHub, ou instabilidade pontual). Rodar a mesma URL de uma máquina local funciona normalmente.

**Status:** não corrigido ainda. As outras fontes (FACEPE, CNPq, FINEP) não são afetadas — é um problema específico de conectividade com o domínio `gov.br` a partir da rede do runner.

### 4.5 Execução agendada roda com sucesso mas não envia nenhum email

**Isso nem sempre é um bug.** O pipeline só envia email quando processa um edital **novo** (não estava salvo com `status="ok"` antes). Se todas as fontes já tinham tudo salvo (nada novo publicado desde a última execução), a run termina com sucesso e zero emails — comportamento esperado, não erro. Confira o resumo no final do log de cada fonte (`found=`, `already_saved=`, `emails_sent=`) antes de assumir que é bug.

## 5. Fluxo de release

Tags/releases (`vX.Y.Z`) marcam pontos de entrega, mas **não têm nenhum efeito técnico** nos workflows — o cron sempre roda em cima do estado atual do branch `main`, com ou sem tag. Servem só como referência histórica (ex: "essa era a versão apresentada na reunião X"). Criar uma tag é opcional, feito manualmente pela tela de Releases do GitHub, geralmente depois de mesclar um PR de `develop` para `main`.

## 6. Ferramentas locais úteis

- **`gh` CLI** (GitHub CLI): permite consultar Secrets (só nomes/datas, não valores) e logs de execução direto do terminal. Precisa de `gh auth login` (fluxo interativo pelo navegador).
- **Tesseract OCR** (`winget install UB-Mannheim.TesseractOCR`): necessário só se for testar o fallback de OCR localmente no Windows. Por padrão só instala o idioma inglês — o pacote de português (`por.traineddata`) precisa ser baixado à parte e colocado na pasta `tessdata` da instalação (ou apontado via variável de ambiente `TESSDATA_PREFIX`).
