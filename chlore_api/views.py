from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .models import Centre, User
from .serializers import CentreSerializer, UserSerializer
from .permissions import EstAdmin, EstChefCentre
from rest_framework_simplejwt.tokens import RefreshToken


class ProfilView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({
            'id':         request.user.id,
            'username':   request.user.username,
            'email':      request.user.email,
            'role':       request.user.role,
            'centre':     request.user.centre_id,
            'centre_nom': request.user.centre.nom if request.user.centre else '',
            'first_name': request.user.first_name,
            'last_name':  request.user.last_name,
        })

class CentreListCreateView(generics.ListCreateAPIView):
    queryset           = Centre.objects.all()
    serializer_class   = CentreSerializer
    permission_classes = [EstChefCentre]   # ← était EstChefOuPlus


class CentreDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = Centre.objects.all()
    serializer_class   = CentreSerializer
    permission_classes = [EstAdmin]
class UserListCreateView(generics.ListCreateAPIView):
    queryset           = User.objects.all().order_by('username')
    serializer_class   = UserSerializer
    permission_classes = [EstAdmin]

class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = User.objects.all()
    serializer_class   = UserSerializer
    permission_classes = [EstAdmin]
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            RefreshToken(request.data['refresh']).blacklist()
        except Exception:
            pass
        return Response(status=205)