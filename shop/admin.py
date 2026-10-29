from django.contrib import admin
from .models import Ristorante, Prodotto, Ingrediente, Ordine, DettaglioOrdine, Coupon, RicettaIngrediente

admin.site.register(Ristorante)

class RicettaIngredienteInline(admin.TabularInline):
    model = RicettaIngrediente
    extra = 3

@admin.register(Prodotto)
class ProdottoAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'prezzo')
    list_filter = ('categoria',)
    search_fields = ('nome', 'categoria')
    filter_horizontal = ('ingredienti',)
    inlines = [RicettaIngredienteInline]

@admin.register(Ingrediente)
class IngredienteAdmin(admin.ModelAdmin):
    list_display = ('nome', 'disponibile')
    list_filter = ('disponibile',)

@admin.register(Ordine)
class OrdineAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_cliente', 'tipo_consegna', 'prezzo_totale', 'stato')
    list_filter = ('stato', 'tipo_consegna')
    search_fields = ('nome_cliente', 'telefono', 'indirizzo')

@admin.register(DettaglioOrdine)
class DettaglioOrdineAdmin(admin.ModelAdmin):
    list_display = ('id', 'ordine', 'prodotto', 'quantita', 'prezzo_totale_articolo')

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('codice', 'sconto_percentuale', 'attivo')
    list_filter = ('attivo',)

@admin.register(RicettaIngrediente)
class RicettaIngredienteAdmin(admin.ModelAdmin):
    list_display = ('prodotto', 'ingrediente', 'quantita_richiesta')
    list_filter = ('prodotto',)