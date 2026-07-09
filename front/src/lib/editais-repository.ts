import {
  Edital,
  SOURCES,
  SourceKey,
  decodeId,
  encodeId,
} from "@/domain/edital";
import { getDb, isMongoConfigured } from "@/lib/mongo";
import { getMockEditais, setMockInterest, shortRef } from "@/lib/mock-data";

// Repositorio de editais: unica porta de acesso a dados para a UI/API.
// Quando o MongoDB nao esta configurado (ou falha), cai para dados mock,
// mantendo o front funcional para demonstracao.

interface EditalDoc {
  url_pdf?: string;
  status?: string;
  interesse?: boolean;
  data_limit_submissao?: Date | string | null;
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

function mapDoc(doc: EditalDoc, source: SourceKey): Edital | null {
  const urlPdf = (doc.url_pdf || "").trim();
  if (!urlPdf) return null;
  const meta = SOURCES[source];
  return {
    id: encodeId(urlPdf),
    urlPdf,
    source,
    sourceLabel: meta.label,
    orgao: meta.orgao,
    color: meta.color,
    ref: shortRef(source, urlPdf),
    titulo: pickTitulo(doc),
    deadline: toIso(doc.data_limit_submissao),
    areas: pickAreas(doc),
    interesse: doc.interesse === true,
  };
}

export async function listEditais(): Promise<Edital[]> {
  if (!isMongoConfigured()) {
    return getMockEditais();
  }

  try {
    const db = await getDb();
    const all: Edital[] = [];

    for (const meta of Object.values(SOURCES)) {
      const docs = await db
        .collection<EditalDoc>(meta.collection)
        .find({ status: "ok" })
        .project({ url_pdf: 1, interesse: 1, data_limit_submissao: 1, resultado: 1 })
        .toArray();

      for (const doc of docs) {
        const edital = mapDoc(doc as EditalDoc, meta.key);
        if (edital) all.push(edital);
      }
    }

    // ordena por prazo mais proximo primeiro; sem prazo vai para o fim
    all.sort((a, b) => {
      if (a.deadline === b.deadline) return 0;
      if (!a.deadline) return 1;
      if (!b.deadline) return -1;
      return a.deadline < b.deadline ? -1 : 1;
    });
    return all;
  } catch (err) {
    console.error("[editais-repository] Falha ao consultar Mongo, usando mock:", err);
    return getMockEditais();
  }
}

export async function setInterest(id: string, interested: boolean): Promise<boolean> {
  if (!isMongoConfigured()) {
    return setMockInterest(id, interested);
  }

  let urlPdf: string;
  try {
    urlPdf = decodeId(id);
  } catch {
    return false;
  }

  try {
    const db = await getDb();
    for (const meta of Object.values(SOURCES)) {
      const result = await db
        .collection<EditalDoc>(meta.collection)
        .updateOne(
          { url_pdf: urlPdf },
          { $set: { interesse: interested, updated_at: new Date() } },
        );
      if (result.matchedCount > 0) return true;
    }
    return false;
  } catch (err) {
    console.error("[editais-repository] Falha ao marcar interesse:", err);
    return false;
  }
}
