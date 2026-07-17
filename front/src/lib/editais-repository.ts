import {
  Edital,
  SOURCES,
  SourceKey,
  SourcePreferences,
  ALL_SOURCES_UNFOLLOWED,
  encodeId,
} from "@/domain/edital";
import { getDb, isMongoConfigured } from "@/lib/mongo";
import {
  getMockEditais,
  getMockPreferences,
  setMockSourceFollowed,
  shortRef,
} from "@/lib/mock-data";

// Preferencias de fonte: documento unico (sem multi-usuario ainda) na collection
// `preferencias_usuario`, com o mesmo shape que a pipeline Python le/escreve.
const PREFERENCES_COLLECTION = "preferencias_usuario";
const PREFERENCES_DOC_ID = "fontes_seguidas";

interface PreferencesDoc {
  _id?: string;
  fontes_seguidas?: string[];
}

// Repositorio de editais: unica porta de acesso a dados para a UI/API.
// Quando o MongoDB nao esta configurado (ou falha), cai para dados mock,
// mantendo o front funcional para demonstracao.

interface EditalDoc {
  url_pdf?: string;
  status?: string;
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
        .project({ url_pdf: 1, data_limit_submissao: 1, resultado: 1 })
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

export async function getPreferences(): Promise<SourcePreferences> {
  if (!isMongoConfigured()) {
    return getMockPreferences();
  }

  try {
    const db = await getDb();
    const doc = await db
      .collection<PreferencesDoc>(PREFERENCES_COLLECTION)
      .findOne({ _id: PREFERENCES_DOC_ID } as never);

    const followed = new Set((doc?.fontes_seguidas || []).map((f) => f.toLowerCase()));
    const prefs = { ...ALL_SOURCES_UNFOLLOWED };
    for (const key of Object.keys(prefs) as SourceKey[]) {
      prefs[key] = followed.has(key);
    }
    return prefs;
  } catch (err) {
    console.error("[editais-repository] Falha ao ler preferencias, usando mock:", err);
    return getMockPreferences();
  }
}

export async function setSourceFollowed(
  source: SourceKey,
  followed: boolean,
): Promise<SourcePreferences> {
  if (!isMongoConfigured()) {
    return setMockSourceFollowed(source, followed);
  }

  try {
    const db = await getDb();
    await db.collection<PreferencesDoc>(PREFERENCES_COLLECTION).updateOne(
      { _id: PREFERENCES_DOC_ID } as never,
      {
        [followed ? "$addToSet" : "$pull"]: { fontes_seguidas: source },
      } as never,
      { upsert: true },
    );
    return getPreferences();
  } catch (err) {
    console.error("[editais-repository] Falha ao gravar preferencias:", err);
    return getMockPreferences();
  }
}
