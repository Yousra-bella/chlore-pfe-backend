from django.urls import path
from . import views

urlpatterns = [
    path('',                               views.RecipientListCreateView.as_view()),
    path('<int:pk>/',                     views.RecipientDetailView.as_view()),
    path('by-qr/<str:qr_code>/',          views.RecipientParQRView.as_view()),
    path('<int:pk>/changer-etat/',        views.ChangerEtatView.as_view()),
    path('<int:pk>/historique/',          views.HistoriqueMouvementsView.as_view()),
    path('mouvements/',                   views.MouvementListView.as_view()),
    path('dashboard/',                    views.DashboardView.as_view()),
    path('alertes/',                      views.AlertesView.as_view()),
    path('export-pdf/',                   views.ExportPDFView.as_view()),
    path('export-excel/', views.ExportExcelView.as_view()),
    path('config-periodicite/',           views.ConfigPeriodiciteView.as_view()),
    path('config-periodicite/<int:pk>/',  views.ConfigPeriodiciteDetailView.as_view()),
    path('supervision/',                  views.SupervisionMouvementsView.as_view()),
    path('mouvements/<int:mouvement_id>/anomalies/',        views.AnomalieListView.as_view()),
    path('mouvements/<int:mouvement_id>/anomalies/creer/',  views.AnomalieCreateView.as_view()),
]