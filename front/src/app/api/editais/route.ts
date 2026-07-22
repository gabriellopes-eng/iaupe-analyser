import { NextRequest, NextResponse } from "next/server";

import { listEditais } from "@/lib/editais-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET /api/editais?email=... -> lista agregada de editais das quatro fontes.
// O campo `interested` de cada edital reflete so o e-mail informado (sem login).
export async function GET(request: NextRequest) {
  const email = request.nextUrl.searchParams.get("email");
  const editais = await listEditais(email);
  return NextResponse.json({ editais });
}
