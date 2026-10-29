from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from django.utils import timezone


class Ristorante(models.Model):
    nome = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, help_text="Identificativo unico nell'URL (es. istanbul-kebab)")
    indirizzo = models.CharField(max_length=255, blank=True)
    telefono = models.CharField(max_length=20, blank=True)
    attivo = models.BooleanField(default=True)
    creato_il = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nome
    

class Ingrediente(models.Model):
    ristorante = models.ForeignKey(Ristorante, on_delete=models.CASCADE, related_name='ingredienti', null=True, blank=True)
    TIPO_SCELTA = (
        ('verdura', 'Verdura'),
        ('salsa', 'Salsa'),
        ('extra', 'Extra'),
    )

    nome = models.CharField(max_length=100)
    tipo = models.CharField(max_length=20, choices=TIPO_SCELTA, default='verdura')
    disponibile = models.BooleanField(default=True)
    sovrapprezzo = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0.00)]
    )

    def __str__(self):
        return f'{self.nome} (+€{self.sovrapprezzo})' if self.sovrapprezzo > 0 else self.nome


# ==========================================
# NUOVI MODELLI: GRUPPI E OPZIONI MODIFICATORI
# ==========================================

class GruppoModificatore(models.Model):
    """
    Raggruppa le opzioni di personalizzazione (es. "Scegli le Salse", "Aggiunte Extra").
    """
    ristorante = models.ForeignKey(
        Ristorante, 
        on_delete=models.CASCADE, 
        related_name='gruppi_modificatori',
        null=True, blank=True
    )
    nome = models.CharField(max_length=100, help_text="Es. Scegli Salse, Extra Carne, Rimuovi Ingredienti")
    descrizione = models.CharField(max_length=255, blank=True, null=True, help_text="Es. Seleziona fino a 2 salse")
    
    # Regole di vincolo
    min_selezioni = models.PositiveIntegerField(default=0, help_text="0 se facoltativo, 1 o più se obbligatorio")
    max_selezioni = models.PositiveIntegerField(default=1, help_text="Numero massimo di opzioni selezionabili")
    obbligatorio = models.BooleanField(default=False)
    
    attivo = models.BooleanField(default=True)
    ordine = models.PositiveIntegerField(default=0, help_text="Ordine di visualizzazione nel menu")

    class Meta:
        ordering = ['ordine', 'nome']
        verbose_name = "Gruppo Modificatore"
        verbose_name_plural = "Gruppi Modificatori"

    def __str__(self):
        return f"{self.nome} ({self.ristorante.nome if self.ristorante else 'Globale'})"


class OpzioneModificatore(models.Model):
    """
    La singola scelta all'interno di un gruppo (es. "Salsa Piccante", "Doppio Formaggio").
    """
    gruppo = models.ForeignKey(
        GruppoModificatore, 
        on_delete=models.CASCADE, 
        related_name='opzioni'
    )
    nome = models.CharField(max_length=100)
    prezzo_aggiuntivo = models.DecimalField(
        max_digits=6, decimal_places=2, default=0.00,
        validators=[MinValueValidator(0.00)]
    )
    ingrediente = models.ForeignKey(
        Ingrediente, 
        on_delete=models.SET_NULL, 
        null=True, blank=True,
        related_name='opzioni_modificatore',
        help_text="Collegamento opzionale alla gestione scorte"
    )
    disponibile = models.BooleanField(default=True)
    ordine = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordine', 'nome']
        verbose_name = "Opzione Modificatore"
        verbose_name_plural = "Opzioni Modificatori"

    def __str__(self):
        prezzo_str = f" (+€{self.prezzo_aggiuntivo})" if self.prezzo_aggiuntivo > 0 else ""
        return f"{self.nome}{prezzo_str}"


class Prodotto(models.Model):
    ristorante = models.ForeignKey(Ristorante, on_delete=models.CASCADE, related_name='prodotti', null=True, blank=True)
    nome = models.CharField(max_length=200)
    descrizione = models.TextField(blank=True, null=True)
    prezzo = models.DecimalField(max_digits=6, decimal_places=2, validators=[MinValueValidator(0.00)])
    categoria = models.CharField(max_length=100)
    immagine = models.ImageField(upload_to='prodotti/', blank=True, null=True)

    # Ingredienti base associati al prodotto
    ingredienti = models.ManyToManyField(
        Ingrediente, blank=True, related_name='prodotti_collegati'
    )
    
    # Gruppi di modificatori abilitati per questo specifico prodotto
    gruppi_modificatori = models.ManyToManyField(
        GruppoModificatore, blank=True, related_name='prodotti_collegati'
    )

    def __str__(self):
        return self.nome


RIDER_CHOICES = (
    ('nessuno', 'Non Assegnato'),
    ('rider_1', 'Rider 1 (Marco)'),
    ('rider_2', 'Rider 2 (Luca)'),
)

class Ordine(models.Model):
    ristorante = models.ForeignKey(Ristorante, on_delete=models.CASCADE, related_name='ordini', null=True, blank=True)
    dettagli_articoli = models.TextField(blank=True, null=True)
    
    TIPO_CONSEGNA_CHOICES = [
        ('ritiro', 'Ritiro al Locale'),
        ('domicilio', 'Consegna a Domicilio'),
        ('tavolo', 'Consumazione al Tavolo'),
    ]

    STATO_CHOICES = [
        ('ricevuto', 'Ricevuto'),
        ('in_preparazione', 'In Preparazione'),
        ('pronto', 'Pronto'),
        ('completato', 'Completato'),
    ]

    nome_cliente = models.CharField(max_length=100, default='Cliente')
    telefono = models.CharField(max_length=20, blank=True, null=True)
    tipo_consegna = models.CharField(
        max_length=20, choices=TIPO_CONSEGNA_CHOICES, default='ritiro'
    )
    indirizzo = models.CharField(max_length=255, blank=True, null=True)
    numero_tavolo = models.CharField(max_length=20, blank=True, null=True)

    prezzo_totale = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    creato_il = models.DateTimeField(auto_now_add=True)
    stato = models.CharField(
        max_length=20, choices=STATO_CHOICES, default='ricevuto'
    )
    pagato = models.BooleanField(default=False)
    rider = models.CharField(max_length=20, choices=RIDER_CHOICES, default='nessuno')

    @property
    def minuti_trascorsi(self):
        if not self.creato_il:
            return 0
        diff = timezone.now() - self.creato_il
        return int(diff.total_seconds() / 60)

    @property
    def livello_urgenza(self):
        minuti = self.minuti_trascorsi
        if minuti < 5:
            return 'verde'      # Fresco / Normale
        elif 5 <= minuti <= 10:
            return 'giallo'     # In attesa da un po'
        else:
            return 'rosso'      # In ritardo / Urgente!

    def __str__(self):
        return f"Ordine #{self.id} - {self.nome_cliente}"


class DettaglioOrdine(models.Model):
    """
    Rappresenta il singolo articolo acquistato all'interno di un ordine 
    (es. 2x Kebab Piatto con modifiche specifiche).
    """
    ordine = models.ForeignKey(Ordine, on_delete=models.CASCADE, related_name='articoli')
    prodotto = models.ForeignKey(Prodotto, on_delete=models.SET_NULL, null=True)
    quantita = models.PositiveIntegerField(default=1)
    prezzo_unitario = models.DecimalField(max_digits=6, decimal_places=2)
    prezzo_totale_articolo = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        return f"{self.quantita}x {self.prodotto.nome if self.prodotto else 'Prodotto eliminato'} (Ordine #{self.ordine.id})"


class DettaglioOrdineModificatore(models.Model):
    """
    Memorizza le opzioni e salse specifiche scelte dal cliente per quel determinato articolo nell'ordine.
    """
    dettaglio_ordine = models.ForeignKey(DettaglioOrdine, on_delete=models.CASCADE, related_name='modificatori_scelti')
    gruppo_nome = models.CharField(max_length=100)
    opzione_nome = models.CharField(max_length=100)
    prezzo_applicato = models.DecimalField(max_digits=6, decimal_places=2, default=0.00)

    def __str__(self):
        return f"-> {self.gruppo_nome}: {self.opzione_nome} (+€{self.prezzo_applicato})"


class Coupon(models.Model):
    codice = models.CharField(max_length=50, unique=True)
    sconto_percentuale = models.IntegerField(help_text="Inserisci la percentuale di sconto (es. 10 per 10%)", default=0)
    attivo = models.BooleanField(default=True)

    def __str__(self):
        return f"Coupon: {self.codice} ({self.sconto_percentuale}%)"


class RicettaIngrediente(models.Model):
    """
    Definisce la quantità di un ingrediente necessaria per preparare un singolo prodotto (Distinta Base).
    """
    prodotto = models.ForeignKey(
        Prodotto, 
        on_delete=models.CASCADE, 
        related_name='ricetta'
    )
    ingrediente = models.ForeignKey(
        Ingrediente, 
        on_delete=models.CASCADE,
        related_name='utilizzato_in'
    )
    quantita_richiesta = models.DecimalField(
        max_digits=6, 
        decimal_places=2, 
        default=1.00,
        help_text="Quantità scalata (es. 1 per panini, 150 per grammi di carne)"
    )

    def __str__(self):
        return f"{self.quantita_richiesta}x {self.ingrediente.nome} per {self.prodotto.nome}"