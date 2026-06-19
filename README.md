# Sysbar

Toolkit per la barra di sistema di Ubuntu/GNOME. Una sola applicazione nel
system tray che raggruppa sei utility: monitor di sistema, mixer del volume per
applicazione, keep awake, auto-quit, disinstallatore e shelf.

Tutto è locale: nessun account, nessuna telemetria. Ogni feature è disattivata
finché non la attivi e si degrada con un messaggio esplicito quando una
dipendenza di sistema non è disponibile.

## Stato

In sviluppo. Sono completi lo scaffolding e le fondamenta (configurazione
GSettings, rilevamento capability, logging, CLI di diagnostica). Le sei feature
vengono implementate a milestone successive (vedi `doc_progetto/`).

## Requisiti

- Ubuntu/GNOME su sessione X11 (alcune feature richiedono X11; su Wayland l'app
  si avvia e disattiva quelle non supportate)
- Python 3.11+
- Binding GTK di sistema: `python3-gi`, `gir1.2-gtk-4.0`, `gir1.2-adw-1`,
  `gir1.2-ayatanaappindicator3-0.1`, `gir1.2-wnck-3.0`
- `uv` per la gestione dell'ambiente Python
- `glib-compile-schemas` (pacchetto `libglib2.0-bin`) per compilare lo schema

Installazione dei binding di sistema su Ubuntu:

```bash
sudo apt install python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 \
  gir1.2-ayatanaappindicator3-0.1 gir1.2-wnck-3.0 libglib2.0-bin
```

## Sviluppo

L'ambiente Python riusa i binding GTK di sistema (`--system-site-packages`) e
installa solo le dipendenze pure-Python.

```bash
uv venv --system-site-packages --python /usr/bin/python3
uv sync
```

Il venv deve usare il Python di sistema (`/usr/bin/python3`): un interprete
gestito da uv non vedrebbe `python3-gi` installato a livello di sistema.

Compila lo schema GSettings e avvia la diagnostica:

```bash
./build.sh                 # compila schema e traduzioni in build/
uv run sysbar --version
uv run sysbar --selftest   # report delle capability rilevate
uv run sysbar --sensors    # dump letture sensori
```

Per avviare l'app con lo schema compilato:

```bash
./build.sh run -- --selftest
# oppure
GSETTINGS_SCHEMA_DIR=./build/schemas uv run sysbar
```

## Test

```bash
uv run pytest
```

I test coprono la logica pura (sanitizzazione configurazione, rilevamento
capability, formattazione log). I boundary di sistema (psutil, pulsectl, X11,
D-Bus) sono dietro interfacce e vengono mockati. La UI GTK non viene testata in
CI: è verificabile manualmente con `--selftest` su una sessione reale.

Lint e type check:

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy
```

## Configurazione

Tutta la configurazione runtime vive in GSettings, schema
`io.github.AndreaBonn.Sysbar`, path `/io/github/AndreaBonn/Sysbar/`. Le chiavi sono
documentate nello schema `data/io.github.AndreaBonn.Sysbar.gschema.xml`. Non sono richiesti secret
né variabili d'ambiente in produzione; `.env.example` elenca le sole variabili
di sviluppo.

## Struttura

```
src/sysbar/
  app/        ciclo di vita, tray, rendering metriche tray
  core/       config (GSettings), capabilities, costanti, errori, i18n, logging
  services/   logica framework-agnostica delle feature (ports + adapter)
  ui/         finestre GTK4: pannello, settings, onboarding, shelf
  support/    diagnostica (selftest, dump sensori)
tests/        mirror di src/sysbar/
data/         schema GSettings, file .desktop, autostart, icone, traduzioni
packaging/    .deb e repository APT
```

## Installazione (.deb)

### Per installare

Scarica il pacchetto `.deb` dall'ultima release
([github.com/AndreaBonn/sysbar/releases/latest](https://github.com/AndreaBonn/sysbar/releases/latest))
e installalo con `apt`, che risolve in automatico i binding GTK di sistema:

```bash
sudo apt install ./sysbar_<versione>_all.deb
```

Il pacchetto installa un venv isolato in `/opt/sysbar` (con
`--system-site-packages`, così riusa i binding GTK di sistema) e un wrapper
`/usr/bin/sysbar`. Avvia l'app dal menu applicazioni o con `sysbar`.

Per disinstallare:

```bash
sudo apt remove sysbar
```

### Build del pacchetto (maintainer)

Build da una macchina con `dpkg-dev` e `debhelper`:

```bash
./build.sh deb        # produce ../sysbar_<versione>_all.deb
```

Gli aggiornamenti passano da APT: vedi `packaging/apt-repo/README.md` per
configurare il repository firmato e installare con `apt`.

## Licenza

GPL-3.0-or-later.
