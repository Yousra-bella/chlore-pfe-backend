from django.contrib import admin
from django.urls import path, include, reverse_lazy # Regroupement des imports
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from chlore_api.views_password_reset import CustomPasswordResetView
from django.views.generic import TemplateView
from django.contrib.auth import views as auth_views

urlpatterns = [
    # ─── LA PIÈCE MANQUANTE ICI ───
    # Si Django redirige vers le chemin vide '', on intercepte et on affiche directement l'écran de succès
    path('', TemplateView.as_view(template_name='registration/password_reset_complete.html'), name='home_success'),

    path('admin/',                  admin.site.urls),
    path('api/token/',              TokenObtainPairView.as_view()),   # ← login JWT
    path('api/token/refresh/',      TokenRefreshView.as_view()),      # ← refresh token
    path('api/auth/',               include('chlore_api.urls')),
    path('api/recipients/',         include('recipients.urls')),
    
    # 1. Formulaire — admin entre son email
    path(
        'password-reset/',
        CustomPasswordResetView.as_view(
            template_name='registration/password_reset_form.html',
            html_email_template_name='registration/password_reset_email.html',
            subject_template_name='registration/password_reset_subject.txt',
            success_url=reverse_lazy('password_reset_done'),
        ),
        name='password_reset',
    ),
    
    # 2. Confirmation — email envoyé
    path(
        'password-reset/done/',
        auth_views.PasswordResetDoneView.as_view(
            template_name='registration/password_reset_done.html',
        ),
        name='password_reset_done',
    ),
    
    # 3. Lien cliqué — nouveau mot de passe
    path(
        'password-reset/confirm/<uidb64>/<token>/',
        auth_views.PasswordResetConfirmView.as_view(
            template_name='registration/password_reset_confirm.html',
            success_url=reverse_lazy('password_reset_complete'),
        ),
        name='password_reset_confirm',
    ),
    
    # 4. Succès final
    path(
        'password-reset/complete/',
        auth_views.PasswordResetCompleteView.as_view(
            template_name='registration/password_reset_complete.html',
        ),
        name='password_reset_complete',
    ),
]