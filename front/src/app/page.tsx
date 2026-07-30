import EditaisView from "@/components/EditaisView";
import { paginateEditais } from "@/domain/edital";
import { listEditais } from "@/lib/editais-repository";

const PAGE_SIZE = 20;

// Server Component: carrega a primeira pagina da vitrine de editais no
// servidor (20 em 20 - o restante vem via scroll infinito, ver
// useEditaisState.ts). O e-mail do usuario so existe no navegador
// (localStorage, sem login) - por isso o carregamento inicial vem sempre com
// `interested: false` (e `interestList` vazia), e o client component
// re-consulta com o e-mail assim que le o localStorage.
export const dynamic = "force-dynamic";

export default async function Page() {
  const { editais: all, live } = await listEditais(null);
  const { items, nextCursor, hasMore } = paginateEditais(all, null, PAGE_SIZE);
  return (
    <EditaisView
      initialEditais={items}
      initialNextCursor={nextCursor}
      initialHasMore={hasMore}
      initialTotalCount={all.length}
      live={live}
    />
  );
}
