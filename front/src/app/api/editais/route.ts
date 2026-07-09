import { NextResponse } from "next/server";

import { listEditais } from "@/lib/editais-repository";

export const runtime = "nodejs";
export const dynamic = "force-dynamic";

// GET /api/editais -> lista agregada de editais das quatro fontes.
export async function GET() {
  const editais = await listEditais();
  return NextResponse.json({ editais });
}
