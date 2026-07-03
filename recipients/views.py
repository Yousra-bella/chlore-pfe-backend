from rest_framework import generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from datetime import date
from django.db.models import Count
from io import BytesIO
import openpyxl

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from .models import Recipient, Mouvement, ConfigPeriodicite, Anomalie
from .serializers import RecipientSerializer, MouvementSerializer, ConfigPeriodiciteSerializer, AnomalieSerializer
from chlore_api.permissions import EstAdmin, EstChefCentre, EstAgent

TRANSITIONS = {
    'plein':       ['branche', 'entretien', 'epreuve'],
    'branche':     ['vide'],
    'vide':        ['remplissage', 'entretien', 'epreuve'],
    'remplissage': ['plein'],
    'entretien':   ['plein', 'epreuve'],
    'epreuve':     ['plein'],
}


class RecipientListCreateView(generics.ListCreateAPIView):
    serializer_class   = RecipientSerializer
    permission_classes = [EstAgent]

    def get_queryset(self):
        q = Recipient.objects.all()
        p = self.request.query_params
        user = self.request.user

        # Récupère le rôle peu importe où il est stocké
        role = getattr(user, 'role', None) or get_role(user)

        if role in ['agent', 'chef_centre']:
            centre_id = getattr(user, 'centre_id', None)
            if not centre_id:
                # Essaie via le profile
                try:
                    centre_id = user.profile.centre_id
                except Exception:
                    pass
            if centre_id:
                q = q.filter(centre_id=centre_id)

        if p.get('code_qr'): q = q.filter(code_qr=p['code_qr'])
        if p.get('etat'):    q = q.filter(etat=p['etat'])
        if p.get('centre'):  q = q.filter(centre_id=p['centre'])
        return q
        

    def perform_create(self, serializer):
        if self.request.user.role == 'agent':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Un agent ne peut pas créer un récipient.")
        serializer.save()


class RecipientDetailView(generics.RetrieveUpdateAPIView):
    queryset           = Recipient.objects.all()
    serializer_class   = RecipientSerializer
    permission_classes = [EstAgent]

    def perform_update(self, serializer):
        if self.request.user.role == 'consultation':
            from rest_framework.exceptions import PermissionDenied
            raise PermissionDenied("Accès lecture seule.")
        serializer.save()


class RecipientParQRView(APIView):
    permission_classes = [EstAgent]

    def get(self, request, qr_code):
        try:
            r = Recipient.objects.get(code_qr=qr_code)
        except Recipient.DoesNotExist:
            return Response({'erreur': 'Récipient introuvable'}, status=404)
        return Response(RecipientSerializer(r).data)


class ChangerEtatView(APIView):
    permission_classes = [EstAgent]

    def post(self, request, pk):
        if request.user.role == 'consultation':
            return Response({'erreur': 'Accès lecture seule.'}, status=403)

        try:
            r = Recipient.objects.get(pk=pk)
        except Recipient.DoesNotExist:
            return Response({'erreur': 'Récipient introuvable'}, status=404)

        if request.user.role == 'agent' and request.user.centre != r.centre:
            return Response({'erreur': 'Accès refusé — autre centre.'}, status=403)

        n_etat = request.data.get('nouvel_etat', '')
        obs    = request.data.get('observation', '')

        if not obs or len(obs.strip()) < 5:
            return Response({'erreur': 'Observation obligatoire (min. 5 caractères).'}, status=400)

        if n_etat not in TRANSITIONS.get(r.etat, []):
            return Response({
                'erreur':     f"Transition {r.etat} → {n_etat} interdite.",
                'autorisees': TRANSITIONS.get(r.etat, []),
            }, status=400)

        if n_etat == 'branche' and r.epreuve_expiree:
            return Response({
                'erreur':       'BRANCHEMENT INTERDIT : épreuve expirée.',
                'date_epreuve': str(r.date_prochaine_epreuve),
            }, status=403)

        ancien = r.etat
        Mouvement.objects.create(
            recipient=r,
            centre=r.centre,
            agent=request.user,
            ancien_etat=ancien,
            nouvel_etat=n_etat,
            observation=obs.strip(),
        )
        r.etat = n_etat
        r.save()
        return Response({
            'message':   f'État mis à jour → {n_etat}',
            'recipient': RecipientSerializer(r).data,
        })


class MouvementListView(generics.ListAPIView):
    serializer_class   = MouvementSerializer
    permission_classes = [EstAgent]

    def get_queryset(self):
        q = Mouvement.objects.all()
        if self.request.user.role == 'agent' and self.request.user.centre_id:
            q = q.filter(centre_id=self.request.user.centre_id)
        p = self.request.query_params
        if p.get('recipient'): q = q.filter(recipient_id=p['recipient'])
        if p.get('centre'):    q = q.filter(centre_id=p['centre'])
        return q


class DashboardView(APIView):
    permission_classes = [EstAgent]

    def get(self, request):
        tous = Recipient.objects.all()
        if request.user.role in ['agent', 'chef_centre'] and request.user.centre_id:
            tous = tous.filter(centre_id=request.user.centre_id)

        par_etat = {}
        for e, _ in Recipient.ETAT_CHOICES:
            par_etat[e] = tous.filter(etat=e).count()

        expirees  = [r for r in tous if r.epreuve_expiree]
        bientot30 = [r for r in tous if 0 <= r.jours_avant_epreuve <= 30]

        stock_par_centre = (
            tous.values('centre__nom')
                .annotate(total=Count('id'))
                .order_by('-total')
        )

        return Response({
            'total':             tous.count(),
            'par_etat':          par_etat,
            'epreuves_expirees': len(expirees),
            'epreuves_bientot':  len(bientot30),
            'stock_par_centre': [
                {'centre': s['centre__nom'], 'total': s['total']}
                for s in stock_par_centre
            ],
            'alertes': [
                {
                    'id':           r.id,
                    'numero_serie': r.numero_serie,
                    'jours':        r.jours_avant_epreuve,
                    'expire':       r.epreuve_expiree,
                }
                for r in tous
                if r.epreuve_expiree or 0 <= r.jours_avant_epreuve <= 30
            ],
            'derniers_mouvements': MouvementSerializer(
                Mouvement.objects.order_by('-date_heure')[:5],
                many=True
            ).data,
        })


class AlertesView(APIView):
    permission_classes = [EstAgent]

    def get(self, request):
        tous = Recipient.objects.all()
        if request.user.role in ['agent', 'chef_centre'] and request.user.centre_id:
            tous = tous.filter(centre_id=request.user.centre_id)

        alertes = []
        for r in tous:
            if r.epreuve_expiree:
                alertes.append({
                    'recipient': r.numero_serie,
                    'type':      'EXPIREE',
                    'message':   f'Épreuve expirée depuis {abs(r.jours_avant_epreuve)} jours',
                    'centre':    r.centre.nom,
                    'etat':      r.etat,
                })
            elif 0 <= r.jours_avant_epreuve <= 30:
                alertes.append({
                    'recipient': r.numero_serie,
                    'type':      'BIENTOT',
                    'message':   f'Épreuve dans {r.jours_avant_epreuve} jours',
                    'centre':    r.centre.nom,
                    'etat':      r.etat,
                })
        return Response({'alertes': alertes, 'total': len(alertes)})


class ExportPDFView(APIView):
    permission_classes = [EstChefCentre]

    def get(self, request):
        # ── Accepter le token via query param pour ouverture navigateur ──
        token_param = request.query_params.get('token')
        if token_param:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from django.contrib.auth import get_user_model
                User = get_user_model()
                validated = AccessToken(token_param)
                request.user = User.objects.get(id=validated['user_id'])
            except Exception:
                return HttpResponse('Token invalide.', status=401)

        BLEU   = colors.HexColor('#1A3A5C')
        VERT   = colors.HexColor('#1D9E75')
        GRIS   = colors.HexColor('#F5F5F3')
        BORD   = colors.HexColor('#DDDDDD')
        ROUGE  = colors.HexColor('#993C1D')

        def S(name, **kw): return ParagraphStyle(name, **kw)
        s_titre  = S('t',  fontSize=20, textColor=BLEU,         fontName='Helvetica-Bold', alignment=TA_CENTER, spaceAfter=4)
        s_sous   = S('s',  fontSize=11, textColor=colors.grey,  fontName='Helvetica',      alignment=TA_CENTER, spaceAfter=2)
        s_h1     = S('h1', fontSize=13, textColor=BLEU,         fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)
        s_body   = S('b',  fontSize=9,  fontName='Helvetica',   spaceAfter=4, leading=13)
        s_hdr    = S('hd', fontSize=9,  textColor=colors.white, fontName='Helvetica-Bold', alignment=TA_CENTER)
        s_cell   = S('c',  fontSize=9,  fontName='Helvetica',   leading=12)
        s_cell_c = S('cc', fontSize=9,  fontName='Helvetica',   alignment=TA_CENTER, leading=12)

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm,   bottomMargin=2*cm)
        story = []

        tous = Recipient.objects.all()
        if request.user.role == 'chef_centre' and request.user.centre_id:
            tous = tous.filter(centre_id=request.user.centre_id)

        # ── En-tête ──
        story.append(Paragraph('RAPPORT TABLEAU DE BORD', s_titre))
        story.append(Paragraph('Gestion des Tanks a Chlore', s_sous))
        story.append(Paragraph(
            f'Genere le {date.today().strftime("%d/%m/%Y")} — par {request.user.username}',
            s_sous
        ))
        story.append(HRFlowable(width='100%', thickness=1, color=BLEU, spaceAfter=12, spaceBefore=8))

        # ── 1. Résumé global ──
        story.append(Paragraph('1. Resume global', s_h1))
        total   = tous.count()
        expires = sum(1 for r in tous if r.epreuve_expiree)
        bientot = sum(1 for r in tous if 0 <= r.jours_avant_epreuve <= 30)

        t1 = Table([
            [Paragraph('Indicateur', s_hdr),              Paragraph('Valeur', s_hdr)],
            [Paragraph('Total recipients', s_cell),        Paragraph(str(total),   s_cell_c)],
            [Paragraph('Epreuves expirees', s_cell),       Paragraph(str(expires), s_cell_c)],
            [Paragraph('Epreuves < 30 jours', s_cell),     Paragraph(str(bientot), s_cell_c)],
        ], colWidths=[12*cm, 4*cm])
        t1.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), BLEU),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [GRIS, colors.white]),
            ('GRID',          (0,0), (-1,-1), 0.3, BORD),
            ('TOPPADDING',    (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING',   (0,0), (-1,-1), 8), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t1)
        story.append(Spacer(1, 0.4*cm))

        # ── 2. Répartition par état ──
        story.append(Paragraph('2. Repartition par etat', s_h1))
        etats_rows = [[Paragraph('Etat', s_hdr), Paragraph('Nombre', s_hdr)]]
        for etat, label in Recipient.ETAT_CHOICES:
            nb = tous.filter(etat=etat).count()
            if nb > 0:
                etats_rows.append([Paragraph(label, s_cell), Paragraph(str(nb), s_cell_c)])
        t2 = Table(etats_rows, colWidths=[12*cm, 4*cm])
        t2.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), VERT),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [GRIS, colors.white]),
            ('GRID',          (0,0), (-1,-1), 0.3, BORD),
            ('TOPPADDING',    (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING',   (0,0), (-1,-1), 8), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t2)
        story.append(Spacer(1, 0.4*cm))

        # ── 3. Stock par centre ──
        story.append(Paragraph('3. Stock par centre', s_h1))
        stock_centres = tous.values('centre__nom').annotate(total=Count('id')).order_by('-total')
        centres_rows = [[Paragraph('Centre', s_hdr), Paragraph('Total', s_hdr)]]
        for s in stock_centres:
            centres_rows.append([
                Paragraph(s['centre__nom'] or 'Non defini', s_cell),
                Paragraph(str(s['total']), s_cell_c),
            ])
        t3 = Table(centres_rows, colWidths=[12*cm, 4*cm])
        t3.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), BLEU),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [GRIS, colors.white]),
            ('GRID',          (0,0), (-1,-1), 0.3, BORD),
            ('TOPPADDING',    (0,0), (-1,-1), 6), ('BOTTOMPADDING', (0,0), (-1,-1), 6),
            ('LEFTPADDING',   (0,0), (-1,-1), 8), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t3)
        story.append(Spacer(1, 0.4*cm))

        # ── 4. Alertes réglementaires ──
        story.append(Paragraph('4. Alertes reglementaires', s_h1))
        alertes = [r for r in tous if r.epreuve_expiree or 0 <= r.jours_avant_epreuve <= 30]
        if alertes:
            alertes_rows = [[
                Paragraph('N Serie', s_hdr), Paragraph('Centre', s_hdr),
                Paragraph('Etat', s_hdr), Paragraph('Prochaine epreuve', s_hdr),
                Paragraph('Statut', s_hdr),
            ]]
            for r in alertes:
                statut = 'EXPIREE' if r.epreuve_expiree else f'Dans {r.jours_avant_epreuve}j'
                alertes_rows.append([
                    Paragraph(r.numero_serie, s_cell),
                    Paragraph(r.centre.nom, s_cell),
                    Paragraph(r.get_etat_display(), s_cell),
                    Paragraph(str(r.date_prochaine_epreuve), s_cell_c),
                    Paragraph(statut, s_cell_c),
                ])
            t4 = Table(alertes_rows, colWidths=[3.5*cm, 4*cm, 3*cm, 3.5*cm, 2*cm])
            t4.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,0), ROUGE),
                ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.HexColor('#FAECE7'), colors.white]),
                ('GRID',          (0,0), (-1,-1), 0.3, BORD),
                ('TOPPADDING',    (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING',   (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t4)
        else:
            story.append(Paragraph('Aucune alerte reglementaire.', s_body))
        story.append(Spacer(1, 0.4*cm))

        # ── 5. Liste complète des récipients ──
        story.append(Paragraph('5. Liste complete des recipients', s_h1))
        recip_rows = [[
            Paragraph('N Serie', s_hdr), Paragraph('Centre', s_hdr),
            Paragraph('Etat', s_hdr),   Paragraph('Capacite', s_hdr),
            Paragraph('Prochaine epreuve', s_hdr), Paragraph('Expire', s_hdr),
        ]]
        for r in tous:
            recip_rows.append([
                Paragraph(r.numero_serie, s_cell),
                Paragraph(r.centre.nom, s_cell),
                Paragraph(r.get_etat_display(), s_cell),
                Paragraph(f'{r.capacite_kg} kg', s_cell_c),
                Paragraph(str(r.date_prochaine_epreuve), s_cell_c),
                Paragraph('OUI' if r.epreuve_expiree else 'Non', s_cell_c),
            ])
        t5 = Table(recip_rows, colWidths=[3.5*cm, 4*cm, 3*cm, 2*cm, 3*cm, 1.5*cm])
        t5.setStyle(TableStyle([
            ('BACKGROUND',    (0,0), (-1,0), BLEU),
            ('ROWBACKGROUNDS',(0,1), (-1,-1), [GRIS, colors.white]),
            ('GRID',          (0,0), (-1,-1), 0.3, BORD),
            ('TOPPADDING',    (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING',   (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        story.append(t5)
        story.append(Spacer(1, 0.4*cm))

        # ── 6. Historique des mouvements ──
        story.append(Paragraph('6. Historique des mouvements (50 derniers)', s_h1))
        mouvements = Mouvement.objects.filter(recipient__in=tous).order_by('-date_heure')[:50]
        if mouvements:
            mouv_rows = [[
                Paragraph('N Serie', s_hdr),    Paragraph('Transition', s_hdr),
                Paragraph('Agent', s_hdr),       Paragraph('Observation', s_hdr),
                Paragraph('Date', s_hdr),
            ]]
            for m in mouvements:
                obs = m.observation[:40] + ('...' if len(m.observation) > 40 else '')
                mouv_rows.append([
                    Paragraph(m.recipient.numero_serie, s_cell),
                    Paragraph(f'{m.ancien_etat} -> {m.nouvel_etat}', s_cell),
                    Paragraph(m.agent.username, s_cell),
                    Paragraph(obs, s_cell),
                    Paragraph(m.date_heure.strftime('%d/%m/%Y %H:%M'), s_cell_c),
                ])
            t6 = Table(mouv_rows, colWidths=[3*cm, 3*cm, 2.5*cm, 5*cm, 3.5*cm])
            t6.setStyle(TableStyle([
                ('BACKGROUND',    (0,0), (-1,0), BLEU),
                ('ROWBACKGROUNDS',(0,1), (-1,-1), [GRIS, colors.white]),
                ('GRID',          (0,0), (-1,-1), 0.3, BORD),
                ('TOPPADDING',    (0,0), (-1,-1), 5), ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                ('LEFTPADDING',   (0,0), (-1,-1), 6), ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
            ]))
            story.append(t6)
        else:
            story.append(Paragraph('Aucun mouvement enregistre.', s_body))

        # ── Build ──
        doc.build(story)
        buffer.seek(0)
        resp = HttpResponse(buffer, content_type='application/pdf')
        resp['Content-Disposition'] = f'attachment; filename=rapport_dashboard_{date.today()}.pdf'
        return resp


class ExportExcelView(APIView):
    permission_classes = [AllowAny]  # Permet l'appel direct via lien de navigateur

    def get(self, request):
        # Authentification par token dans l'URL si fourni
        token_param = request.query_params.get('token')
        if token_param:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from django.contrib.auth import get_user_model
                User = get_user_model()
                validated = AccessToken(token_param)
                request.user = User.objects.get(id=validated['user_id'])
            except Exception:
                return HttpResponse('Token invalide.', status=401)

        # Filtrage par centre selon l'utilisateur connecté
        tous = Recipient.objects.all().select_related('centre')
        if hasattr(request.user, 'role') and request.user.role in ['agent', 'chef_centre'] and request.user.centre_id:
            tous = tous.filter(centre_id=request.user.centre_id)

        # Génération du classeur Excel
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Inventaire_Tanks"

        en_tetes = ['ID', 'Numero Serie', 'Etat', 'Centre Logistique', 'Capacite (kg)', 'Prochaine Epreuve', 'Status']
        ws.append(en_tetes)

        for r in tous:
            statut = 'EXPIREE' if r.epreuve_expiree else 'CONFORME'
            ws.append([
                r.id,
                r.numero_serie or '',
                r.get_etat_display() if hasattr(r, 'get_etat_display') else r.etat,
                r.centre.nom if r.centre else 'Non defini',
                r.capacite_kg,
                str(r.date_prochaine_epreuve) if r.date_prochaine_epreuve else '',
                statut
            ])

        response = HttpResponse(
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = 'attachment; filename="Inventaire_Tanks.xlsx"'
        wb.save(response)
        return response


class HistoriqueMouvementsView(generics.ListAPIView):
    serializer_class   = MouvementSerializer
    permission_classes = [EstAgent]

    def get_queryset(self):
        recipient_id = self.kwargs['pk']
        return Mouvement.objects.filter(
            recipient_id=recipient_id
        ).order_by('-date_heure')


class ConfigPeriodiciteView(generics.ListCreateAPIView):
    queryset           = ConfigPeriodicite.objects.all()
    serializer_class   = ConfigPeriodiciteSerializer
    permission_classes = [EstAdmin]


class ConfigPeriodiciteDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset           = ConfigPeriodicite.objects.all()
    serializer_class   = ConfigPeriodiciteSerializer
    permission_classes = [EstAdmin]


class SupervisionMouvementsView(generics.ListAPIView):
    serializer_class   = MouvementSerializer
    permission_classes = [EstChefCentre]

    def get_queryset(self):
        user = self.request.user
        q = Mouvement.objects.all().order_by('-date_heure')
        if user.role == 'chef_centre' and user.centre_id:
            q = q.filter(centre_id=user.centre_id)
        return q[:100]  # 100 derniers mouvements


# ✅ APRÈS — corrigé
class AnomalieCreateView(APIView):
    permission_classes = [EstChefCentre]

    def post(self, request, mouvement_id):        # ✅ nom cohérent
        try:
            mouvement = Mouvement.objects.get(pk=mouvement_id)  # ✅ variable correcte
        except Mouvement.DoesNotExist:
            return Response({'erreur': 'Mouvement introuvable'}, status=404)

        commentaire = request.data.get('commentaire', '').strip()
        if len(commentaire) < 5:
            return Response({'erreur': 'Commentaire trop court (min. 5 caractères)'}, status=400)

        anomalie = Anomalie.objects.create(
            mouvement=mouvement,
            chef_centre=request.user,
            commentaire=commentaire,
        )
        return Response(AnomalieSerializer(anomalie).data, status=201)

class AnomalieListView(generics.ListAPIView):
    serializer_class   = AnomalieSerializer
    permission_classes = [EstChefCentre]

    def get_queryset(self):
        mouvement_id = self.kwargs['mouvement_id']
        return Anomalie.objects.filter(mouvement_id=mouvement_id)