import { Edital, daysUntil, decodeId, normalizeEmail } from "@/domain/edital";
import { getDb, isMongoConfigured } from "@/lib/mongo";
import { EditalDoc, mapDoc } from "@/lib/edital-mapper";

// Repositorio de editais: unica porta de acesso a dados (I/O) para a UI/API.
// A traducao doc->Edital fica em edital-mapper.ts; aqui so entra/sai do Mongo.
// Sem dado fake: se o MongoDB nao estiver configurado ou a consulta falhar,
// devolve lista vazia com `live: false` - a UI mostra "fora do ar", nao dados
// ilustrativos.

// Todos os editais (de qualquer fonte) vivem numa unica collection Mongo -
// mesma collection que a pipeline Python le/escreve (ver pipeline/db/connection.py).
const EDITAIS_COLLECTION = "editais";

export interface EditaisResult {
  editais: Edital[];
  live: boolean;
}

// Edital sem prazo (deadline null) fica; com prazo no passado sai da vitrine.
function excludeExpired(editais: Edital[]): Edital[] {
  return editais.filter((e) => {
    const days = daysUntil(e.deadline);
    return days === null || days >= 0;
  });
}

// Lista todos os editais, ordenados por prazo mais proximo primeiro (sem prazo vai pro fim).
export async function listEditais(email: string | null): Promise<EditaisResult> {
  if (!isMongoConfigured()) {
    return { editais: [], live: false };
  }

  try {
    const db = await getDb();
    const docs = await db
      .collection<EditalDoc>(EDITAIS_COLLECTION)
      .find({ status: "ok" })
      .project({ url_pdf: 1, fonte: 1, data_limit_submissao: 1, resultado: 1, interessados: 1 })
      .toArray();

    const all = docs
      .map((doc) => mapDoc(doc as EditalDoc, email))
      .filter((e): e is Edital => e !== null);

    // Ordena por prazo mais proximo primeiro; sem prazo vai para o fim.
    // Desempate por `id` quando o prazo e igual (inclusive null == null):
    // sem isso a ordem de itens empatados dependeria da ordem de retorno do
    // Mongo, que nao e garantida - e a paginacao por cursor precisa de uma
    // ordenacao 100% deterministica pra nao pular nem repetir itens entre paginas.
    all.sort((a, b) => {
      if (a.deadline !== b.deadline) {
        if (!a.deadline) return 1;
        if (!b.deadline) return -1;
        return a.deadline < b.deadline ? -1 : 1;
      }
      return a.id < b.id ? -1 : a.id > b.id ? 1 : 0;
    });
    return { editais: excludeExpired(all), live: true };
  } catch (err) {
    console.error("[editais-repository] Falha ao consultar Mongo:", err);
    return { editais: [], live: false };
  }
}

// Marca ou desmarca interesse de UM edital especifico para o e-mail informado.
export async function setEditalInterest(
  id: string,
  email: string,
  interested: boolean,
): Promise<boolean> {
  if (!isMongoConfigured()) {
    return false;
  }

  let urlPdf: string;
  try {
    urlPdf = decodeId(id);
  } catch {
    return false;
  }

  const normalized = normalizeEmail(email);

  try {
    const db = await getDb();
    const collection = db.collection<EditalDoc>(EDITAIS_COLLECTION);
    const update = interested
      ? { $addToSet: { interessados: normalized }, $set: { updated_at: new Date() } }
      : { $pull: { interessados: normalized }, $set: { updated_at: new Date() } };
    const result = await collection.updateOne({ url_pdf: urlPdf }, update);
    return result.matchedCount > 0;
  } catch (err) {
    console.error("[editais-repository] Falha ao gravar interesse:", err);
    return false;
  }
}
