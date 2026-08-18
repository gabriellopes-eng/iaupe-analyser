// Camada de dominio para as preferencias de notificacao do docente.
// Mesma ideia de domain/edital.ts: tipos e catalogos fixos, sem dependencia
// de framework/banco.

// Catalogo identico ao usado pelo Gemini para classificar editais
// (pipeline/pdf_pipeline/analyzer.py::AREAS_INTERESSE). Nao ha arquivo
// compartilhado entre o back Python e o front TS neste repo - cada lado ja
// duplica seu proprio catalogo (ver SOURCES em domain/edital.ts vs os
// scrapers em Python), entao seguimos a mesma convencao aqui.
export const AREAS_INTERESSE_OPTIONS: string[] = [
  "Projetos de Pesquisa, Desenvolvimento e Inovação (PD&I)",
  "Extensão Tecnológica (prestação de serviços, assistência tecnológica)",
  "Empreendedorismo (apoio a startups, spin-offs)",
  "Incubação de Empresas",
  "Aceleração de Negócios",
  "Serviços Tecnológicos",
  "Propriedade Intelectual (patentes, licenciamento, transferência de tecnologia)",
  "Captação de Recursos para PD&I/Inovação",
];

// Catalogo identico ao usado pelo Gemini para classificar editais
// (pipeline/pdf_pipeline/analyzer.py::SEGMENTOS). Deliberadamente NAO e o
// catalogo de ~19 valores da planilha legada que populou a base inicial -
// usar o mesmo catalogo dos editais garante que o match (docente x edital)
// da futura notificacao funcione por intersecao direta de conjuntos.
export const SEGMENTOS_OPTIONS: string[] = [
  "Saúde",
  "Educação",
  "Indústria",
  "Comércio",
  "Serviços",
  "Agropecuária",
  "Tecnologia da informação(TI)",
  "Construção civil",
  "Transporte e Logística",
  "Administração pública",
];

export interface DocentePreferences {
  email: string;
  areasInteresse: string[];
  segmentos: string[];
}

// Filtra uma lista qualquer, mantendo so os valores que existem no catalogo
// informado - usado tanto no client (evita marcar opcao invalida) quanto na
// API (defesa em profundidade, nao confia so na validacao do client).
export function filterKnownOptions(values: string[], catalog: string[]): string[] {
  const known = new Set(catalog);
  const seen = new Set<string>();
  return (values || []).filter((v) => known.has(v) && !seen.has(v) && seen.add(v));
}
