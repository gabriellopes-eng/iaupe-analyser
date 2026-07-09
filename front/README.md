# IAUPE Analyzer — Front (Next.js)

Frontend da funcionalidade **"editais de interesse"**: o pesquisador marca os editais
que acompanha e passa a receber lembretes de prazo (D-30, D-15, D-7) **apenas dos
selecionados**, em vez de todos.

Este módulo é independente da pipeline Python. O **único ponto de integração** é o
MongoDB compartilhado: o front lê as collections `editais_facepe`, `editais_cnpq`,
`editais_finep` e `editais_capes` e grava o campo `interesse` no documento do edital —
o mesmo campo que a pipeline usa no envio de lembretes com `--only-interest`.

## Stack

- Next.js 14 (App Router) + React 18 + TypeScript
- Driver oficial `mongodb` (usado apenas no servidor)
- Sem dependências de UI externas (CSS próprio, ícones SVG inline)

## Como rodar

```powershell
cd front
npm install
npm run dev
```

Acesse http://localhost:3000.

Sem `MONGODB_URI` configurado, o app roda em **modo demonstração (mock)** com dados
ilustrativos — útil para apresentar a tela sem depender do banco. Um selo `DEMO`/`AO VIVO`
no topo indica o modo atual.

### Conectar ao MongoDB real

Copie o exemplo e preencha com as credenciais do mesmo cluster da pipeline:

```powershell
Copy-Item .env.local.example .env.local
```

```env
MONGODB_URI=mongodb+srv://usuario:senha@cluster.mongodb.net/?retryWrites=true
MONGODB_DB=iaupe-analyser
```

Se a conexão falhar, o app registra o erro no console e volta para o mock, sem quebrar a tela.

## Arquitetura (alta coesão, baixo acoplamento)

Camadas em `src/`, cada uma dependendo apenas da camada de baixo:

```
domain/        Tipos e regras puras (Edital, urgência de prazo, id).  Sem framework, sem I/O.
lib/           Acesso a dados: cliente Mongo, dados mock e o repositório (fallback).
app/api/       Endpoints HTTP finos, delegando ao repositório.
components/    UI: apresentacionais + o container interativo EditaisView.
app/           layout + page (Server Component que carrega os dados).
```

- **`domain/edital.ts`** — contrato compartilhado (`Edital`), `daysUntil`, `deadlineUrgency`,
  `formatPtBrDate`, `encodeId`/`decodeId`, e os metadados das fontes (`SOURCES`).
- **`lib/editais-repository.ts`** — única porta de acesso a dados. Decide entre Mongo e mock.
- **`app/api/editais`** — `GET` lista agregada das quatro fontes.
- **`app/api/editais/[id]/interest`** — `PATCH` marca/desmarca (`{ "interested": boolean }`).
- **`components/EditaisView.tsx`** — estado da tela, filtro Todos/Meus interesses e
  marcação com atualização otimista (reverte se a API falhar).

O `id` de cada edital é a `url_pdf` codificada em base64url, para servir de parâmetro de rota.

## Como funciona (passo a passo)

### 1. Carregamento da página (servidor)

`app/page.tsx` é um **Server Component** com `export const dynamic = "force-dynamic"`
(renderiza a cada requisição, sem cache). Ele carrega os dados no servidor e entrega ao
container interativo:

```
page.tsx (servidor)
  → listEditais()                     // repositório decide a fonte dos dados
  → <EditaisView initialEditais live> // live = isMongoConfigured()
```

O booleano `live` controla o selo `DEMO` / `AO VIVO` no topo.

### 2. Fonte dos dados: mock ou Mongo

Toda leitura passa por `lib/editais-repository.ts`, a **única porta de dados**:

- **Sem `MONGODB_URI`** → devolve o mock de `lib/mock-data.ts` (modo `DEMO`).
- **Com `MONGODB_URI`** → conecta no Mongo, varre as collections
  `editais_facepe/cnpq/finep/capes`, filtra `status=ok`, mapeia cada documento para o
  tipo `Edital` e ordena pelo prazo mais próximo.
- **Se a conexão falhar** → registra o erro no console e cai no mock. A tela nunca quebra.

### 3. Estado e renderização (navegador)

`components/EditaisView.tsx` é um **Client Component** que mantém a lista em `useState`.
Dele derivam, via `useMemo`:

- `interestList` — editais marcados como de interesse;
- `urgentInterest` — marcados com prazo em ≤ 7 dias (alimenta o KPI vermelho);
- `visible` — todos ou apenas os marcados, conforme o filtro **Todos / Meus interesses**.

Cada `EditalCard` calcula a urgência do prazo com as regras puras do domínio
(`daysUntil` + `deadlineUrgency`): **≤ 7 dias** = urgente (vermelho), **≤ 20** = próximo
(âmbar), acima disso = calmo (verde).

### 4. Marcar interesse (atualização otimista)

Ao clicar na estrela de um card:

```
onToggle(edital)
  → atualiza o estado na hora (otimista) + exibe toast
  → PATCH /api/editais/:id/interest  { "interested": true | false }
  → se a API falhar: reverte o estado + toast de erro
```

A interface responde instantaneamente e só desfaz a mudança se o backend recusar.

### 5. Camada de API

As rotas em `app/api/` são finas — apenas delegam ao repositório:

- `GET /api/editais` → `listEditais()`
- `PATCH /api/editais/:id/interest` → `setInterest(id, interested)` (404 se não achar)

O `:id` é a `url_pdf` em base64url (`encodeId` / `decodeId`). O `PATCH` decodifica de
volta para a `url_pdf`, procura o documento nas collections e grava o campo `interesse`.

### 6. Integração com a pipeline Python

Os dois módulos **nunca se chamam diretamente**. O único elo é o schema do MongoDB: o
campo `interesse` que este front grava é o mesmo que a pipeline lê ao enviar os lembretes
de prazo com a flag `--only-interest`.

### 7. Tema claro/escuro

`ThemeToggle` carimba `data-theme="light" | "dark"` no elemento raiz, que sobrepõe a
media query `prefers-color-scheme` nos dois sentidos. As cores são todas variáveis CSS
(tokens) definidas em `app/globals.css`.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/editais` | Lista agregada de editais (`status=ok`) das quatro fontes |
| PATCH | `/api/editais/:id/interest` | Marca/desmarca interesse. Body: `{ "interested": true }` |

## Scripts

```powershell
npm run dev     # desenvolvimento (http://localhost:3000)
npm run build   # build de producao (inclui checagem de tipos)
npm run start   # sobe o build de producao
```

## Status

Protótipo funcional: build e tipos verificados; GET/PATCH e a tela validados de ponta a
ponta em modo mock. A integração com o Mongo usa o mesmo schema da pipeline; falta apenas
apontar `MONGODB_URI` para o cluster com credenciais válidas.
