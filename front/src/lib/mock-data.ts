import { Edital, SourceKey, SOURCES, encodeId } from "@/domain/edital";

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
  interesse: boolean;
}

const SEEDS: Seed[] = [
  {
    source: "finep",
    urlPdf: "https://www.finep.gov.br/editais/tecnova-2026-2027.pdf",
    titulo: "Carta Convite MCTI/FINEP — Programa Tecnova 2026/2027",
    deadlineDays: 29,
    areas: ["Inovação", "Micro e pequenas empresas"],
    interesse: true,
  },
  {
    source: "facepe",
    urlPdf: "https://www.facepe.br/editais/bfp-2026.pdf",
    titulo: "BFP — Bolsa de Fixação de Pesquisador 2026",
    deadlineDays: 4,
    areas: ["Formação de RH", "Todas as áreas"],
    interesse: false,
  },
  {
    source: "cnpq",
    urlPdf: "https://www.gov.br/cnpq/chamada-12-2026-pq.pdf",
    titulo: "Chamada CNPq/MCTI nº 12/2026 — Bolsas de Produtividade em Pesquisa (PQ)",
    deadlineDays: 15,
    areas: ["Pesquisadores PQ", "Multidisciplinar"],
    interesse: true,
  },
  {
    source: "facepe",
    urlPdf: "https://www.facepe.br/editais/apq-2026.pdf",
    titulo: "APQ — Auxílio à Pesquisa e Programas Estratégicos 2026",
    deadlineDays: 7,
    areas: ["Projetos de pesquisa", "Doutores"],
    interesse: false,
  },
  {
    source: "capes",
    urlPdf: "https://www.gov.br/capes/print-2026.pdf",
    titulo: "Programa CAPES-PrInt — Internacionalização 2026",
    deadlineDays: 83,
    areas: ["Internacionalização", "Pós-graduação"],
    interesse: false,
  },
  {
    source: "finep",
    urlPdf: "https://www.finep.gov.br/editais/subvencao-2026.pdf",
    titulo: "Subvenção Econômica à Inovação — Chamada Pública 2026",
    deadlineDays: 42,
    areas: ["Subvenção", "Empresas"],
    interesse: false,
  },
];

// Estado em memoria para o mock persistir a marcacao durante a sessao do servidor.
const mockState: Edital[] = SEEDS.map((seed) => {
  const meta = SOURCES[seed.source];
  return {
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
    interesse: seed.interesse,
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

export function getMockEditais(): Edital[] {
  // devolve copias para evitar mutacao acidental fora do setMockInterest
  return mockState.map((e) => ({ ...e }));
}

export function setMockInterest(id: string, interested: boolean): boolean {
  const found = mockState.find((e) => e.id === id);
  if (!found) return false;
  found.interesse = interested;
  return true;
}
