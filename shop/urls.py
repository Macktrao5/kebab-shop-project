from django.urls import path
from .views import applica_coupon_ajax
from .views import ( 
    menu_view, 
    aggiungi_al_carrello, 
    svuota_carrello, 
    checkout_view, 
    ordine_successo_view,
    cucina_dashboard_view, 
    aggiorna_stato_ordine,
    crea_checkout_session, 
    pagamento_successo, 
    pagamento_annullato,
    stripe_webhook, 
    dashboard_view, 
    carrello_view, 
    personalizza_prodotto_view,
    stampa_comanda_view, 
    statistiche_view, 
    stampa_comanda,
    toggle_ingrediente, 
    applica_coupon, 
    dettaglio_prodotto_vista,
    crea_ordine_con_modificatori, 
    kds_cucina_view,
    gestisci_ricetta_prodotto,
    statistiche_ristorante_view,
    dashboard_rider_view,
    stato_ordine_view,
    rimuovi_dal_carrello,
    modifica_quantita_carrello
)

urlpatterns = [
    # -------------------------------------------------------------
    # ROTTE MULTI-TENANT (Per Ristorante Specifico via Slug)
    # -------------------------------------------------------------
    path('ristorante/<slug:ristorante_slug>/', menu_view, name='ristorante_menu'),
    path('ristorante/<slug:ristorante_slug>/cucina/', cucina_dashboard_view, name='ristorante_cucina'),
    path('ristorante/<slug:ristorante_slug>/cucina/kds/', kds_cucina_view, name='kds_cucina'),
    path('ristorante/<slug:ristorante_slug>/statistiche/', statistiche_ristorante_view, name='statistiche_ristorante'),
    path('prodotto/<int:prodotto_id>/ricetta/', gestisci_ricetta_prodotto, name='gestisci_ricetta'),

    # -------------------------------------------------------------
    # ROTTE BASE (Compatibilità con Pulsanti e Template)
    # -------------------------------------------------------------
    path('', dashboard_view, name='dashboard'),
    path('menu/', menu_view, name='menu'),
    path('carrello/', checkout_view, name='carrello'),
    path('modifica-quantita/<str:item_key>/<str:azione>/',modifica_quantita_carrello, name='modifica_quantita_carrello'),
    path('checkout/', checkout_view, name='checkout'),
    path('cucina/', cucina_dashboard_view, name='cucina_dashboard'),
    path('statistiche/', statistiche_view, name='statistiche'),
    path('rider/', dashboard_rider_view, name='dashboard_rider'),
    
    # TRACCIAMENTO STATO ORDINE (Punto di riferimento principale)
    path('stato-ordine/<int:ordine_id>/', stato_ordine_view, name='stato_ordine'),
    path('ordine/<int:ordine_id>/', stato_ordine_view, name='stato_ordine_alt'),

    # -------------------------------------------------------------
    # AZIONI ORDINI & CARRELLO
    # -------------------------------------------------------------
    path('aggiungi/<int:prodotto_id>/', aggiungi_al_carrello, name='aggiungi_al_carrello'),
    path('rimuovi-dal-carrello/<str:item_key>/',rimuovi_dal_carrello, name='rimuovi_dal_carrello'),
    path('svuota/', svuota_carrello, name='svuota_carrello'),
    path('personalizza/<int:prodotto_id>/', personalizza_prodotto_view, name='personalizza_prodotto'),
    path('ordine/successo/<int:ordine_id>/', ordine_successo_view, name='ordine_successo'),
    path('ristorante/<slug:ristorante_slug>/crea-ordine/', crea_ordine_con_modificatori, name='crea_ordine_con_modificatori'),

    # -------------------------------------------------------------
    # GESTIONE CUCINA & STAMPA
    # -------------------------------------------------------------
    path('cucina/aggiorna/<int:ordine_id>/', aggiorna_stato_ordine, name='aggiorna_stato_ordine'),
    path('aggiorna-stato-ordine/<int:ordine_id>/', aggiorna_stato_ordine, name='aggiorna_stato_ordine_alt'),
    path('stampa-comanda/<int:ordine_id>/', stampa_comanda, name='stampa_comanda'),
    path('comanda/<int:ordine_id>/', stampa_comanda_view, name='stampa_comanda_view'),
    path('toggle-ingrediente/<int:ingrediente_id>/', toggle_ingrediente, name='toggle_ingrediente'),
    path('ristorante/<slug:ristorante_slug>/prodotto/<int:prodotto_id>/', dettaglio_prodotto_vista, name='dettaglio_prodotto'),

    # -------------------------------------------------------------
    # MARKETING & PAGAMENTI STRIPE
    # -------------------------------------------------------------
    path('applica-coupon/', applica_coupon, name='applica_coupon'),
    path('applica-coupon-ajax/', applica_coupon_ajax, name='applica_coupon_ajax'),
    path('checkout/stripe/<int:ordine_id>/', crea_checkout_session, name='crea_checkout_session'),
    path('pagamento/successo/<int:ordine_id>/', pagamento_successo, name='pagamento_successo'),
    path('pagamento/annullato/<int:ordine_id>/', pagamento_annullato, name='pagamento_annullato'),
    path('webhook/stripe/', stripe_webhook, name='stripe_webhook'),
]