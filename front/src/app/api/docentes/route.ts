import { NextRequest, NextResponse } from "next/server";

import { isValidEmail } from "@/domain/edital";
import { AREAS_INTERESSE_OPTIONS, SEGMENTOS_OPTIONS } from "@/domain/docente";
import { getDocentePreferences, saveDocentePreferences } from "@/lib/docentes-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET /api/docentes?email=... -> preferencias do docente (areas/segmentos).
// "Nao encontrado" nao e erro: devolve arrays vazios, ja que so significa que
// o docente ainda nao marcou nada (ex.: primeiro acesso pela tela nova).
export async function GET(request: NextRequest) {
  const email = (request.nextUrl.searchParams.get("email") || "").trim();
  if (!isValidEmail(email)) {
    return NextResponse.json({ ok: false, error: "E-mail inválido" }, { status: 400 });
  }

  const prefs = await getDocentePreferences(email);
  return NextResponse.json({
    ok: true,
    areasInteresse: prefs?.areasInteresse || [],
    segmentos: prefs?.segmentos || [],
  });
}

// PUT /api/docentes -> grava (upsert) as preferencias do docente informado
// (sem autenticacao, so o e-mail digitado - mesmo padrao de /api/editais/:id/interest).
export async function PUT(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as {
    email?: string;
    areasInteresse?: unknown;
    segmentos?: unknown;
  };

  const email = (body.email || "").trim();
  if (!isValidEmail(email)) {
    return NextResponse.json({ ok: false, error: "E-mail inválido" }, { status: 400 });
  }

  const areasInteresse = Array.isArray(body.areasInteresse)
    ? body.areasInteresse.filter((v): v is string => typeof v === "string")
    : [];
  const segmentos = Array.isArray(body.segmentos)
    ? body.segmentos.filter((v): v is string => typeof v === "string")
    : [];

  // rejeita explicitamente valores fora do catalogo fixo, em vez de so
  // filtrar em silencio - a validacao no client (checkboxes) nao deve ser a
  // unica linha de defesa.
  const areaInvalida = areasInteresse.some((v) => !AREAS_INTERESSE_OPTIONS.includes(v));
  const segmentoInvalido = segmentos.some((v) => !SEGMENTOS_OPTIONS.includes(v));
  if (areaInvalida || segmentoInvalido) {
    return NextResponse.json(
      { ok: false, error: "Área ou segmento fora do catálogo permitido" },
      { status: 400 },
    );
  }

  const ok = await saveDocentePreferences(email, areasInteresse, segmentos);
  if (!ok) {
    return NextResponse.json(
      { ok: false, error: "Não foi possível salvar. Tente novamente." },
      { status: 502 },
    );
  }

  return NextResponse.json({ ok: true });
}
