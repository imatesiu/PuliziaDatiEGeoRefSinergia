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

## Avvio con Docker

La configurazione Docker è predisposta per HTTPS usando:

- [tls/fullchain.pem](/Users/spagnolo/github/PuliziaDatiSinergia/tls/fullchain.pem)
- [tls/privkey.pem](/Users/spagnolo/github/PuliziaDatiSinergia/tls/privkey.pem)

Di default il container cerca i certificati nella cartella `tls` del progetto, tramite questi path interni:

- `/app/tls/fullchain.pem`
- `/app/tls/privkey.pem`

### Avvio rapido con script

```bash
./run_docker.sh
```

Lo script:

- rimuove un eventuale container precedente con lo stesso nome
- esegue la build dell'immagine Docker aggiornata
- avvia il container HTTPS sulla porta esterna `9382`
- monta `/etc/letsencrypt` dal server host in sola lettura
- usa in produzione i certificati in `/etc/letsencrypt/live/rtapp.isti.cnr.it/`

Nota importante:

- lo script monta l'intera cartella `/etc/letsencrypt` e non solo `live/rtapp.isti.cnr.it/`
- questo serve perché `fullchain.pem` e `privkey.pem` in `live/` sono spesso link simbolici verso `archive/`
- montare solo la cartella `live/...` potrebbe rompere la risoluzione dei link

### Build immagine

```bash
docker build -t pulizia-dati-sinergia:1.3.0 .
```

### Avvio container

```bash
docker run --rm -p 9382:8443 --name pulizia-dati-sinergia pulizia-dati-sinergia:1.3.0
```

Poi apri nel browser:

```text
https://127.0.0.1:9382
```

### Avvio con Docker Compose

```bash
docker compose up --build
```

Anche in questo caso l'app sarà disponibile su:

```text
https://127.0.0.1:9382
```

### Configurazione TLS nel container

Il container avvia Gunicorn in HTTPS usando queste variabili:

- `TLS_ENABLED=true`
- `TLS_CERT_FILE=/app/tls/fullchain.pem`
- `TLS_KEY_FILE=/app/tls/privkey.pem`
- `PORT=8443`

Se i file TLS non sono presenti, il container termina con errore esplicito.

## File principali

- [app.py](/Users/spagnolo/github/PuliziaDatiSinergia/app.py): entrypoint Flask della web app
- [templates/index.html](/Users/spagnolo/github/PuliziaDatiSinergia/templates/index.html): interfaccia di upload
- [georef_pipeline.py](/Users/spagnolo/github/PuliziaDatiSinergia/georef_pipeline.py): logica condivisa di analisi e geocoding
- [analyze_georef_excel.py](/Users/spagnolo/github/PuliziaDatiSinergia/analyze_georef_excel.py): script CLI per sola analisi
- [geocode_valid_addresses_osm.py](/Users/spagnolo/github/PuliziaDatiSinergia/geocode_valid_addresses_osm.py): script CLI per geocoding
- [app_version.py](/Users/spagnolo/github/PuliziaDatiSinergia/app_version.py): nome e versione ufficiale dell'app
- [requirements.txt](/Users/spagnolo/github/PuliziaDatiSinergia/requirements.txt): dipendenze Python
- [Dockerfile](/Users/spagnolo/github/PuliziaDatiSinergia/Dockerfile): immagine Docker della web app
- [docker-entrypoint.sh](/Users/spagnolo/github/PuliziaDatiSinergia/docker-entrypoint.sh): avvio Gunicorn con TLS
- [docker-compose.yml](/Users/spagnolo/github/PuliziaDatiSinergia/docker-compose.yml): avvio rapido containerizzato
- [run_docker.sh](/Users/spagnolo/github/PuliziaDatiSinergia/run_docker.sh): build e avvio rapido del container Docker
- [.dockerignore](/Users/spagnolo/github/PuliziaDatiSinergia/.dockerignore): esclusioni dal contesto Docker
- [tls/fullchain.pem](/Users/spagnolo/github/PuliziaDatiSinergia/tls/fullchain.pem): certificato TLS usato dal container
- [tls/privkey.pem](/Users/spagnolo/github/PuliziaDatiSinergia/tls/privkey.pem): chiave privata TLS usata dal container

## Versione applicazione

La versione corrente è definita in:

- [app_version.py](/Users/spagnolo/github/PuliziaDatiSinergia/app_version.py)

Valori attuali:

- `APP_NAME = "Pulizia Dati Sinergia"`
- `APP_VERSION = "1.3.0"`

## Regola di manutenzione

Ogni volta che viene fatta una modifica distribuita della web app, aggiornare sempre `APP_VERSION`.

Questo serve a mantenere coerenti:

- la versione mostrata nell'interfaccia
- la versione registrata nel `job_manifest.json`
- la tracciabilità delle modifiche rilasciate

## Note operative

- Il geocoding usa Nominatim di OpenStreetMap.
- Prima della ricerca OSM, la query viene ripulita da prefissi non utili come `LUOGO DETTO`, `LDT`, `LOC.` e `LOCALITÀ`.
- La home mostra lo stato del job, la percentuale di avanzamento e una stima del tempo rimanente fino alla generazione dello ZIP.
- Per il geocoding reale è consigliato inserire un'email nel form.
- È disponibile anche la modalità `dry run`, che genera gli output senza chiamare il geocoder.
- Se il file contiene molti indirizzi, l'elaborazione può richiedere tempo a causa del rate limit del servizio.
- Il container Docker deve avere accesso a internet per poter interrogare Nominatim durante il geocoding reale.
- Con certificati autofirmati o non riconosciuti dal sistema, il browser potrebbe mostrare un avviso HTTPS alla prima apertura.
- In produzione `run_docker.sh` usa i certificati LetsEncrypt presenti sotto `/etc/letsencrypt/live/rtapp.isti.cnr.it/`.
