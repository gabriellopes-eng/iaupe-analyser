import EditaisView from "@/components/EditaisView";
import { listEditais } from "@/lib/editais-repository";

// Server Component: carrega a vitrine de editais no servidor. O e-mail do
// usuario so existe no navegador (localStorage, sem login) - por isso o
// carregamento inicial vem sempre com `interested: false`, e o client
// component re-consulta com o e-mail assim que le o localStorage.
export const dynamic = "force-dynamic";

export default async function Page() {
  const { editais, live } = await listEditais(null);
  return <EditaisView initialEditais={editais} live={live} />;
}
