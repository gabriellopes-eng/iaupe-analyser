# IAUPE Analyzer — Front (Next.js)

Frontend da funcionalidade **"editais de interesse"**: o pesquisador digita só o
próprio e-mail (sem cadastro, sem senha) e marca os editais específicos que quer
acompanhar. Os lembretes de prazo (D-30, D-15, D-7) chegam individualmente para cada
e-mail, só dos editais que aquela pessoa marcou — nunca dos que outra pessoa marcou.

Este módulo é independente da pipeline Python. O **único ponto de integração** é o
MongoDB compartilhado: o front lê as collections `editais_facepe`, `editais_cnpq`,
`editais_finep` e `editais_capes` para exibir os editais, e grava o e-mail da pessoa
no campo `interessados` do edital específico marcado — o mesmo campo que a pipeline
lê para saber quem notificar quando o prazo se aproxima.

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
domain/        Tipos e regras puras (Edital, validação de e-mail, urgência de prazo, id).
lib/           Acesso a dados: cliente Mongo, dados mock e o repositório (fallback).
app/api/       Endpoints HTTP finos, delegando ao repositório.
components/    UI: apresentacionais + o container interativo EditaisView.
app/           layout + page (Server Component que carrega os dados).
```

- **`domain/edital.ts`** — contrato compartilhado (`Edital`, com o campo `interested`
  relativo a um e-mail específico), `isValidEmail`, `normalizeEmail`, `daysUntil`,
  `deadlineUrgency`, `formatPtBrDate`, `encodeId`/`decodeId`, e os metadados das
  fontes (`SOURCES`, usado só para exibição, não para seleção).
- **`lib/editais-repository.ts`** — única porta de acesso a dados. Decide entre Mongo e mock.
- **`app/api/editais`** — `GET` lista agregada das quatro fontes; aceita `?email=` para
  calcular `interested` por edital.
- **`app/api/editais/[id]/interest`** — `PATCH` marca/desmarca um edital específico
  para um e-mail (`{ "email": "...", "interested": boolean }`).
- **`components/EditaisView.tsx`** — estado da tela, identificação por e-mail, filtro
  Todos/Meus interesses e a marcação por edital com atualização otimista.
- **`components/EmailGate.tsx`** — captura o e-mail (sem autenticação) e guarda no
  navegador (`localStorage`) para as próximas visitas.

O `id` de cada edital é a `url_pdf` codificada em base64url, para servir de parâmetro de rota.

## Como funciona (passo a passo)

### 1. Carregamento da página (servidor)

`app/page.tsx` é um **Server Component** com `export const dynamic = "force-dynamic"`
(renderiza a cada requisição, sem cache). O servidor não tem acesso ao `localStorage`
do navegador, então a primeira carga sempre vem sem e-mail (`interested: false` em
tudo); o client component re-consulta com o e-mail assim que o lê do navegador:

```
page.tsx (servidor)
  → listEditais(null)                     // repositório decide a fonte dos dados
  → <EditaisView initialEditais live>     // live = isMongoConfigured()
```

O booleano `live` controla o selo `DEMO` / `AO VIVO` no topo.

### 2. Fonte dos dados: mock ou Mongo

Toda leitura passa por `lib/editais-repository.ts`, a **única porta de dados**:

- **Sem `MONGODB_URI`** → devolve o mock de `lib/mock-data.ts` (modo `DEMO`), calculando
  `interested` a partir do e-mail informado.
- **Com `MONGODB_URI`** → conecta no Mongo, varre as collections
  `editais_facepe/cnpq/finep/capes`, filtra `status=ok`, mapeia cada documento para o
  tipo `Edital` e calcula `interested` conferindo se o e-mail está no array
  `interessados` daquele documento — **sem nunca devolver a lista inteira para o
  navegador** (privacidade: uma pessoa não pode ver quem mais acompanha o mesmo edital).
- **Se a conexão falhar** → registra o erro no console e cai no mock. A tela nunca quebra.

### 3. Identificação por e-mail (sem autenticação)

`components/EmailGate.tsx` pede só o e-mail — sem senha, sem verificação. Ao confirmar:

```
handleSetEmail(email)
  → localStorage.setItem("iaupe:email", email)
  → refetch em /api/editais?email=... (recalcula interested para esse e-mail)
```

Nas próximas visitas (mesmo navegador), `EditaisView` lê o e-mail salvo automaticamente
via `useEffect` e já busca o estado correto — não precisa digitar de novo. Um botão
"trocar e-mail" limpa o `localStorage` e zera os `interested` localmente.

### 4. Estado e renderização (navegador)

`components/EditaisView.tsx` é um **Client Component** que mantém a lista de editais e
o e-mail atual em `useState`. Deles derivam, via `useMemo`:

- `interestList` — editais marcados como de interesse pelo e-mail atual;
- `urgentInterest` — dentre os marcados, quantos têm prazo em ≤ 7 dias (KPI vermelho);
- `visible` — todos ou apenas os marcados, conforme o filtro **Todos / Meus interesses**.

Cada `EditalCard` calcula a urgência do prazo com as regras puras do domínio
(`daysUntil` + `deadlineUrgency`): **≤ 7 dias** = urgente (vermelho), **≤ 20** = próximo
(âmbar), acima disso = calmo (verde).

### 5. Marcar interesse num edital (atualização otimista)

Ao clicar na estrela de um card (exige e-mail já identificado):

```
toggle(edital)
  → atualiza o estado na hora (otimista) + exibe toast
  → PATCH /api/editais/:id/interest  { "email": "...", "interested": true | false }
  → se a API falhar: reverte o estado + toast de erro
```

Sem e-mail identificado, o clique só mostra um aviso pedindo para digitar o e-mail —
não marca nada.

### 6. Camada de API

As rotas em `app/api/` são finas — apenas delegam ao repositório:

- `GET /api/editais?email=...` → `listEditais(email)`
- `PATCH /api/editais/:id/interest` → `setEditalInterest(id, email, interested)`
  (400 se o e-mail for inválido, 404 se o edital não existir)

### 7. Integração com a pipeline Python

Os dois módulos **nunca se chamam diretamente**. O único elo é o schema do MongoDB: o
campo `interessados` (lista de e-mails) que este front grava em cada documento de
edital é o mesmo que a pipeline lê antes de enviar os lembretes de prazo — e manda um
e-mail individual para cada endereço da lista, nunca em cópia/Cc entre si.

### 8. Tema claro/escuro

Removido — o app sempre abre no tema claro (sem toggle).

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| GET | `/api/editais?email=...` | Lista agregada de editais (`status=ok`) das quatro fontes, com `interested` calculado por e-mail |
| PATCH | `/api/editais/:id/interest` | Marca/desmarca um edital para um e-mail. Body: `{ "email": "...", "interested": true }` |

## Scripts

```powershell
npm run dev     # desenvolvimento (http://localhost:3000)
npm run build   # build de producao (inclui checagem de tipos)
npm run start   # sobe o build de producao
```

## Status

Protótipo funcional: seleção por **edital específico**, identificação só por e-mail
(sem autenticação). Testado de ponta a ponta contra o Mongo real: dois e-mails
diferentes marcam editais diferentes de forma independente, sem um ver o interesse do
outro. Roda em modo mock quando `MONGODB_URI` não está configurado.
