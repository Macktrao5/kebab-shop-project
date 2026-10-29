import os
import qrcode

# Cambia questo URL con l'IP locale della tua rete (es. http://192.168.1.50:8000) o con il tuo dominio internet
BASE_URL = 'http://127.0.0.1:8000'

# Cartella di destinazione per salvare le immagini dei QR Code
CARTELLA_OUTPUT = 'qr_tavoli'
if not os.path.exists(CARTELLA_OUTPUT):
  os.makedirs(CARTELLA_OUTPUT)

# Generiamo i QR Code per 10 tavoli (puoi cambiare 11 con il numero di tavoli che desideri)
NUMERO_TAVOLI = 10

print("🚀 Generazione QR Code in corso...")

for num in range(1, NUMERO_TAVOLI + 1):
  # L'URL passa il parametro ?tavolo=N
  url = f'{BASE_URL}/menu/?tavolo={num}'

  # Crea l'immagine del QR code
  qr = qrcode.QRCode(
      version=1,
      error_correction=qrcode.constants.ERROR_CORRECT_L,
      box_size=10,
      border=4,
  )
  qr.add_data(url)
  qr.make(fit=True)

  img = qr.make_image(fill_color='black', back_color='white')
  nome_file = os.path.join(CARTELLA_OUTPUT, f'qr_tavolo_{num}.png')
  img.save(nome_file)

  print(f'✅ Creato QR Code per Tavolo {num} -> {nome_file}')

print(
    f'\n🎉 Fatto! Trovi tutte le immagini pronte da stampare nella cartella'
    f' "{CARTELLA_OUTPUT}".'
)