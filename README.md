# ✈️ ADS-B Military Tracker — Italy

Questo progetto raccoglie un insieme di script per il **monitoraggio dei voli militari (ADS-B)**, con salvataggio su CSV/DB e pubblicazione automatica di report in formato Markdown per [Hugo](https://gohugo.io/).

## 📌 Funzionalità principali

- **Raccolta voli militari**  
  Lo script `mil_logger.py` interroga l’endpoint pubblico [`/v2/mil`](https://opendata.adsb.fi/api/v2/mil) e registra solo i contatti con flag militare.
- **Filtro geografico (opzionale)**  
  Possibilità di limitare i contatti ai poligoni definiti in un file GeoJSON (`--polygons-file`).
- **Registrazione CSV**  
  Ogni evento è salvato in `mil.csv` con colonne essenziali:
first_seen_utc, hex, callsign, reg, model_t, lat, lon, alt_ft, gs_kt, squawk, ground
- **Conversione CSV → SQLite**  
Lo script `publish_adsb_report.py` importa i dati da CSV in `events.db`, con deduplica (`PRIMARY KEY` su `first_seen_utc, hex`).
- **Generazione report Hugo**  
Possibilità di generare post giornalieri, settimanali o mensili con tabelle Markdown dei voli militari:
- Titolo in formato:  
  - Giornaliero: `Report voli militari in ITALIA dd.mm.yy`  
  - Settimanale: `Report voli militari in ITALIA settimana dd.mm.yy → dd.mm.yy`  
  - Mensile: `Report voli militari in ITALIA mese mm.yy`
- **Automazione pronta per server**  
Entrambi gli script sono pensati per essere lanciati da cron o systemd.

---

## 📂 Struttura progetto

flight_mil_ita/
├── mil_logger.py # raccolta voli militari, output su CSV
├── publish_adsb_report.py # genera post Hugo dai dati raccolti
├── mil.csv # CSV con i contatti militari (output logger)
├── events.db # DB SQLite (popolato da publish_adsb_report.py)
└── README.md # documentazione progetto

---

## ⚙️ Requisiti

- Python 3.9+
- Moduli standard (`sqlite3`, `csv`, `argparse`, ecc.)
- [Requests](https://pypi.org/project/requests/) per le chiamate API:
  ```bash
  pip install requests

  🚀 Utilizzo
1. Avviare il logger

Avvia la raccolta dei voli militari con intervallo di polling (default 60 secondi):
python3 mil_logger.py --interval 120 --csv /home/pi/flight_mil_ita/mil.csv

Con filtro GeoJSON (es. poligoni Italia):
python3 mil_logger.py --polygons-file polygons_italy.geojson

2. Pubblicare report

Genera report giornaliero:
python3 publish_adsb_report.py --period daily

Settimanale:
python3 publish_adsb_report.py --period weekly

Mensile:
python3 publish_adsb_report.py --period monthly

I post vengono salvati in ~/blog/content/posts/<anno>/YYYY-MM-DD-monitor-mil-report.md.

📊 Esempio output tabella
first_seen_utc	hex	callsign	reg	model_t	lat	lon	alt_ft	gs_kt	squawk	ground
2025-09-17 08:15 UTC	43ea87	MCNZI	MM12345	A139	45.1	9.2	12000	240	7000	0
2025-09-17 09:42 UTC	43ea99	ITA412	MM67890	C130	41.9	12.5	18000	320	7000

🔄 Automazione

Puoi automatizzare con systemd:

/etc/systemd/system/mil_logger.service

[Unit]
Description=ADS-B Military Logger
After=network.target

[Service]
ExecStart=/usr/bin/python3 /home/pi/flight_mil_ita/mil_logger.py --csv /home/pi/flight_mil_ita/mil.csv --interval 120
WorkingDirectory=/home/pi/flight_mil_ita
Restart=always

[Install]
WantedBy=multi-user.target

E con cron per la pubblicazione giornaliera:
0 23 * * * /usr/bin/python3 /home/pi/flight_mil_ita/publish_adsb_report.py --period daily
