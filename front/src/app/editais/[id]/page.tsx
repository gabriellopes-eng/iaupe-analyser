import { notFound } from "next/navigation";

import EditalDetailView from "@/components/EditalDetailView";
import { getEditalDetail } from "@/lib/editais-repository";

export const dynamic = "force-dynamic";

interface EditalDetailPageProps {
  params: { id: string };
}

// Pagina de detalhamento: mesmo conteudo que o email de notificacao mostra
// (ver pipeline/emails/saved_record_email_notifier.py), mas como pagina web
// normal - sem literalmente reusar o HTML do email, que depende de recursos
// so validos dentro de um cliente de email (cid: de imagem, tabela de
// layout fixo). O e-mail so tem acesso a `null` (sem login), igual a carga
// inicial da listagem - por isso `interested` aqui sempre vem false.
export default async function EditalDetailPage({ params }: EditalDetailPageProps) {
  const edital = await getEditalDetail(params.id, null);
  if (!edital) notFound();

  return <EditalDetailView edital={edital} />;
}
