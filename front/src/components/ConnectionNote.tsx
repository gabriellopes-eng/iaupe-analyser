import { InfoIcon } from "@/components/icons";

interface ConnectionNoteProps {
  live: boolean;
}

// Rodape explicando o estado da conexao com o MongoDB.
export default function ConnectionNote({ live }: ConnectionNoteProps) {
  return (
    <footer className="note">
      <InfoIcon />
      <span>
        {live ? (
          <>
            <b>Conectado ao MongoDB.</b> A marcação grava seu e-mail na lista{" "}
            <code>interessados</code> do edital; os lembretes de prazo avisam cada pessoa
            individualmente, sem expor o e-mail de ninguém.
          </>
        ) : (
          <>
            <b>Sem conexão com o banco.</b> Verifique se <code>MONGODB_URI</code> está
            configurado e se o cluster está acessível. A tela volta ao normal assim que a
            conexão for restabelecida.
          </>
        )}
      </span>
    </footer>
  );
}
