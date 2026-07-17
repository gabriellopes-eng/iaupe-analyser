import { NextRequest, NextResponse } from "next/server";

import { SourceKey, SOURCES } from "@/domain/edital";
import { getPreferences, setSourceFollowed } from "@/lib/editais-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET /api/preferencias -> fontes atualmente seguidas pelo usuario.
export async function GET() {
  const preferences = await getPreferences();
  return NextResponse.json({ preferences });
}

// PATCH /api/preferencias -> liga ou desliga uma fonte (FACEPE/CNPq/FINEP/CAPES).
export async function PATCH(request: NextRequest) {
  const body = (await request.json().catch(() => ({}))) as {
    source?: string;
    followed?: boolean;
  };

  const source = (body.source || "") as SourceKey;
  if (!Object.prototype.hasOwnProperty.call(SOURCES, source)) {
    return NextResponse.json({ ok: false, error: "Fonte inválida" }, { status: 400 });
  }

  const preferences = await setSourceFollowed(source, Boolean(body.followed));
  return NextResponse.json({ ok: true, preferences });
}
