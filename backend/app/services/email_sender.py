import logging
import json
from urllib import request, error
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def enviar_email_conta_criada(
    destinatario: str,
    nome_pessoa: str,
    email_login: str,
    senha_temporaria: str,
) -> bool:
    if not settings.BREVO_API_KEY:
        logger.error("BREVO_API_KEY não configurada.")
        return False

    try:
        payload = json.dumps({
            "sender": {
                "name": settings.BREVO_FROM_NAME or "ASAP",
                "email": settings.BREVO_FROM_EMAIL,
            },
            "to": [{"email": destinatario, "name": nome_pessoa}],
            "subject": "Sua conta no sistema da ASAP foi criada!",
            "htmlContent": f"""
            <p>Olá, {nome_pessoa},</p>
            <p>Sua conta no sistema de gestão da ASAP foi criada com sucesso.</p>
            <ul>
                <li><strong>E-mail:</strong> {email_login}</li>
                <li><strong>Senha Temporária:</strong> {senha_temporaria}</li>
            </ul>
            <p>Recomendamos que você altere sua senha após o primeiro login.</p>
            <p>Acesse: <a href="{settings.FRONTEND_URL}">{settings.FRONTEND_URL}</a></p>
            <p>Atenciosamente,<br>Equipe ASAP</p>
            """,
        }).encode("utf-8")

        req = request.Request(
            "https://api.brevo.com/v3/smtp/email",
            data=payload,
            headers={
                "Content-Type": "application/json",
                "api-key": settings.BREVO_API_KEY,
            },
            method="POST",
        )

        with request.urlopen(req, timeout=15) as resp:
            logger.info(f"E-mail enviado para {destinatario}: {resp.status}")
            return True

    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {destinatario}: {e}")
        return False