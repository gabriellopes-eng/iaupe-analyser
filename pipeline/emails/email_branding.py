from __future__ import annotations

# Linha de tabela (<tr>) com uma faixa branca no topo do email, contendo os logos
# institucionais lado a lado: UPE a esquerda, IIT a direita.
# Os src="cid:logo_upe"/"cid:logo_iit" apontam para as imagens que o SmtpEmailService
# anexa inline na mensagem (ver INLINE_LOGOS em smtp_email_service.py) - por isso o
# logo so aparece quando esta string e usada dentro do HTML enviado por aquele servico.
# border-radius nos dois cantos superiores porque esta e a primeira celula visual do email.
#
# Compartilhado pelos dois templates de notificacao (edital salvo e alerta de prazo)
# para manter o mesmo cabecalho e evitar duplicar o HTML dos logos em cada um.
LOGO_HEADER_HTML = (
    "<tr><td style='background:#ffffff; padding:18px 36px; border-radius:8px 8px 0 0;'>"
    "<table width='100%'><tr>"
    "<td align='left' style='width:50%;'><img src='cid:logo_upe' alt='UPE' style='height:42px; display:block;'></td>"
    "<td align='right' style='width:50%;'><img src='cid:logo_iit' alt='IIT' style='height:42px; display:block;'></td>"
    "</tr></table>"
    "</td></tr>"
)
