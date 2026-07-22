import {
  Edital,
  SOURCES,
  daysUntil,
  decodeId,
  encodeId,
  isSourceKey,
  normalizeEmail,
} from "@/domain/edital";
import { getDb, isMongoConfigured } from "@/lib/mongo";
import { getMockEditais, setMockInterest, shortRef } from "@/lib/mock-data";

// Repositorio de editais: unica porta de acesso a dados para a UI/API.
// Quando o MongoDB nao esta configurado (ou falha), cai para dados mock,
// mantendo o front funcional para demonstracao.

// Todos os editais (de qualquer fonte) vivem numa unica collection Mongo -
// mesma collection que a pipeline Python le/escreve (ver pipeline/db/mongo.py).
const EDITAIS_COLLECTION = "editais";

interface EditalDoc {
  url_pdf?: string;
  status?: string;
  fonte?: string;
  data_limit_submissao?: Date | string | null;
  interessados?: string[];
  resultado?: {
    titulo?: string;
    titulo_edital?: string;
    descricao?: string;
    areas_interesse?: unknown;
  };
}

function pickTitulo(doc: EditalDoc): string {
  const r = doc.resultado || {};
  const titulo = (r.titulo || r.titulo_edital || r.descricao || "").toString().trim();
  if (!titulo) return "Edital sem título identificado";
  return titulo.length > 140 ? `${titulo.slice(0, 137).trimEnd()}...` : titulo;
}

function pickAreas(doc: EditalDoc): string[] {
  const raw = doc.resultado?.areas_interesse;
  if (!Array.isArray(raw)) return [];
  return raw
    .map((v) => String(v).trim())
    .filter(Boolean)
    .slice(0, 2);
}

function toIso(value: Date | string | null | undefined): string | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return Number.isNaN(d.getTime()) ? null : d.toISOString();
}

// So calcula se O E-MAIL ATUAL esta na lista - nunca devolve a lista inteira
// pro cliente, pra nao vazar o e-mail de uma pessoa pra outra.
function mapDoc(doc: EditalDoc, email: string | null): Edital | null {
  const urlPdf = (doc.url_pdf || "").trim();
  const fonte = doc.fonte || "";
  if (!urlPdf || !isSourceKey(fonte)) return null;

  const meta = SOURCES[fonte];
  const interessados = (doc.interessados || []).map((e) => e.toLowerCase());
  return {
    id: encodeId(urlPdf),
    urlPdf,
    source: fonte,
    sourceLabel: meta.label,
    orgao: meta.orgao,
    color: meta.color,
    ref: shortRef(fonte, urlPdf),
    titulo: pickTitulo(doc),
    deadline: toIso(doc.data_limit_submissao),
    areas: pickAreas(doc),
    interested: email ? interessados.includes(normalizeEmail(email)) : false,
  };
}

// Edital sem prazo (deadline null) fica; com prazo no passado sai da vitrine.
function excludeExpired(editais: Edital[]): Edital[] {
  return editais.filter((e) => {
    const days = daysUntil(e.deadline);
    return days === null || days >= 0;
  });
}

// Lista todos os editais, ordenados por prazo mais proximo primeiro (sem prazo vai pro fim).
export async function listEditais(email: string | null): Promise<Edital[]> {
  if (!isMongoConfigured()) {
    return excludeExpired(getMockEditais(email));
  }

  try {
    const db = await getDb();
    const docs = await db
      .collection<EditalDoc>(EDITAIS_COLLECTION)
      .find({ status: "ok" })
      .project({ url_pdf: 1, fonte: 1, data_limit_submissao: 1, resultado: 1, interessados: 1 })
      .toArray();

    const all = docs
      .map((doc) => mapDoc(doc as EditalDoc, email))
      .filter((e): e is Edital => e !== null);

    // ordena por prazo mais proximo primeiro; sem prazo vai para o fim
    all.sort((a, b) => {
      if (a.deadline === b.deadline) return 0;
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return a.deadline < b.deadline ? -1 : 1;
    });
    return excludeExpired(all);
  } catch (err) {
    console.error("[editais-repository] Falha ao consultar Mongo, usando mock:", err);
    return excludeExpired(getMockEditais(email));
  }
}

// Marca ou desmarca interesse de UM edital especifico para o e-mail informado.
export async function setEditalInterest(
  id: string,
  email: string,
  interested: boolean,
): Promise<boolean> {
  if (!isMongoConfigured()) {
    return setMockInterest(id, email, interested);
  }

  let urlPdf: string;
  try {
    urlPdf = decodeId(id);
  } catch {
    return false;
  }

  const normalized = normalizeEmail(email);

  try {
    const db = await getDb();
    const result = await db.collection<EditalDoc>(EDITAIS_COLLECTION).updateOne(
      { url_pdf: urlPdf },
      {
        [interested ? "$addToSet" : "$pull"]: { interessados: normalized },
        $set: { updated_at: new Date() },
      } as never,
    );
    return result.matchedCount > 0;
  } catch (err) {
    console.error("[editais-repository] Falha ao gravar interesse:", err);
    return false;
  }
}
