import EditaisView from "@/components/EditaisView";
import { getPreferences, listEditais } from "@/lib/editais-repository";
import { isMongoConfigured } from "@/lib/mongo";

// Server Component: carrega editais e preferencias de fonte no servidor.
export const dynamic = "force-dynamic";

export default async function Page() {
  const [editais, preferences] = await Promise.all([listEditais(), getPreferences()]);
  return (
    <EditaisView
      initialEditais={editais}
      initialPreferences={preferences}
      live={isMongoConfigured()}
    />
  );
}
