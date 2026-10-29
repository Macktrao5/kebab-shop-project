import qrcode

# Inserisci il dominio/IP del tuo server (es. 'http://192.168.1.100:8000' in rete locale o il tuo dominio web)
BASE_URL = "http://127.0.0.1:8000"

# Genera i QR code per 10 tavoli
for num_tavolo in range(1, 11):
  url = f"{BASE_URL}/menu/?tavolo={num_tavolo}"
  img = qrcode.make(url)
  img.save(f"qr_tavolo_{num_tavolo}.png")
  print(f"Creato QR Code per Tavolo {num_tavolo}: {url}")