# Sysbar, convenzioni di progetto

Tray app per Ubuntu/GNOME. Python 3.11+, GTK4 e libadwaita di sistema via PyGObject,
architettura ports-and-adapters. Questo file raccoglie le regole che non si deducono
leggendo il codice. Le decisioni con la loro motivazione stanno in
`docs/DESIGN_DECISIONS.md`.

## Ambiente

Il venv usa `--system-site-packages` e riusa `python3-gi` e GTK4 della distribuzione: un
interprete gestito da uv non vedrebbe i typelib GI di sistema. In `pyproject.toml` vanno
solo dipendenze pure-Python.

```bash
uv sync
uv run pytest                       # suite completa
xvfb-run -a uv run pytest -m ui     # smoke finestre e gate traduzioni
uv run ruff check . && uv run mypy  # lint e tipi, mypy in strict
```

## Struttura

```
src/sysbar/
  app/            composizione: application.py, tray_controller.py, windows.py, context.py
  app/features/   una feature per modulo, wiring e capability gating
  app/tray/       protocollo tray (StatusNotifierItem, dbusmenu)
  core/           config GSettings, capability, i18n, logging, validazione
  services/       logica di feature framework-agnostica (ports + adapters)
  ui/             finestre GTK4
  support/        diagnostica (selftest, dump sensori)
tests/            mirror di src/sysbar
specs/<slug>/     piano, scomposizione e checklist runtime del lavoro in corso
```

## Regola di non-ricrescita di `application.py`

`app/application.py` era arrivato a 862 righe perché ogni feature vi aggiungeva un attributo
nullable e i suoi handler, e ogni chiamante pagava un `if ... is not None`.

**Una feature nuova costa un modulo in `app/features/` più due righe in `application.py`**:
la costruzione in `_build_features` e, se serve, una riga di routing in
`_on_settings_changed`. Se ne servono tre, il confine è nel posto sbagliato.

Corollario, **interfaccia totale**: un modulo feature tiene i propri `| None` all'interno e
non li restituisce mai. Se il backend manca, `state()` risponde comunque con un valore e
`toggle()` non fa nulla. Il degrado resta esplicito all'utente ma smette di essere
un'informazione che viaggia fino ai chiamanti.

Il gate è eseguibile, non è una convenzione: `tests/test_source_limits.py` fa fallire la CI
oltre 300 righe per file, 30 per funzione, 4 parametri posizionali. Le violazioni
pre-esistenti sono congelate in due allowlist, e un quarto test rimuove dal congelamento
ciò che ha smesso di violare. Non aggiungere voci: estrai un helper.

## Dove mettere i dati

- **Scalari** in GSettings (`data/io.github.AndreaBonn.Sysbar.gschema.xml`), letti solo
  tramite il wrapper tipato `core/config.py`, che sanitizza le chiavi vincolate con le
  funzioni `sanitized_*` di `core/validation.py`. Mai `Gio.Settings` diretto altrove.
- **Dati strutturati** in un manifest JSON sotto `~/.local/share/sysbar/<feature>/`, con il
  pattern di `services/shelf/shelf_service.py`: `load()` e `save()`, segnale
  `items-changed`, `from_dict` che solleva su dato corrotto e `load()` che degrada
  all'insieme vuoto con `log.warning`.

## Vincoli che rompono la CI se ignorati

- **Invariante dbusmenu**: il conteggio dei nodi del menu non deve cambiare tra un update e
  l'altro, altrimenti l'host ricicla gli id per posizione e lo stato si desincronizza. Le
  voci non pertinenti si emettono con `visible=False`, non si rimuovono. Per contenuti a
  cardinalità variabile serve un pool fisso di slot, come `MAX_PERIPHERAL_ROWS`.
- **Gate traduzioni**: ogni stringa che passa da `_()` deve avere un msgid in
  `data/locale/it/LC_MESSAGES/sysbar.po`, e ogni finestra nuova va aggiunta a
  `_exercise_windows` in `tests/ui/test_translation_coverage.py`. Non passare da `_()` testo
  scritto dall'utente: finirebbe nel catalogo.
- **Coverage**: ogni modulo nuovo o è testato, o sta in `[tool.coverage.run] omit` con un
  commento che dice perché. La logica pura non si mette in omit: si estrae e si testa.

## Convenzioni di codice

- Import GI sempre dopo `gi.require_version`, con `# noqa: E402`.
- Ogni boundary di sistema dietro un `Protocol` in `ports.py`, adapter concreto separato,
  fake nei test. La logica in `services/` non importa GI.
- Nessun magic value inline: tutto in `core/constants.py`.
- Docstring in formato NumPy sulle funzioni non banali; i commenti spiegano il perché.
- Test comportamentali con valori concreti, mai `assert x is not None`. Un bug corretto
  porta con sé il test di regressione.
- Commit in Conventional Commits, senza attribuzione AI. Push solo su richiesta esplicita.
