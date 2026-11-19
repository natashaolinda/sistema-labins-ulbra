import json
import logging
from urllib.request import Request, urlopen

from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

logger = logging.getLogger(__name__)


class AppsScriptEmailBackend(BaseEmailBackend):
    """
    Envia as notificações do Labins pelo Google Apps Script,
    usando HTTPS em vez de SMTP.
    """

    def send_messages(self, email_messages):
        enviados = 0

        for mensagem in email_messages:
            destinatarios = mensagem.recipients()

            if not destinatarios:
                continue

            try:
                # Prepara os dados para o Google Apps Script.
                dados = {
                    "token": settings.LABINS_API_KEY,
                    "to": destinatarios,
                    "subject": mensagem.subject,
                    "body": mensagem.body,
                }

                requisicao = Request(
                    settings.LABINS_EMAIL_API_URL,
                    data=json.dumps(dados).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )

                # Envia a solicitação por HTTPS.
                with urlopen(requisicao, timeout=15) as resposta:
                    resultado = json.load(resposta)

                if resultado.get("ok") is not True:
                    raise RuntimeError(
                        resultado.get("mensagem", "Falha no envio.")
                    )

                enviados += 1

            except Exception:
                logger.exception(
                    "Erro ao enviar notificação pelo Google Apps Script."
                )

                if not self.fail_silently:
                    raise

        return enviados
