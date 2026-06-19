import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def enviar_email_conta_criada(
    destinatario: str,
    nome_pessoa: str,
    email_login: str,
    senha_temporaria: str,
):
    """Envia um e-mail de boas-vindas com credenciais temporárias via Brevo SMTP."""
    print(f"[DEBUG] Tentando enviar email para {destinatario}")
    print(f"[DEBUG] BREVO_SMTP_KEY configurada: {bool(settings.BREVO_SMTP_KEY)}")

    if not settings.BREVO_SMTP_KEY:
        logger.error("BREVO_SMTP_KEY não configurada. O e-mail não será enviado.")
        return

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = "Sua conta no sistema da ASAP foi criada!"
        msg["From"] = f"{settings.BREVO_FROM_NAME or 'ASAP'} <{settings.BREVO_FROM_EMAIL}>"
        msg["To"] = destinatario

        html = f"""
        <p>Olá, {nome_pessoa},</p>
        <p>Sua conta no sistema de gestão da ASAP foi criada com sucesso.</p>
        <p>Use as seguintes credenciais para fazer login:</p>
        <ul>
            <li><strong>E-mail:</strong> {email_login}</li>
            <li><strong>Senha Temporária:</strong> {senha_temporaria}</li>
        </ul>
        <p>Recomendamos que você altere sua senha após o primeiro login.</p>
        <p>Acesse o sistema em: <a href="{settings.FRONTEND_URL}">{settings.FRONTEND_URL}</a></p>
        <br>
        <p>Atenciosamente,</p>
        <p>Equipe ASAP</p>
        """

        msg.attach(MIMEText(html, "html"))

        with smtplib.SMTP("smtp-relay.brevo.com", 587) as server:
            server.starttls()
            server.login(settings.BREVO_SMTP_LOGIN, settings.BREVO_SMTP_KEY)
            server.sendmail(settings.BREVO_FROM_EMAIL, destinatario, msg.as_string())

        logger.info(f"E-mail enviado para {destinatario}")

    except Exception as e:
        logger.error(f"Falha ao enviar e-mail para {destinatario}: {e}")