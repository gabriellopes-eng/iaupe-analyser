import EditaisView from "@/components/EditaisView";
import { listEditais } from "@/lib/editais-repository";
import { isMongoConfigured } from "@/lib/mongo";

// Server Component: carrega os editais no servidor e entrega ao container interativo.
export const dynamic = "force-dynamic";

export default async function Page() {
  const editais = await listEditais();
  return <EditaisView initialEditais={editais} live={isMongoConfigured()} />;
}
