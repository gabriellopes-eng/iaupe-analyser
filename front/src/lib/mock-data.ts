import { Edital, SourceKey, SOURCES, encodeId, normalizeEmail } from "@/domain/edital";

// Dados de demonstracao usados quando o MongoDB nao esta configurado.
// Prazos sao relativos ao "hoje" para manter os niveis de urgencia sempre coerentes.
function inDays(n: number): string {
  const d = new Date();
  d.setUTCHours(0, 0, 0, 0);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString();
}

interface Seed {
  source: SourceKey;
  urlPdf: string;
  titulo: string;
  deadlineDays: number;
  areas: string[];
  interessados?: string[];
}

const SEEDS: Seed[] = [
  {
    source: "finep",
    urlPdf: "https://www.finep.gov.br/editais/tecnova-2026-2027.pdf",
    titulo: "Carta Convite MCTI/FINEP - Programa Tecnova 2026/2027",
    deadlineDays: 29,
    areas: ["Inovação", "Micro e pequenas empresas"],
    interessados: ["demo@upe.br"],
  },
  {
    source: "facepe",
    urlPdf: "https://www.facepe.br/editais/bfp-2026.pdf",
    titulo: "BFP - Bolsa de Fixação de Pesquisador 2026",
    deadlineDays: 4,
    areas: ["Formação de RH", "Todas as áreas"],
  },
  {
    source: "cnpq",
    urlPdf: "https://www.gov.br/cnpq/chamada-12-2026-pq.pdf",
    titulo: "Chamada CNPq/MCTI nº 12/2026 - Bolsas de Produtividade em Pesquisa (PQ)",
    deadlineDays: 15,
    areas: ["Pesquisadores PQ", "Multidisciplinar"],
  },
  {
    source: "facepe",
    urlPdf: "https://www.facepe.br/editais/apq-2026.pdf",
    titulo: "APQ - Auxílio à Pesquisa e Programas Estratégicos 2026",
    deadlineDays: 7,
    areas: ["Projetos de pesquisa", "Doutores"],
  },
  {
    source: "capes",
    urlPdf: "https://www.gov.br/capes/print-2026.pdf",
    titulo: "Programa CAPES-PrInt - Internacionalização 2026",
    deadlineDays: 83,
    areas: ["Internacionalização", "Pós-graduação"],
  },
  {
    source: "finep",
    urlPdf: "https://www.finep.gov.br/editais/subvencao-2026.pdf",
    titulo: "Subvenção Econômica à Inovação - Chamada Pública 2026",
    deadlineDays: 42,
    areas: ["Subvenção", "Empresas"],
  },
];

interface MockRecord {
  edital: Omit<Edital, "interested">;
  interessados: Set<string>;
}

// Estado em memoria para o mock persistir durante a sessao do servidor.
// Cada edital guarda sua propria lista de e-mails interessados, igual ao
// schema real (`interessados` no documento do edital, sem multi-usuario
// autenticado - so o e-mail digitado identifica a pessoa).
const mockState: MockRecord[] = SEEDS.map((seed) => {
  const meta = SOURCES[seed.source];
  return {
    edital: {
      id: encodeId(seed.urlPdf),
      urlPdf: seed.urlPdf,
      source: seed.source,
      sourceLabel: meta.label,
      orgao: meta.orgao,
      color: meta.color,
      ref: shortRef(seed.source, seed.urlPdf),
      titulo: seed.titulo,
      deadline: inDays(seed.deadlineDays),
      areas: seed.areas,
    },
    interessados: new Set((seed.interessados || []).map(normalizeEmail)), // adicionar nos editais e ja posso tirar o mock
  };
});

export function shortRef(source: SourceKey, urlPdf: string): string {
  let hash = 0;
  for (let i = 0; i < urlPdf.length; i++) {
    hash = (hash * 31 + urlPdf.charCodeAt(i)) & 0xffff;
  }
  const code = String(hash % 1000).padStart(3, "0");
  return `${SOURCES[source].label.toUpperCase()}-${code}`;
}

export function getMockEditais(email: string | null): Edital[] {
  const normalized = email ? normalizeEmail(email) : null;
  return mockState.map((record) => ({
    ...record.edital,
    interested: normalized ? record.interessados.has(normalized) : false,
  }));
}

export function setMockInterest(id: string, email: string, interested: boolean): boolean {
  const record = mockState.find((r) => r.edital.id === id);
  if (!record) return false;
  const normalized = normalizeEmail(email);
  if (interested) {
    record.interessados.add(normalized);
  } else {
    record.interessados.delete(normalized);
  }
  return true;
}
