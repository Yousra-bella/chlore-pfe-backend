from rest_framework_simplejwt.authentication import JWTAuthentication


class QueryParamJWTAuthentication(JWTAuthentication):
    """
    Permet l'authentification JWT via ?token= dans l'URL.
    Utilisé uniquement pour le téléchargement PDF via navigateur.
    """
    def authenticate(self, request):
        token = request.query_params.get('token')
        if not token:
            return None
        try:
            validated_token = self.get_validated_token(token)
            return self.get_user(validated_token), validated_token
        except Exception:
            return None