import { Db, MongoClient } from "mongodb";

// Cliente MongoDB compartilhado (singleton) reaproveitado entre requisicoes.
// O front conversa com o MESMO banco da pipeline Python: esse e o unico ponto
// de acoplamento entre os dois modulos (contrato via schema das collections).

let clientPromise: Promise<MongoClient> | null = null;

export function isMongoConfigured(): boolean {
  return Boolean((process.env.MONGODB_URI || "").trim());
}

function getClient(): Promise<MongoClient> {
  if (!isMongoConfigured()) {
    throw new Error("MONGODB_URI nao configurado");
  }
  if (!clientPromise) {
    const client = new MongoClient(process.env.MONGODB_URI as string, {
      serverSelectionTimeoutMS: 8000,
    });
    // se a conexao falhar, limpa o cache para que a proxima chamada tente de
    // novo em vez de reusar para sempre a mesma promise rejeitada (ex.: falha
    // transitoria do cluster, e nao um problema permanente de configuracao).
    clientPromise = client.connect().catch((err) => {
      clientPromise = null;
      throw err;
    });
  }
  return clientPromise;
}

export async function getDb(): Promise<Db> {
  const client = await getClient();
  const dbName = (process.env.MONGODB_DB || "iaupe-analyser").trim();
  return client.db(dbName);
}
