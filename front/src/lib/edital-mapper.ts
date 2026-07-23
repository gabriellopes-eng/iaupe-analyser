import { Edital, SOURCES, encodeId, isSourceKey, normalizeEmail } from "@/domain/edital";

// Traducao entre o documento bruto salvo no Mongo (EditalDoc) e o tipo de
// dominio Edital usado pela UI/API. Camada pura, sem I/O.

export interface EditalDoc {
  url_pdf?: string;
  status?: string;
  fonte?: string;
  data_limit_submissao?: Date | string | null;
  interessados?: string[];
  updated_at?: Date;
  resultado?: {
    titulo?: string;
    titulo_edital?: string;
    descricao?: string;
    areas_interesse?: unknown;
  };
}

function shortRef(source: string, urlPdf: string): string {
  let hash = 0;
  for (let i = 0; i < urlPdf.length; i++) {
    hash = (hash * 31 + urlPdf.charCodeAt(i)) & 0xffff;
  }
  const code = String(hash % 1000).padStart(3, "0");
  return `${source.toUpperCase()}-${code}`;
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
export function mapDoc(doc: EditalDoc, email: string | null): Edital | null {
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
