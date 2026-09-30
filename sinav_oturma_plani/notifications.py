"""E-posta gönderimi. Gmail, okul mail sunucusu gibi herhangi bir SMTP
sunucusuyla çalışır.

Ortam değişkenleri:
    SMTP_HOST      - örn. smtp.gmail.com (zorunlu)
    SMTP_PORT      - örn. 587 (varsayılan: 587, STARTTLS)
    SMTP_USER      - SMTP kullanıcı adı (zorunlu)
    SMTP_PASSWORD  - SMTP şifresi/uygulama şifresi (zorunlu)
    SMTP_FROM      - Gönderen adresi (varsayılan: SMTP_USER)
"""
import os
import smtplib
from email.message import EmailMessage


def smtp_configured():
    """SMTP göndermek için gereken asgari ayarlar mevcut mu?"""
    return bool(os.environ.get('SMTP_HOST') and os.environ.get('SMTP_USER')
                and os.environ.get('SMTP_PASSWORD'))


def send_email(to_addr, subject, body):
    """Tek bir e-posta gönderir.

    Ayarlar eksikse ya da gönderim başarısız olursa hata fırlatır."""
    if not smtp_configured():
        raise RuntimeError(
            "SMTP ayarları yapılandırılmamış (SMTP_HOST/SMTP_USER/SMTP_PASSWORD "
            "ortam değişkenlerini ayarlayın)."
        )

    host = os.environ['SMTP_HOST']
    port = int(os.environ.get('SMTP_PORT', '587'))
    user = os.environ['SMTP_USER']
    password = os.environ['SMTP_PASSWORD']
    from_addr = os.environ.get('SMTP_FROM', user)

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = from_addr
    msg['To'] = to_addr
    msg.set_content(body)

    if port == 465:
        with smtplib.SMTP_SSL(host, port, timeout=15) as server:
            server.login(user, password)
            server.send_message(msg)
    else:
        with smtplib.SMTP(host, port, timeout=15) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
