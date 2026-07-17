# IAUPE Analyzer — Front (Next.js)

Frontend da funcionalidade **"fontes de interesse"**: o pesquisador liga as fontes
(FACEPE, CNPq, FINEP, CAPES) que acompanha e passa a receber lembretes de prazo
(D-30, D-15, D-7) de **todo edital dessas fontes**, sem precisar marcar edital por edital.

Este módulo é independente da pipeline Python. O **único ponto de integração** é o
MongoDB compartilhado: o front lê as collections `editais_facepe`, `editais_cnpq`,
`editais_finep` e `editais_capes` para exibir os editais, e grava a lista de fontes
seguidas na collection `preferencias_usuario` — a mesma que a pipeline lê antes de
enviar os lembretes de cada fonte.

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
domain/        Tipos e regras puras (Edital, preferencias de fonte, urgência de prazo, id).
lib/           Acesso a dados: cliente Mongo, dados mock e o repositório (fallback).
app/api/       Endpoints HTTP finos, delegando ao repositório.
components/    UI: apresentacionais + o container interativo EditaisView.
app/           layout + page (Server Component que carrega os dados).
```

- **`domain/edital.ts`** — contrato compartilhado (`Edital`), `SourcePreferences`,
  `daysUntil`, `deadlineUrgency`, `formatPtBrDate`, `encodeId`, e os metadados das
  fontes (`SOURCES`).
- **`lib/editais-repository.ts`** — única porta de acesso a dados. Decide entre Mongo e mock.
- **`app/api/editais`** — `GET` lista agregada das quatro fontes.
- **`app/api/preferencias`** — `GET` lê as fontes seguidas, `PATCH` liga/desliga uma fonte.
- **`components/EditaisView.tsx`** — estado da tela, filtro Todos/Minhas fontes e o
  toggle de fonte com atualização otimista (reverte se a API falhar).
- **`components/FontesToggle.tsx`** — painel com as 4 chaves liga/desliga, uma por fonte.

O `id` de cada edital é a `url_pdf` codificada em base64url, para servir de parâmetro de rota.

## Como funciona (passo a passo)

### 1. Carregamento da página (servidor)

`app/page.tsx` é um **Server Component** com `export const dynamic = "force-dynamic"`
(renderiza a cada requisição, sem cache). Ele carrega os dados no servidor e entrega ao
container interativo:

```
page.tsx (servidor)
  → listEditais() + getPreferences()               // repositório decide a fonte dos dados
  → <EditaisView initialEditais initialPreferences live> // live = isMongoConfigured()
```

O booleano `live` controla o selo `DEMO` / `AO VIVO` no topo.

### 2. Fonte dos dados: mock ou Mongo

Toda leitura passa por `lib/editais-repository.ts`, a **única porta de dados**:

- **Sem `MONGODB_URI`** → devolve o mock de `lib/mock-data.ts` (modo `DEMO`).
- **Com `MONGODB_URI`** → conecta no Mongo, varre as collections
  `editais_facepe/cnpq/finep/capes`, filtra `status=ok`, mapeia cada documento para o
  tipo `Edital` e ordena pelo prazo mais próximo. As preferências vêm de um único
  documento na collection `preferencias_usuario`.
- **Se a conexão falhar** → registra o erro no console e cai no mock. A tela nunca quebra.

### 3. Estado e renderização (navegador)

`components/EditaisView.tsx` é um **Client Component** que mantém a lista de editais e as
preferências de fonte em `useState`. Delas derivam, via `useMemo`:

- `followedList` — editais cuja fonte está ligada;
- `followedSourcesCount` — quantas das 4 fontes estão ligadas (alimenta o KPI dourado);
- `urgentFollowed` — dentre os seguidos, quantos têm prazo em ≤ 7 dias (KPI vermelho);
- `visible` — todos ou apenas os das fontes seguidas, conforme o filtro **Todos / Minhas fontes**.

Cada `EditalCard` é somente apresentação: mostra se a fonte dele está ligada (borda/selo
dourado) e calcula a urgência do prazo com as regras puras do domínio (`daysUntil` +
`deadlineUrgency`): **≤ 7 dias** = urgente (vermelho), **≤ 20** = próximo (âmbar), acima
disso = calmo (verde).

### 4. Ligar/desligar uma fonte (atualização otimista)

Ao clicar numa chave do `FontesToggle`:

```
toggleSource(source)
  → atualiza o estado na hora (otimista) + exibe toast
  → PATCH /api/preferencias  { "source": "capes", "followed": true | false }
  → se a API falhar: reverte o estado + toast de erro
```

A interface responde instantaneamente e só desfaz a mudança se o backend recusar. Ligar
uma fonte afeta **todos** os editais dela de uma vez — não há mais marcação por edital
individual.

### 5. Camada de API

As rotas em `app/api/` são finas — apenas delegam ao repositório:

- `GET /api/editais` → `listEditais()`
- `GET /api/preferencias` → `getPreferences()`
- `PATCH /api/preferencias` → `setSourceFollowed(source, followed)` (400 se a fonte for inválida)

### 6. Integração com a pipeline Python

Os dois módulos **nunca se chamam diretamente**. O único elo é o schema do MongoDB: o
documento `{ _id: "fontes_seguidas", fontes_seguidas: [...] }` que este front grava na
collection `preferencias_usuario` é o mesmo que a pipeline lê (`get_followed_sources()`)
antes de enviar os lembretes de cada fonte — se a fonte não estiver na lista, a pipeline
pula o envio dela inteiramente.

### 7. Tema claro/escuro

`ThemeToggle` carimba `data-theme="light" | "dark"` no elemento raiz, que sobrepõe a
media query `prefers-color-scheme` nos dois sentidos. As cores são todas variáveis CSS
(tokens) definidas em `app/globals.css`.

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/editais` | Lista agregada de editais (`status=ok`) das quatro fontes |
| GET | `/api/preferencias` | Fontes atualmente seguidas |
| PATCH | `/api/preferencias` | Liga/desliga uma fonte. Body: `{ "source": "capes", "followed": true }` |

## Scripts

```powershell
npm run dev     # desenvolvimento (http://localhost:3000)
npm run build   # build de producao (inclui checagem de tipos)
npm run start   # sobe o build de producao
```

## Status

Protótipo funcional: seleção por **fonte** (não mais por edital individual). Roda em modo
mock por padrão; a integração com o Mongo usa o mesmo schema da pipeline — falta apenas
apontar `MONGODB_URI` para o cluster com credenciais válidas.
