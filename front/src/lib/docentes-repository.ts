import { normalizeEmail } from "@/domain/edital";
import {
  AREAS_INTERESSE_OPTIONS,
  DocentePreferences,
  SEGMENTOS_OPTIONS,
  filterKnownOptions,
} from "@/domain/docente";
import { getDb, isMongoConfigured } from "@/lib/mongo";

// Repositorio de preferencias de docente: unica porta de acesso a dados (I/O)
// para a UI/API. Mesma collection Mongo que o script de import da task 1 usa
// (sandbox/import_docentes_interesse.py) - front e pipeline Python sao dois
// clientes independentes da mesma base, conectados so pelo schema (ver
// front/src/lib/mongo.ts).
const DOCENTES_COLLECTION = "docentes";

// Diferencia quem se cadastrou/editou pela tela de quem veio da carga
// inicial da planilha ("planilha_docentes_2026", ver sandbox/import_docentes_interesse.py).
const ORIGEM_AUTO_CADASTRO = "auto_cadastro";

interface DocenteDoc {
  email: string;
  areas_interesse?: string[];
  segmentos?: string[];
  created_at?: Date;
  updated_at?: Date;
  origem?: string;
}

// Busca as preferencias de UM docente pelo e-mail. Devolve arrays vazios
// (nao null) quando o docente existe mas ainda nao marcou nada, e null so
// quando o e-mail nunca apareceu na base - "nao encontrado" nao e erro aqui,
// e simplesmente "sem preferencias ainda".
export async function getDocentePreferences(email: string): Promise<DocentePreferences | null> {
  if (!isMongoConfigured()) return null;

  const normalized = normalizeEmail(email);

  try {
    const db = await getDb();
    const doc = await db.collection<DocenteDoc>(DOCENTES_COLLECTION).findOne({ email: normalized });
    if (!doc) return null;
    // filtra contra o catalogo atual antes de devolver: docentes importados da
    // planilha legada (task 1) podem ter valores de um catalogo antigo/diferente
    // (ex.: "Tecnologia da informação( TI)" com espaço, vs "Tecnologia da
    // informação(TI)" do catalogo atual). Sem filtrar aqui, esse valor legado
    // ficaria "escondido" no estado do formulario (nao aparece marcado em
    // nenhum chip) e travaria QUALQUER salvamento futuro na validacao do PUT,
    // mesmo o docente so tendo escolhido opcoes validas pela tela.
    return {
      email: normalized,
      areasInteresse: filterKnownOptions(doc.areas_interesse || [], AREAS_INTERESSE_OPTIONS),
      segmentos: filterKnownOptions(doc.segmentos || [], SEGMENTOS_OPTIONS),
    };
  } catch (err) {
    console.error("[docentes-repository] Falha ao buscar preferencias:", err);
    return null;
  }
}

// Grava (upsert) as preferencias de um docente. Mesmo shape que o script
// Python da task 1 ja usa: $set nos campos mutaveis + $setOnInsert nos
// imutaveis (email/origem/created_at ficam fixos apos o primeiro save).
export async function saveDocentePreferences(
  email: string,
  areasInteresse: string[],
  segmentos: string[],
): Promise<boolean> {
  if (!isMongoConfigured()) return false;

  const normalized = normalizeEmail(email);
  if (!normalized) return false;

  // defesa em profundidade: o client ja restringe via checkboxes aos
  // catalogos fixos, mas a API nao confia so nisso.
  const cleanAreas = filterKnownOptions(areasInteresse, AREAS_INTERESSE_OPTIONS);
  const cleanSegmentos = filterKnownOptions(segmentos, SEGMENTOS_OPTIONS);

  try {
    const db = await getDb();
    const now = new Date();
    await db.collection<DocenteDoc>(DOCENTES_COLLECTION).updateOne(
      { email: normalized },
      {
        $set: {
          areas_interesse: cleanAreas,
          segmentos: cleanSegmentos,
          updated_at: now,
        },
        $setOnInsert: {
          email: normalized,
          origem: ORIGEM_AUTO_CADASTRO,
          created_at: now,
        },
      },
      { upsert: true },
    );
    return true;
  } catch (err) {
    console.error("[docentes-repository] Falha ao gravar preferencias:", err);
    return false;
  }
}
