from django.urls import path
from . import views

urlpatterns = [
    path('profil/',              views.ProfilView.as_view()),
    path('centres/',             views.CentreListCreateView.as_view()),
    path('centres/<int:pk>/',    views.CentreDetailView.as_view()),
    path('users/',               views.UserListCreateView.as_view()),
    path('users/<int:pk>/',      views.UserDetailView.as_view()),
]