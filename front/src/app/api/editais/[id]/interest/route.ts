import { NextRequest, NextResponse } from "next/server";

import { setInterest } from "@/lib/editais-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// PATCH /api/editais/:id/interest -> marca ou desmarca um edital como de interesse.
export async function PATCH(
  request: NextRequest,
  { params }: { params: { id: string } },
) {
  const body = (await request.json().catch(() => ({}))) as { interested?: boolean };
  const interested = Boolean(body.interested);

  const ok = await setInterest(params.id, interested);
  if (!ok) {
    return NextResponse.json(
      { ok: false, error: "Edital não encontrado" },
      { status: 404 },
    );
  }

  return NextResponse.json({ ok: true, interested });
}
