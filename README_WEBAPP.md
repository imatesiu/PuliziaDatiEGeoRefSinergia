# Pulizia Dati Sinergia Web App

## Cosa fa

Questa applicazione web locale permette di:

- caricare un file di input in formato `.xlsx`, `.xlsm` oppure `.csv`
- analizzare i dati e classificare ogni riga in:
  - `validi`
  - `da_verificare`
  - `scarti`
- geocodificare i record `validi` tramite OpenStreetMap Nominatim
- generare uno `.zip` finale con tutti gli output del processo

## Flusso di lavoro

Quando carichi un file, l'app esegue questi passaggi:

1. salva temporaneamente il file caricato
2. legge il contenuto del file
3. analizza righe, colonne, duplicati e anomalie
4. genera i CSV separati per categoria
5. geocodifica i record `validi`
6. prepara un archivio `.zip`
7. restituisce lo `.zip` in download

## Contenuto dello ZIP

Lo ZIP di output contiene:

- una copia del file originale caricato
- `*_summary.txt`
- `*_analysis.json`
- `*_validi.csv`
- `*_da_verificare.csv`
- `*_scarti.csv`
- `*_validi_geocoded.csv`
- `job_manifest.json`
- `nominatim_cache.json`

## Avvio dell'app

Dalla cartella del progetto esegui:

```bash
./run_app.sh
```

Poi apri nel browser:

```text
http://127.0.0.1:8000
```

## File principali

- [app.py](/Users/spagnolo/github/PuliziaDatiSinergia/app.py): entrypoint Flask della web app
- [templates/index.html](/Users/spagnolo/github/PuliziaDatiSinergia/templates/index.html): interfaccia di upload
- [georef_pipeline.py](/Users/spagnolo/github/PuliziaDatiSinergia/georef_pipeline.py): logica condivisa di analisi e geocoding
- [analyze_georef_excel.py](/Users/spagnolo/github/PuliziaDatiSinergia/analyze_georef_excel.py): script CLI per sola analisi
- [geocode_valid_addresses_osm.py](/Users/spagnolo/github/PuliziaDatiSinergia/geocode_valid_addresses_osm.py): script CLI per geocoding
- [app_version.py](/Users/spagnolo/github/PuliziaDatiSinergia/app_version.py): nome e versione ufficiale dell'app

## Versione applicazione

La versione corrente è definita in:

- [app_version.py](/Users/spagnolo/github/PuliziaDatiSinergia/app_version.py)

Valori attuali:

- `APP_NAME = "Pulizia Dati Sinergia"`
- `APP_VERSION = "1.0.0"`

## Regola di manutenzione

Ogni volta che viene fatta una modifica distribuita della web app, aggiornare sempre `APP_VERSION`.

Questo serve a mantenere coerenti:

- la versione mostrata nell'interfaccia
- la versione registrata nel `job_manifest.json`
- la tracciabilità delle modifiche rilasciate

## Note operative

- Il geocoding usa Nominatim di OpenStreetMap.
- Per il geocoding reale è consigliato inserire un'email nel form.
- È disponibile anche la modalità `dry run`, che genera gli output senza chiamare il geocoder.
- Se il file contiene molti indirizzi, l'elaborazione può richiedere tempo a causa del rate limit del servizio.
