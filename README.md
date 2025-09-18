# ✈️ ADS-B Military Tracker — Italy

Questo progetto raccoglie un insieme di script per il **monitoraggio dei voli militari (ADS-B)**, con salvataggio su CSV/DB e pubblicazione automatica di report in formato Markdown per [Hugo](https://gohugo.io/).

## 📌 Funzionalità principali

- **Raccolta voli militari**  
  Lo script `flight_mil_ita.py` interroga l’endpoint pubblico [`/v2/mil`](https://opendata.adsb.fi/api/v2/mil) e registra solo i contatti con flag militare.
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
