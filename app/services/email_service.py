import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# Configurações de email - devem ser definidas como variáveis de ambiente
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USER = os.getenv("EMAIL_USER", "seu-email@gmail.com")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "sua-senha-app")
EMAIL_FROM = os.getenv("EMAIL_FROM", "AgentCicle <noreply@agentcicle.com>")

def enviar_email(destinatario: str, codigo: str, tipo: str = "verificacao"):
    """
    Envia um email com código de verificação ou redefinição de senha
    
    Args:
        destinatario: Email do destinatário
        codigo: Código de verificação/redefinição
        tipo: Tipo de email ("verificacao" ou "redefinicao")
    """
    try:
        # Configurar mensagem
        msg = MIMEMultipart()
        msg['From'] = EMAIL_FROM
        msg['To'] = destinatario
        
        # Definir assunto e conteúdo com base no tipo
        if tipo == "verificacao":
            msg['Subject'] = "Confirme seu cadastro no AgentCicle"
            corpo_email = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #8a2be2;">Bem-vinda ao AgentCicle!</h2>
                    <p>Estamos felizes por você se juntar a nós. Para confirmar seu email, use o código abaixo:</p>
                    <div style="background-color: #f7f7f7; padding: 15px; border-radius: 4px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold;">
                        {codigo}
                    </div>
                    <p>Este código expira em 24 horas.</p>
                    <p>Se você não solicitou este código, por favor ignore este email.</p>
                    <p>Atenciosamente,<br>Equipe AgentCicle</p>
                </div>
            </body>
            </html>
            """
        else:  # redefinicao
            msg['Subject'] = "Redefinição de senha - AgentCicle"
            corpo_email = f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 5px;">
                    <h2 style="color: #8a2be2;">Redefinição de Senha</h2>
                    <p>Recebemos uma solicitação para redefinir sua senha. Use o código abaixo para prosseguir:</p>
                    <div style="background-color: #f7f7f7; padding: 15px; border-radius: 4px; text-align: center; font-size: 24px; letter-spacing: 5px; font-weight: bold;">
                        {codigo}
                    </div>
                    <p>Este código expira em 30 minutos.</p>
                    <p>Se você não solicitou esta redefinição, por favor entre em contato conosco imediatamente.</p>
                    <p>Atenciosamente,<br>Equipe AgentCicle</p>
                </div>
            </body>
            </html>
            """
        
        # Anexar corpo do email
        msg.attach(MIMEText(corpo_email, 'html'))
        
        # Conectar ao servidor SMTP e enviar
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as servidor:
            servidor.starttls()  # Ativar conexão segura
            servidor.login(EMAIL_USER, EMAIL_PASSWORD)
            servidor.send_message(msg)
            
        # Log de envio bem-sucedido
        print(f"Email enviado para {destinatario} com sucesso em {datetime.now()}")
        return True
        
    except Exception as e:
        # Log de erro
        print(f"Erro ao enviar email para {destinatario}: {str(e)}")
        # Para desenvolvimento/testes, ainda imprime o código
        print(f"\n📧 [FALLBACK] Código para {destinatario}: {codigo}\n")
        return False
        
def enviar_email_verificacao(email: str, codigo: str):
    """Função específica para envio de email de verificação"""
    return enviar_email(email, codigo, "verificacao")
    
def enviar_email_redefinicao(email: str, codigo: str):
    """Função específica para envio de email de redefinição de senha"""
    return enviar_email(email, codigo, "redefinicao")
