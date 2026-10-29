from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from datetime import timedelta
from django.db.models import Sum, Count, Avg
from django.db.models import Q
from .models import Ristorante, Prodotto, Ingrediente, Ordine, Coupon
import stripe
from django.conf import settings
from django.urls import reverse, get_resolver
import datetime
from django.db import transaction
from .models import Ristorante, Prodotto, Ordine, DettaglioOrdine, DettaglioOrdineModificatore, OpzioneModificatore, RicettaIngrediente, User
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.http import JsonResponse


stripe.api_key = settings.STRIPE_SECRET_KEY


# -------------------------------------------------------------
# GESTIONE RUOLI E DECORATORI DI ACCESSO
# -------------------------------------------------------------
def is_cucina(user):
    return user.is_authenticated and (user.groups.filter(name='Cucina').exists() or user.is_superuser)

def is_rider(user):
    return user.is_authenticated and (user.groups.filter(name='Rider').exists() or user.is_superuser)

def is_cassa_o_gestore(user):
    return user.is_authenticated and (user.groups.filter(name='Cassa').exists() or user.is_superuser)

def solo_cucina_required(view_func):
    return user_passes_test(is_cucina, login_url='/accounts/login/')(view_func)

def solo_cassa_required(view_func):
    return user_passes_test(is_cassa_o_gestore, login_url='/accounts/login/')(view_func)


# -------------------------------------------------------------
# 1. MENU MULTI-TENANT
# -------------------------------------------------------------
def menu_view(request, ristorante_slug=None):
    if ristorante_slug:
        ristorante = get_object_or_404(Ristorante, slug=ristorante_slug, attivo=True)
    else:
        ristorante = Ristorante.objects.filter(attivo=True).first()
        if not ristorante:
            return render(request, 'shop/errore.html', {'messaggio': 'Nessun ristorante attivo trovato.'})

    prodotti = Prodotto.objects.filter(ristorante=ristorante)
    ingredienti = Ingrediente.objects.filter(ristorante=ristorante)

    categoria_selezionata = request.GET.get('cat', 'kebab')

    if categoria_selezionata == 'bibite':
        categoria_filtrata = 'bevande'
    elif categoria_selezionata == 'pizze':
        categoria_filtrata = 'pizza'
    else:
        categoria_filtrata = categoria_selezionata

    tavolo_param = request.GET.get('tavolo')
    if tavolo_param:
        request.session['numero_tavolo_qr'] = tavolo_param

    prodotti = prodotti.filter(categoria__iexact=categoria_filtrata)

    context = {
        'ristorante': ristorante,
        'prodotti': prodotti,
        'ingredienti': ingredienti,
        'categoria_selezionata': categoria_selezionata,
    }
    return render(request, 'shop/menu.html', context)


def cucina_dashboard_view(request):
    if request.method == 'POST':
        ordine_id = request.POST.get('ordine_id')
        nuovo_stato = request.POST.get('stato')
        rider_val = request.POST.get('rider_id')

        if ordine_id:
            ordine = get_object_or_404(Ordine, id=ordine_id)
            
            if nuovo_stato:
                ordine.stato = nuovo_stato
            
            # Assegniamo il valore del rider (stringa o null)
            if rider_val and rider_val.strip():
                ordine.rider = rider_val
            else:
                ordine.rider = None

            ordine.save()
            messages.success(request, f"Ordine #{ordine.id} aggiornato: Stato '{ordine.stato}', Rider '{ordine.rider}'")
            return redirect('cucina_dashboard')

    ordini = Ordine.objects.all().order_by('-creato_il')
    ingredienti = Ingrediente.objects.all()
    context = {
        'ordini': ordini,
        'ingredienti': ingredienti,  # <-- Questo mancava e faceva rimanere il box vuoto!
    }
    return render(request, 'shop/cucina.html', context)

# -------------------------------------------------------------
# 3. STATISTICHE E ANALYTICS MULTI-TENANT
# -------------------------------------------------------------
def statistiche_view(request):
    ristorante_attivo = Ristorante.objects.filter(attivo=True).first()
    
    if ristorante_attivo:
        ordini_base = Ordine.objects.filter(ristorante=ristorante_attivo)
    else:
        ordini_base = Ordine.objects.all()

    ordini_validi = ordini_base.filter(pagato=True) | ordini_base.filter(stato='completato')

    oggi = timezone.now().date()
    inizio_settimana = oggi - datetime.timedelta(days=oggi.weekday())
    inizio_mese = oggi.replace(day=1)

    incasso_oggi = ordini_validi.filter(
        creato_il__date=oggi
    ).aggregate(Sum('prezzo_totale'))['prezzo_totale__sum'] or 0.00

    incasso_settimana = ordini_validi.filter(
        creato_il__date__gte=inizio_settimana
    ).aggregate(Sum('prezzo_totale'))['prezzo_totale__sum'] or 0.00

    incasso_mese = ordini_validi.filter(
        creato_il__date__gte=inizio_mese
    ).aggregate(Sum('prezzo_totale'))['prezzo_totale__sum'] or 0.00

    totale_cumulato = ordini_validi.aggregate(Sum('prezzo_totale'))['prezzo_totale__sum'] or 0.00

    totale_ordini_count = ordini_validi.count()
    scontrino_medio = ordini_validi.aggregate(Avg('prezzo_totale'))['prezzo_totale__avg'] or 0.00

    incasso_carte = ordini_base.filter(
        pagato=True
    ).aggregate(Sum('prezzo_totale'))['prezzo_totale__sum'] or 0.00

    incasso_contanti = ordini_base.filter(
        pagato=False
    ).aggregate(Sum('prezzo_totale'))['prezzo_totale__sum'] or 0.00

    asporto_count = ordini_base.filter(tipo_consegna='asporto').count()
    domicilio_count = ordini_base.filter(tipo_consegna='domicilio').count()
    ritiro_count = ordini_base.filter(tipo_consegna='ritiro').count()
    tavolo_count = ordini_base.filter(tipo_consegna='tavolo').count()

    ultimi_ordini = ordini_base.order_by('-id')[:10]
    
    prodotti_piu_venduti = DettaglioOrdine.objects.exclude(
        ordine__stato='annullato'
    ).values(
        'prodotto__nome'
    ).annotate(
        quantita_totale=Sum('quantita'),
        incasso_totale=Sum('prezzo_totale_articolo')
    ).order_by('-quantita_totale')[:5]
    
    context = {
        'incasso_oggi': incasso_oggi,
        'incasso_settimana': incasso_settimana,
        'incasso_mese': incasso_mese,
        'totale_cumulato': totale_cumulato,
        'scontrino_medio': scontrino_medio,
        'totale_ordini_count': totale_ordini_count,
        'incasso_carte': incasso_carte,
        'incasso_contanti': incasso_contanti,
        'asporto_count': asporto_count,
        'domicilio_count': domicilio_count,
        'ritiro_count': ritiro_count,
        'tavolo_count': tavolo_count,
        'ultimi_ordini': ultimi_ordini,
        'prodotti_piu_venduti': prodotti_piu_venduti,
    }
    return render(request, 'shop/statistiche.html', context)


# -------------------------------------------------------------
# 4. DASHBOARD GENERALE E ALTRE FUNZIONI UTILI
# -------------------------------------------------------------
def dashboard_view(request):
    ristoranti = Ristorante.objects.filter(attivo=True)
    return render(request, 'shop/dashboard.html', {'ristoranti': ristoranti})


def carrello_view(request):
    # Leggiamo correttamente 'carrello' (in italiano) per sincronizzarlo con tutto il resto
    carrello = request.session.get('carrello', {})
    coupon_code = request.session.get('coupon_code')
    sconto_percentuale = request.session.get('sconto_percentuale', 0)
    
    totale_prodotti = 0
    
    # Gestione sicura sia se è un dizionario che se è una lista
    if isinstance(carrello, dict):
        for item in carrello.values():
            if isinstance(item, dict):
                totale_prodotti += float(item.get('prezzo', 0)) * int(item.get('quantita', 1))
    elif isinstance(carrello, list):
        for item in carrello:
            if isinstance(item, dict):
                totale_prodotti += float(item.get('prezzo', 0)) * int(item.get('quantita', 1))

    sconto_valore = (totale_prodotti * sconto_percentuale) / 100
    totale_finale = max(0.0, totale_prodotti - sconto_valore)

    context = {
        'carrello': carrello,
        'coupon_code': coupon_code,
        'sconto_percentuale': sconto_percentuale,
        'sconto_valore': sconto_valore,
        'totale_prodotti': totale_prodotti,
        'totale_finale': totale_finale,
    }
    return render(request, 'shop/carrello.html', context)


def svuota_carrello(request):
    if 'carrello' in request.session:
        del request.session['carrello']
    if 'coupon_code' in request.session:
        del request.session['coupon_code']
    if 'sconto_percentuale' in request.session:
        del request.session['sconto_percentuale']
    request.session.modified = True
    messages.success(request, "Carrello svuotato.")
    return redirect('menu')


def personalizza_prodotto_view(request, prodotto_id):
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    ingredienti = Ingrediente.objects.filter(ristorante=prodotto.ristorante)
    
    if request.method == 'POST':
        ingredienti_selezionati_ids = request.POST.getlist('ingredienti')
        ingredienti_validi = Ingrediente.objects.filter(
            id__in=ingredienti_selezionati_ids,
            ristorante=prodotto.ristorante,
            disponibile=True
        )
        
        nomi_ingredienti = [ing.nome for ing in ingredienti_validi]
        if len(ingredienti_validi) == ingredienti.count():
            dettaglio_custom = "Al Menù"
        elif nomi_ingredienti:
            dettaglio_custom = ", ".join(nomi_ingredienti)
        else:
            dettaglio_custom = "Senza ingredienti"
        
        carrello = request.session.get('carrello', [])
        carrello.append({
            'prodotto_id': prodotto.id,
            'nome': prodotto.nome,
            'prezzo': float(prodotto.prezzo),
            'ingredienti': dettaglio_custom,
            'quantita': 1
        })
        request.session['carrello'] = carrello
        
        return redirect('carrello')

    return render(request, 'shop/personalizza.html', {
        'prodotto': prodotto, 
        'ingredienti': ingredienti
    })


def applica_coupon_ajax(request):
    """Gestisce l'applicazione del coupon in background senza ricaricare la pagina."""
    if request.method == 'POST':
        codice = request.POST.get('coupon', '').strip()
        try:
            coupon = Coupon.objects.get(codice__iexact=codice, attivo=True)
            request.session['coupon_code'] = coupon.codice
            request.session['sconto_percentuale'] = coupon.sconto_percentuale
            request.session.modified = True
            
            return JsonResponse({
                'success': True,
                'codice': coupon.codice,
                'sconto_percentuale': coupon.sconto_percentuale,
                'message': f"Coupon '{coupon.codice}' applicato! Sconto del {coupon.sconto_percentuale}%."
            })
        except Coupon.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': "Codice coupon non valido o scaduto."
            })
    return JsonResponse({'success': False, 'message': 'Metodo non consentito.'}, status=400)


def checkout_view(request):
    carrello = request.session.get('carrello', {})
    totale_lordo = 0.0

    if isinstance(carrello, dict):
        for item in carrello.values():
            if isinstance(item, dict):
                prezzo = float(item.get('prezzo', 0))
                quantita = int(item.get('quantita', 1))
                item['totale_articolo'] = round(prezzo * quantita, 2)
                totale_lordo += item['totale_articolo']
    elif isinstance(carrello, list):
        for item in carrello:
            if isinstance(item, dict):
                prezzo = float(item.get('prezzo', 0))
                quantita = int(item.get('quantita', 1))
                totale_lordo += round(prezzo * quantita, 2)

    totale_lordo = round(totale_lordo, 2)
    sconto_percentuale = request.session.get('sconto_percentuale', 0)
    sconto_valore = round((totale_lordo * sconto_percentuale) / 100, 2)
    totale_complessivo = max(0.0, round(totale_lordo - sconto_valore, 2))

    if request.method == 'POST':
        if not carrello:
            return redirect('menu')
        
        ristorante_attivo = Ristorante.objects.filter(attivo=True).first()
        nome_cliente = request.POST.get('nome_cliente', 'Cliente')
        tipo_consegna = request.POST.get('tipo_consegna', 'ritiro')

        telefono = request.POST.get('telefono', '') if tipo_consegna != 'tavolo' else ''
        indirizzo = request.POST.get('indirizzo', '') if tipo_consegna == 'domicilio' else ''
        numero_tavolo = request.POST.get('numero_tavolo', '') if tipo_consegna == 'tavolo' else ''

        testo_dettagli = ''
        items_iterable = carrello.values() if isinstance(carrello, dict) else carrello
        for item in items_iterable:
            if isinstance(item, dict):
                nome_prod = item.get('nome', 'Prodotto')
                qta = item.get('quantita', 1)
                prezzo_art = item.get('totale_articolo', 0)
                ingredienti_nomi = item.get('ingredienti_nomi', [])
                if not ingredienti_nomi:
                    ing_ids = item.get('ingredienti', [])
                    for ing_id in ing_ids:
                        ing_obj = Ingrediente.objects.filter(id=ing_id).first()
                        if ing_obj:
                            ingredienti_nomi.append(ing_obj.nome)
                
                ing_str = ', '.join(ingredienti_nomi) if ingredienti_nomi else 'Standard / Nessuna modifica'
                testo_dettagli += f'- {qta}x {nome_prod} (€{prezzo_art:.2f})\n  Ingredienti: {ing_str}\n\n'
        if sconto_percentuale > 0:
            testo_dettagli += f"🎟️ Coupon applicato: -{sconto_percentuale}% (-€{sconto_valore:.2f})\n"

        ordine = Ordine.objects.create(
            ristorante=ristorante_attivo,
            nome_cliente=nome_cliente,
            telefono=telefono,
            tipo_consegna=tipo_consegna,
            indirizzo=indirizzo,
            numero_tavolo=numero_tavolo,
            prezzo_totale=totale_complessivo,
            dettagli_articoli=testo_dettagli,
            pagato=False,
            stato='nuovo'
        )

        for item in items_iterable:
            if isinstance(item, dict):
                prodotto_id = item.get('prodotto_id')
                if prodotto_id:
                    prodotto_obj = Prodotto.objects.filter(id=prodotto_id).first()
                    if prodotto_obj:
                        qta = int(item.get('quantita', 1))
                        prezzo_unita = float(item.get('prezzo', prodotto_obj.prezzo))
                        totale_art = round(prezzo_unita * qta, 2)
                        
                        DettaglioOrdine.objects.create(
                            ordine=ordine,
                            prodotto=prodotto_obj,
                            quantita=qta,
                            prezzo_unitario=prezzo_unita,
                            prezzo_totale_articolo=totale_art
                        )

        try:
            session = stripe.checkout.Session.create(
                line_items=[{
                    'price_data': {
                        'currency': 'eur',
                        'product_data': {
                            'name': f'Ordine #{ordine.id} - Kebab Shop',
                        },
                        'unit_amount': int(round(ordine.prezzo_totale * 100)),
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('pagamento_successo', args=[ordine.id])
                ),
                cancel_url=request.build_absolute_uri(
                    reverse('pagamento_annullato', args=[ordine.id])
                ),
            )

            if 'carrello' in request.session:
                del request.session['carrello']
            if 'coupon_code' in request.session:
                del request.session['coupon_code']
            if 'sconto_percentuale' in request.session:
                del request.session['sconto_percentuale']
            request.session.modified = True

            return redirect(session.url, code=303)

        except Exception as e:
            return render(request, 'shop/errore.html', {'errore': str(e)})

    context = {
        'carrello': carrello,
        'totale_lordo': totale_lordo,
        'sconto_percentuale': sconto_percentuale,
        'sconto_valore': sconto_valore,
        'totale_complessivo': totale_complessivo,
    }
    return render(request, 'shop/checkout.html', context)

def ordine_successo_view(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)
    return render(request, 'shop/successo.html', {'ordine': ordine})


def aggiorna_stato_ordine(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)
    if request.method == 'POST':
        nuovo_stato = request.POST.get('stato')
        rider_id = request.POST.get('rider_id')
        
        if nuovo_stato:
            if nuovo_stato == 'completato' and ordine.stato != 'completato':
                scala_magazzino_per_ordine(ordine)
            ordine.stato = nuovo_stato
        
        if rider_id:
            ordine.rider_id = rider_id if rider_id != 'No Rider' else None
            
        ordine.save()
        messages.success(request, f"Ordine #{ordine.id} aggiornato con successo!")
        
    return redirect(request.META.get('HTTP_REFERER', 'cucina_dashboard'))


def stato_ordine_view(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)
    return render(request, 'shop/stato_ordine.html', {'ordine': ordine})


def stampa_comanda_view(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)
    return render(request, 'shop/comanda_singola.html', {'ordine': ordine})


def stampa_comanda(request, ordine_id):
    return stampa_comanda_view(request, ordine_id)


def toggle_ingrediente(request, ingrediente_id):
    ingrediente = get_object_or_404(Ingrediente, id=ingrediente_id)
    ingrediente.disponibile = not ingrediente.disponibile
    ingrediente.save()
    return redirect(request.META.get('HTTP_REFERER', 'cucina_dashboard'))


def applica_coupon(request):
    if request.method == 'POST':
        codice = request.POST.get('coupon', '').strip()
        try:
            coupon = Coupon.objects.get(codice__iexact=codice, attivo=True)
            request.session['coupon_code'] = coupon.codice
            request.session['sconto_percentuale'] = coupon.sconto_percentuale
            messages.success(request, f"Coupon '{coupon.codice}' applicato! Sconto del {coupon.sconto_percentuale}%.")
        except Coupon.DoesNotExist:
            messages.error(request, "Codice coupon non valido o scaduto.")
    return redirect('carrello')


def stato_ordine(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)
    return render(request, 'shop/stato_ordine.html', {'ordine': ordine})


# -------------------------------------------------------------
# 5. PAGAMENTI STRIPE & CARRELLO
# -------------------------------------------------------------
def crea_checkout_session(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': f'Ordine #{ordine.id} - Kebab Shop',
                    },
                    'unit_amount': int(ordine.prezzo_totale * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(
                reverse('pagamento_successo', args=[ordine.id])
            ),
            cancel_url=request.build_absolute_uri(
                reverse('pagamento_annullato', args=[ordine.id])
            ),
        )
        return redirect(session.url, code=303)
    except Exception as e:
        return render(request, 'shop/errore.html', {'errore': str(e)})


def pagamento_successo(request, ordine_id):
    ordine = get_object_or_404(Ordine, id=ordine_id)
    ordine.pagato = True
    if not ordine.stato or ordine.stato == 'da_pagare':
        ordine.stato = 'ricevuto'
    ordine.save()
    request.session['ultimo_ordine_id'] = ordine.id
    return redirect('stato_ordine', ordine_id=ordine.id)


def pagamento_annullato(request, ordine_id):
    return render(request, 'shop/annullato.html')


def stripe_webhook(request):
    from django.http import HttpResponse
    return HttpResponse(status=200)


def aggiungi_al_carrello(request, prodotto_id):
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    carrello = request.session.get('carrello', {})

    # Quantità e ingredienti predefiniti (per un click diretto tipo Bevande)
    quantita = 1
    ingredienti_ids = []
    ingredienti_nomi = []

    # Se arriva dal form di personalizzazione (POST)
    if request.method == 'POST':
        quantita = int(request.POST.get('quantita', 1))
        ingredienti_ids = request.POST.getlist('ingredienti')
        if ingredienti_ids:
            ing_objs = Ingrediente.objects.filter(id__in=ingredienti_ids)
            ingredienti_nomi = [ing.nome for ing in ing_objs]

    # Chiave unica per distinguere prodotti standard o con varianti di ingredienti
    ing_key = "-".join(sorted([str(i) for i in ingredienti_ids])) if ingredienti_ids else "standard"
    item_key = f"{prodotto.id}_{ing_key}"

    prezzo_unitario = float(prodotto.prezzo)

    if item_key in carrello:
        carrello[item_key]['quantita'] += quantita
        carrello[item_key]['totale_articolo'] = round(carrello[item_key]['quantita'] * prezzo_unitario, 2)
    else:
        carrello[item_key] = {
            'prodotto_id': prodotto.id,
            'nome': prodotto.nome,
            'prezzo': prezzo_unitario,
            'quantita': quantita,
            'totale_articolo': round(quantita * prezzo_unitario, 2),
            'ingredienti': ingredienti_ids,
            'ingredienti_nomi': ingredienti_nomi
        }

    request.session['carrello'] = carrello
    request.session.modified = True
    
    messages.success(request, f"{quantita}x {prodotto.nome} aggiunto al carrello!")

    # Se arrivava dal POST con l'opzione "continua", resta sulla personalizzazione, altrimenti va al checkout
    if request.method == 'POST':
        prossima_azione = request.POST.get('prossima_azione', 'checkout')
        if prossima_azione == 'continua':
            return redirect('personalizza_prodotto', prodotto_id=prodotto.id)

    # Per le bevande o click diretti, porta direttamente alla pagina unificata di pagamento/checkout
    return redirect('checkout')

@transaction.atomic
def crea_ordine_con_modificatori(request, ristorante_slug):
    ristorante = get_object_or_404(Ristorante, slug=ristorante_slug)
    
    if request.method == 'POST':
        nome_cliente = request.POST.get('nome_cliente', 'Cliente')
        telefono = request.POST.get('telefono', '')
        tipo_consegna = request.POST.get('tipo_consegna', 'ritiro')
        indirizzo = request.POST.get('indirizzo', '')
        numero_tavolo = request.POST.get('numero_tavolo', '')
        
        ordine = Ordine.objects.create(
            ristorante=ristorante,
            nome_cliente=nome_cliente,
            telefono=telefono,
            tipo_consegna=tipo_consegna,
            indirizzo=indirizzo,
            numero_tavolo=numero_tavolo,
            prezzo_totale=0.00
        )
        
    return redirect('menu_ristorante', slug=ristorante_slug)


def dettaglio_prodotto_vista(request, ristorante_slug, prodotto_id):
    ristorante = get_object_or_404(Ristorante, slug=ristorante_slug)
    prodotto = get_object_or_404(Prodotto, id=prodotto_id, ristorante=ristorante)
    gruppi_modificatori = prodotto.gruppi_modificatori.filter(attivo=True).prefetch_related('opzioni')
    
    context = {
        'ristorante': ristorante,
        'prodotto': prodotto,
        'gruppi_modificatori': gruppi_modificatori,
    }
    return render(request, 'kebab/dettaglio_prodotto.html', context)


@solo_cucina_required
def kds_cucina_view(request, ristorante_slug):
    ristorante = get_object_or_404(Ristorante, slug=ristorante_slug)
    
    ordini_attivi = Ordine.objects.filter(
        ristorante=ristorante,
        stato__in=['ricevuto', 'in_preparazione']
    ).prefetch_related('articoli__modificatori_scelti', 'articoli__prodotto').order_by('creato_il')
    
    riepilogo_articoli = Ordine.objects.filter(
        ristorante=ristorante,
        stato__in=['ricevuto', 'in_preparazione']
    ).filter(articoli__isnull=False).values(
        'articoli__prodotto__nome'
    ).annotate(
        totale_quantita=Sum('articoli__quantita')
    ).order_by('-totale_quantita')

    context = {
        'ristorante': ristorante,
        'ordini_attivi': ordini_attivi,
        'riepilogo_articoli': riepilogo_articoli,
    }
    return render(request, 'kebab/kds_cucina.html', context)


def scala_magazzino_per_ordine(ordine):
    for dettaglio in ordine.articoli.all():
        prodotto = dettaglio.prodotto
        quantita_ordinata = dettaglio.quantita
        
        ricette = RicettaIngrediente.objects.filter(prodotto=prodotto).select_related('ingrediente')
        for ricetta in ricette:
            ingrediente = ricetta.ingrediente
            totale_da_scalare = ricetta.quantita_richiesta * quantita_ordinata
            
            if hasattr(ingrediente, 'quantita'):
                ingrediente.quantita = max(0, ingrediente.quantita - totale_da_scalare)
                if ingrediente.quantita == 0:
                    ingrediente.disponibile = False
                ingrediente.save()


def gestisci_ricetta_prodotto(request, prodotto_id):
    prodotto = get_object_or_404(Prodotto, id=prodotto_id)
    ristorante = prodotto.ristorante
    
    ricetta_items = RicettaIngrediente.objects.filter(prodotto=prodotto).select_related('ingrediente')
    ingredienti_disponibili = Ingrediente.objects.filter(ristorante=ristorante) if ristorante else Ingrediente.objects.all()

    if request.method == 'POST':
        azione = request.POST.get('azione')
        
        if azione == 'aggiungi_aggiorna':
            ingrediente_id = request.POST.get('ingrediente_id')
            quantita = request.POST.get('quantita_richiesta', 1.0)
            
            if ingrediente_id:
                ingrediente = get_object_or_404(Ingrediente, id=ingrediente_id)
                RicettaIngrediente.objects.update_or_create(
                    prodotto=prodotto,
                    ingrediente=ingrediente,
                    defaults={'quantita_richiesta': quantita}
                )
                messages.success(request, f"Ingrediente {ingrediente.nome} salvato nella ricetta!")
                
        elif azione == 'elimina':
            ricetta_id = request.POST.get('ricetta_id')
            RicettaIngrediente.objects.filter(id=ricetta_id, prodotto=prodotto).delete()
            messages.success(request, "Ingrediente rimosso dalla ricetta.")
            
        return redirect('gestisci_ricetta', prodotto_id=prodotto.id)

    context = {
        'prodotto': prodotto,
        'ricetta_items': ricetta_items,
        'ingredienti_disponibili': ingredienti_disponibili,
    }
    return render(request, 'shop/gestisci_ricetta.html', context)


def login_personalizzato_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            if user.groups.filter(name='Cucina').exists():
                return redirect('kds_cucina', ristorante_slug='istanbul-kebab')
            elif user.groups.filter(name='Rider').exists():
                return redirect('dashboard_rider')
            elif user.groups.filter(name='Cassa').exists() or user.is_superuser:
                return redirect('menu')
            else:
                return redirect('home')
        else:
            messages.error(request, "Credenziali non valide.")
            
    return render(request, 'shop/login.html')


def statistiche_ristorante_view(request, ristorante_slug):
    ristorante = get_object_or_404(Ristorante, slug=ristorante_slug)
    ordini_validi = Ordine.objects.filter(ristorante=ristorante, stato='completato')
    
    statistiche_generali = ordini_validi.aggregate(
        fatturato_totale=Sum('prezzo_totale'),
        totale_ordini=Count('id'),
        scontrino_medio=Avg('prezzo_totale')
    )
    
    prodotti_piu_venduti = DettaglioOrdine.objects.filter(
        ordine__ristorante=ristorante,
        ordine__stato='completato'
    ).values(
        'prodotto__nome'
    ).annotate(
        quantita_totale=Sum('quantita'),
        incasso_totale=Sum('prezzo_totale_articolo')
    ).order_by('-quantita_totale')[:5]

    context = {
        'ristorante': ristorante,
        'stats': statistiche_generali,
        'prodotti_piu_venduti': prodotti_piu_venduti,
    }
    return render(request, 'shop/statistiche.html', context)


@user_passes_test(is_rider, login_url='/accounts/login/')
def dashboard_rider_view(request):
    is_rider = request.user.groups.filter(name='Rider').exists()
    is_cucina = request.user.groups.filter(name='Cucina').exists()
    
    if not request.user.is_authenticated or (not request.user.is_staff and not is_rider and not is_cucina):
        return redirect('menu')
        
    ordini_domicilio = Ordine.objects.filter(
        tipo_consegna='domicilio'
    ).exclude(stato='completato').order_by('-id')

    context = {
        'ordini': ordini_domicilio,
    }
    return render(request, 'shop/dashboard_rider.html', context)



def rimuovi_dal_carrello(request, item_key):
    carrello = request.session.get('carrello', {})
    if item_key in carrello:
        del carrello[item_key]
        request.session['carrello'] = carrello
        request.session.modified = True
        messages.success(request, "Prodotto rimosso dall'ordine.")
    return redirect('checkout')



def modifica_quantita_carrello(request, item_key, azione):
    """
    azione può essere 'aumenta' o 'diminuisci'
    """
    carrello = request.session.get('carrello', {})
    
    if item_key in carrello:
        if azione == 'aumenta':
            carrello[item_key]['quantita'] += 1
        elif azione == 'diminuisci':
            carrello[item_key]['quantita'] -= 1
            if carrello[item_key]['quantita'] <= 0:
                del carrello[item_key]
        
        request.session['carrello'] = carrello
        request.session.modified = True
        
    return redirect(request.META.get('HTTP_REFERER', 'checkout'))

def get_totale_articoli_carrello(carrello):
    totale_pezzi = 0
    if isinstance(carrello, dict):
        for item in carrello.values():
            if isinstance(item, dict):
                totale_pezzi += int(item.get('quantita', 1))
    elif isinstance(carrello, list):
        for item in carrello:
            if isinstance(item, dict):
                totale_pezzi += int(item.get('quantita', 1))
    return totale_pezzi