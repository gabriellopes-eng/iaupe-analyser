import { NextRequest, NextResponse } from "next/server";

import { paginateEditais } from "@/domain/edital";
import { listEditais } from "@/lib/editais-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

const DEFAULT_PAGE_SIZE = 20;

// GET /api/editais?email=...&cursor=...&limit=20 -> uma pagina de editais
// (20 em 20, cursor = id do ultimo item da pagina anterior), mais dados que
// nao sao paginados: `interestList` (completa - normalmente pequena, e o
// "Meus interesses" do usuario) e `totalCount` (total real, ja que `editais`
// aqui e so a pagina atual). O campo `interested` de cada edital reflete so
// o e-mail informado (sem login). `live` indica se a consulta ao Mongo
// realmente funcionou (sem dado fake de fallback).
export async function GET(request: NextRequest) {
  const email = request.nextUrl.searchParams.get("email");
  const cursor = request.nextUrl.searchParams.get("cursor");
  const limitParam = Number(request.nextUrl.searchParams.get("limit"));
  const limit = Number.isFinite(limitParam) && limitParam > 0 ? limitParam : DEFAULT_PAGE_SIZE;

  const { editais: all, live } = await listEditais(email);
  const { items, nextCursor, hasMore } = paginateEditais(all, cursor, limit);
  const interestList = all.filter((e) => e.interested);

  return NextResponse.json({
    editais: items,
    nextCursor,
    hasMore,
    totalCount: all.length,
    interestList,
    live,
  });
}
