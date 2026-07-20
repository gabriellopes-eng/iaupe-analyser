import { NextRequest, NextResponse } from "next/server";

import { isValidEmail } from "@/domain/edital";
import { setEditalInterest } from "@/lib/editais-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// PATCH /api/editais/:id/interest -> marca ou desmarca interesse de UM edital
// especifico para o e-mail informado (sem autenticacao, so o endereco digitado).
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const body = (await request.json().catch(() => ({}))) as {
    email?: string;
    interested?: boolean;
  };

  const email = (body.email || "").trim();
  if (!isValidEmail(email)) {
    return NextResponse.json({ ok: false, error: "E-mail inválido" }, { status: 400 });
  }

  const interested = Boolean(body.interested);
  const ok = await setEditalInterest(params.id, email, interested);
  if (!ok) {
    return NextResponse.json(
      { ok: false, error: "Edital não encontrado" },
      { status: 404 },
    );
  }

  return NextResponse.json({ ok: true, interested });
}
