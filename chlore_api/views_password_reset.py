from django.contrib.auth.views import PasswordResetView
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


class CustomPasswordResetView(PasswordResetView):
    """
    Vue personnalisée qui envoie l'email en HTML correctement
    au lieu du texte brut par défaut de Django.
    """
    html_email_template_name = 'registration/password_reset_email.html'

    def send_mail(
        self, subject_template_name, email_template_name,
        context, from_email, to_email, html_email_template_name=None
    ):
        # ── Génère le sujet ──
        subject = render_to_string(subject_template_name, context)
        subject = ''.join(subject.splitlines())  # supprime les retours à la ligne

        # ── Génère le contenu HTML ──
        html_content = render_to_string(
            html_email_template_name or self.html_email_template_name,
            context
        )

        # ── Crée un texte brut simple en fallback ──
        text_content = (
            f"Bonjour,\n\n"
            f"Cliquez sur ce lien pour réinitialiser votre mot de passe :\n"
            f"{context['protocol']}://{context['domain']}"
            f"/password-reset/confirm/{context['uid']}/{context['token']}/\n\n"
            f"Si vous n'avez pas demandé cette réinitialisation, ignorez cet email."
        )

        # ── Envoie l'email en multipart (HTML + texte) ──
        email_message = EmailMultiAlternatives(
            subject, text_content, from_email, [to_email]
        )
        email_message.attach_alternative(html_content, 'text/html')
        email_message.send()