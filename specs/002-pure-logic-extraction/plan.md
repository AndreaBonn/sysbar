# Piano: logica pura fuori dai moduli omessi dalla coverage (sysbar)

Data: 2026-10-19. Base: `main` @ 7a8a88e, albero pulito.

## Obiettivo

Le decisioni con comportamento verificabile oggi sepolte in finestre GTK, moduli feature e
adapter D-Bus (esclusi dalla coverage) vivono in moduli puri misurati, coperte da test
comportamentali. Le finestre restano glue sottile. Nessun comportamento osservabile cambia,
nessun modulo omesso viene forzato in misura, nessuna estrazione esiste solo per alzare un numero.

## Approccio

Pattern già presente nel repo, da replicare, non da inventare:

- **`app/<superficie>_content.py`** (puro, misurato, importa `_` ma non GI): cosa una finestra
  mostra e decide. Precedenti: `uninstall_content.py`, `settings_content.py`,
  `onboarding_content.py`, `panel_summary.py`, `tray_state.py`.
- **Metodo sul servizio** quando la decisione appartiene al dominio del servizio (target-state di
  un toggle, testo trascinato su shelf), testato con il fake/reale già usato in `tests/services/`.
- **Modulo `services/<feature>/` senza GI** quando la logica è di un adapter di sistema
  (`portal.py`, `inhibitor.py`): il pezzo puro esce, il pezzo D-Bus resta in omit.

Criterio di taglio per ogni candidato (tabella "Guadagno/Costo" di code-standards):
estrai solo se c'è almeno una decisione con >= 2 esiti osservabili che un test può nominare
con valori concreti, e se il modulo di destinazione è coeso (cambia per lo stesso motivo).
Altrimenti "lascia" con la ragione.

Ogni sub-task = un commit `refactor(<scope>): ...` con test nello stesso commit,
comportamento invariato. Ordine dentro il task: (1) test del modulo puro scritti per primi,
rossi su import mancante; (2) estrazione; (3) verde; (4) prova di rottura: invertire a mano
una condizione del modulo estratto, vedere il test rosso, ripristinare; (5) la finestra o la
feature chiama il modulo; (6) smoke UI sotto xvfb verde.

Comandi (dal root del repo):

```
uv run pytest --ignore=tests/ui -q                       # unit
xvfb-run -a uv run pytest tests/ui -o addopts=""         # smoke + gate traduzioni (come CI)
uv run ruff check . && uv run mypy                       # lint + tipi strict
uv run pytest --ignore=tests/ui --cov=sysbar --cov-branch --cov-report=term-missing -q   # misura
```

Nota: `--cov-branch` non è in `pyproject.toml`. Il 99% branch della baseline si ottiene solo
passandolo a mano: baseline e misura finale usano lo stesso comando.

## Definition of Done

- [ ] Ogni sub-task T1-T18 è un commit su `main` locale, con `uv run pytest --ignore=tests/ui`,
      `xvfb-run -a uv run pytest tests/ui -o addopts=""`, `ruff` e `mypy` verdi dopo il commit.
- [ ] Ogni modulo o funzione nuova ha test in `tests/` a specchio, con valori concreti
      (Given/When/Then). Esempio: dato un `SystemSnapshot` con `net_rx_rate=None`, la riga
      `net_speed` di `metric_rows(...)` è `None` (riga nascosta); con rx=1024, tx=2048 è
      `"↓1.0 KB/s ↑2.0 KB/s"` (valore esatto da `metric_format`, non riscritto nel test).
- [ ] Ogni test nuovo è stato visto rosso (import mancante o rottura intenzionale) prima del verde.
- [ ] Line coverage resta 100% sul codice misurato; branch coverage (con `--cov-branch`) >= baseline,
      con i 3 parziali "reali" di T1 chiusi e i 5 restanti dichiarati irraggiungibili nel corpo del commit.
- [ ] Nessuna voce nuova in `[tool.coverage.run] omit`, nessuna in `_LONG_FUNCTION_ALLOWLIST`
      o `_WIDE_SIGNATURE_ALLOWLIST`. Le voci `portal.PortalGlobalShortcuts._create_session` e
      `parsers.parse_upower_devices` sono rimosse (il test ratchet lo esige quando smettono di violare).
- [ ] Il gate traduzioni esercita ogni ramo delle funzioni pure che emettono stringhe utente
      (T18); se emergono msgid assenti nel `.po` vengono aggiunti con traduzione italiana.
- [ ] Le stringhe `_()` spostate hanno msgid identici byte per byte (verificato con
      `grep -c` nel `.po` prima e dopo).
- [ ] Checklist runtime manuale (sezione Criteri di verifica) eseguita su sessione reale per le
      finestre toccate, esito per controllo registrato.

## Assunzioni

- Commit diretti su `main` locale come chiesto dall'utente; nessun push (git-workflow: push solo
  su richiesta esplicita). Se il ramo protetto lato remoto rifiuterà poi il push, si porta tutto
  su `chore/pure-logic-extraction` senza riscrivere i commit.
- `--cov-branch` resta un flag da riga di comando: attivarlo in `pyproject.toml` cambia il
  badge di CI ed è una decisione separata (vedi Fuori scope). Anchor incidentale, non vincolo.
- La regola CLAUDE.md "la logica in `services/` non importa GI" vale per i moduli nuovi.
  `shelf_service.py` e `keep_awake/manager.py` la violano già (GObject per i segnali): pre-esistente,
  non toccato.
- Il gate traduzioni registra a runtime (non scansiona il sorgente): spostare una chiamata `_()`
  in un modulo puro non cambia cosa registra, purché il ramo sia esercitato. Verificato in
  `tests/ui/test_translation_coverage.py:1-40`.
- I test UI saltano senza display: "suite verde" significa entrambi i comandi, non solo `uv run pytest`.

## Disambiguazione

- Opzione A: estrazione per superficie in moduli `*_content.py` / metodi di servizio, finestre invariate
  nella struttura → nessun cambio architetturale, glue resta in omit.
- Opzione B: convertire le finestre in MVP (presenter puro per finestra, view passiva) → copre di
  più ma riscrive ogni finestra e i suoi smoke test, presenter per finestre da 2 decisioni.
- Opzione C: togliere `ui/*` da omit e testare le finestre sotto xvfb in CI per la coverage
  → misura glue GTK, test che verificano widget e non comportamento.
- Raccomandata: **A**. È il pattern già consolidato nel repo (5 moduli `*_content`/`*_state`
  esistono), e il vincolo dell'utente esclude esplicitamente l'estrazione di glue per il numero.
  B è da rivalutare solo se una finestra supera 4-5 decisioni (oggi nessuna lo fa).

## Classificazione dei rami parziali della baseline

| Ramo | Natura | Esito |
|---|---|---|
| `app/commands/actions.py` 94->92 | `refresh_enabled` su mapping parziale: input lecito di una funzione pubblica (`application.py:82` inizializza `_actions = {}`) | **gap reale**, test in T2 |
| `services/scenes/apply.py` 105->107 | `match action.toggle` in `_apply_toggle` senza return: un `SystemToggle` nuovo passa e restituisce APPLIED senza aver fatto niente; mypy non lo vede | **gap di design**, `assert_never` in T1 |
| `services/scenes/summary.py` 42->35 | `match` dentro un loop senza return: un'azione nuova viene ignorata in silenzio | **gap di design**, T1 |
| `services/scenes/editing.py` 158->160 | `match` che assegna `choice, percent`: una condizione nuova dà `UnboundLocalError` | **gap di design**, T1 |
| `app/commands/models.py` 115->exit, `services/palette/models.py` 110->exit, `services/scenes/apply.py` 84->exit, `services/scenes/editing.py` 184->exit, `services/scenes/triggers.py` 182->exit | `match` esaustivo in funzione con return: mypy strict segnala già "Missing return" su una variante nuova | **irraggiungibile**, si lascia; aggiungere `case _` qui = righe in più a guadagno nullo |
| `services/scenes/engine.py` 97->exit | `_perform(None, clear=False)` è escluso da `decision.is_noop` in `update` (`engine.py:76`) | **irraggiungibile**, guardia difensiva su invariante cross-modulo, si lascia |

## Sub-task (10-30 min ciascuno)

T0. Baseline misurata - file: nessuno (output in scratchpad) - rischio: basso - stima 10 min
    verify: i 4 comandi sopra salvati in `scratchpad/baseline-*.log`; riga `TOTAL` con branch, conteggio test (1164), elenco parziali identico alla tabella | dip: - | par: ok | rollback: n/a

T1. `assert_never` sui 3 match non esaustivi per il type checker - file: `services/scenes/apply.py`, `services/scenes/summary.py`, `services/scenes/editing.py`, `pyproject.toml` (solo se serve la regola di esclusione) - rischio: basso - 20 min
    `case _: assert_never(x)` (da `typing`) nei 3 punti. Esclusione dalla coverage: prima prova senza nulla; se il ramo `case _` resta "missing", `# pragma: no cover` sulla sola riga `case _:` (esclude il blocco). Mai una regex larga su `case _:` in `pyproject.toml`: nasconderebbe wildcard con logica.
    verify: mypy rosso aggiungendo temporaneamente un membro a `SystemToggle` (errore su `apply.py`), revert, mypy verde; report con `--cov-branch` senza i 3 parziali; corpo del commit con la tabella dei 5 irraggiungibili | dip: T0 | par: ok | rollback: revert

T2. Test di `refresh_enabled` su mapping parziale e vuoto - file: `tests/app/commands/test_actions.py` (o il file esistente che copre `actions.py`) - rischio: basso - 10 min
    Given mapping con solo il comando A e stato in cui A è disponibile / When `refresh_enabled` / Then A abilitato, nessuna `KeyError`; mapping vuoto non solleva. Test-only, commit `test(commands): ...`.
    verify: 94->92 sparisce dal report branch; rottura: sostituire la guardia con `actions[command.id]` → test rosso | dip: T0 | par: ok | rollback: revert

T3. Righe metriche del pannello in `app/panel_rows.py` - file: nuovo `src/sysbar/app/panel_rows.py`, `ui/panel/metrics_section.py`, `ui/panel/panel_window.py`, nuovo `tests/app/test_panel_rows.py` - rischio: medio - 30 min
    Estrai: `metric_rows(snapshot, temperature_unit) -> dict[str, MetricRow(text, level)]` (la mappa riga->valore di `update_snapshot`, `_percent`, `_uptime`, `_temp`, potenza `"{:.0f} W"`), `clamp_level` (oggi in `_MetricRow.show`), `net_pair(rx, tx, rate)` condiviso fra riga `net_speed`/`net_total` e `update_net_processes` (oggi lo stesso formato "↓ ↑" è scritto due volte: cambiano insieme), `process_row_text(process) -> (title, subtitle)` con fallback `_("Unknown")`, `fan_subtitle(rpm)`.
    Lascia in UI: `_GROUPS`, `_LEVEL_ROWS`, `_ROW_SPARKLINE_METRIC` (layout), sparkline visibility (2 righe), `_title_widget` (dipende da display).
    Destinazione separata da `panel_summary.py` (che risponde a "la macchina sta bene?"), importa da lì `memory_text`/`battery_text`.
    verify: test con snapshot tutto-None (tutte le righe None), tutto valorizzato (testi esatti), level 130 → 100 e -5 → 0, process con nome vuoto → titolo `Unknown`; smoke `test_panel_window_builds`, `test_panel_window_net_processes_update` verdi | dip: T0 | par: ok | rollback: revert

T4. Decisioni della palette in `app/palette_content.py` - file: nuovo `src/sysbar/app/palette_content.py`, `ui/palette/palette_window.py`, nuovo `tests/app/test_palette_content.py` - rischio: medio - 30 min
    Estrai: `run_decision(entry) -> RunDecision {RUN, FIX, IGNORE}` (oggi `_run`: runnable → esegui e chiudi; non runnable con `fix_label` → applica fix; altrimenti niente; la decisione si prende da `is_runnable`/`fix_label` senza invocare, l'invocazione resta alla finestra: `activate()` torna True sse `Runnable`, equivalenza verificata su `services/palette/models.py:104`), `section_title(kind_value, previous_kind_value) -> str | None` (oggi `_section_header`, lavora sui nomi di riga per il motivo scritto nel commento: va preservato), `row_presentation(entry) -> RowPresentation(subtitle, activatable, dimmed, show_reveal, show_fix)`, `empty_state(query) -> (title, description)`. Le tabelle `_KIND_ICONS`/`_KIND_TITLES` seguono la funzione che le usa.
    Lascia: `_move_selection` (aritmetica già pura in `services/palette/matcher.next_index`), `_dismiss` (guardia di idempotenza legata a `notify::is-active`), `_key_hint`.
    verify: test per i 3 esiti di `run_decision`, header: stesso kind del precedente → None, kind sconosciuto → None, primo della lista → titolo; `dimmed` vero solo se non runnable e senza fix; smoke palette (3 test) verdi; runtime: Enter su voce con fix applica il fix | dip: T0 | par: ok | rollback: revert

T5. Scelte dei dispositivi audio in `app/device_choices.py` - file: nuovo `src/sysbar/app/device_choices.py`, `ui/panel/device_section.py`, nuovo `tests/app/test_device_choices.py` - rischio: medio - 20 min
    Estrai: `default_choices(devices) -> DeviceChoices(labels, names, selected: int | None)` (oggi `DeviceSection._fill`: indice del device di default, None se lista vuota) e `name_at(choices, index) -> str | None` (bounds check di `_on_output/_input_selected`). Secondo consumatore in T6 (`scene_output_choices`), quindi il modulo non è speculativo.
    verify: nessun default → indice 0; default al terzo posto → 2; lista vuota → `selected is None`; indice fuori range → None; smoke `test_device_section_binds_and_populates` verde | dip: T0 | par: ok | rollback: revert

T6. Form dell'editor scene in `app/scenes_content.py` - file: nuovo `src/sysbar/app/scenes_content.py`, `src/sysbar/app/device_choices.py`, `ui/scenes/scene_editor.py`, nuovo `tests/app/test_scenes_content.py` - rischio: alto - 30 min
    Estrai: una tabella sola per le scelte trigger (oggi `_TRIGGER_CHOICES` e le etichette di `_trigger_model` sono due tuple parallele in punti diversi: un riordino di una sola rompe la mappatura in silenzio), `TOGGLE_CHOICES` con etichette, `trigger_rows_visibility(choice) -> (percent_visible, restore_visible)`, `scene_output_choices(devices, selected_name)` in `device_choices.py` (prima voce "Leave unchanged"), `form_draft(values: FormValues, base: Scene) -> SceneDraft` (nome strip con fallback al nome base, toggle a None filtrati, indice device fuori range → "", `preserved` dalla base). `FormValues` dataclass frozen: la firma resta entro 4 parametri.
    Lascia: `_save` (uuid4 + controller), costruzione widget.
    verify: test su ogni scelta trigger, nome vuoto/spazi → nome base, device selezionato non più collegato → indice 0; test che `len(labels) == len(choices)` per entrambe le tabelle; smoke `test_editing_a_preset_saves_it_without_losing_actions` e `test_scenes_window_opens_the_editor_for_a_new_scene` verdi | dip: T5 | par: seq (tocca `device_choices.py`) | rollback: revert

T7. Righe della lista scene - file: `src/sysbar/app/scenes_content.py`, `ui/scenes/scenes_window.py`, `tests/app/test_scenes_content.py` - rischio: basso - 15 min
    Estrai: `removal_kind(scene) -> RemovalKind | None` (built-in non modificato → None; preset modificato → RESTORE; scena utente → DELETE) con icona/tooltip associati, `device_descriptions(outputs) -> dict[str, str]` (solo device con descrizione).
    Lascia: `_build_state_widget` (un `if` su active_id che sceglie fra due widget), navigazione stack.
    verify: 3 casi di `removal_kind` con scene reali da `PRESET_SCENES`; smoke `test_scenes_window_lists_every_scene`, `test_activating_a_scene_from_the_list_marks_it_active` verdi | dip: T6 | par: seq (stesso modulo e test) | rollback: revert

T8. Messaggi e disponibilità della feature scene - file: `services/scenes/summary.py`, `services/scenes/adapters.py`, `app/features/scenes.py`, `tests/services/scenes/test_scene_summary.py`, `tests/services/scenes/test_scene_adapters.py` - rischio: basso - 20 min
    Estrai: `partial_note(outcomes, scene_name) -> str` (oggi `_partial_note`: vuoto se nessun esito o tutti applicati, altrimenti "{applied} of {total}..."), `trigger_announcement(scene_name, outcomes) -> str` (nota parziale oppure "A trigger switched to {scene}."), `toggle_supported(toggle, *, dnd_available, mic_available) -> bool` (oggi `SceneDrivers._supports`, prende booleani per non importare `app/` da `services/`). `summary.py` è già il modulo "scene descritte per l'utente".
    Lascia: `trigger_for`/`save_trigger` (lookup di 2 righe sullo store, spostarli creerebbe la dipendenza `store -> editing` per `rule_id_for`), `TriggerState` rimpiazzato campo per campo (equivale a `dataclasses.replace`), `toggle_focus` (un `if`), `_set_output` (appartenenza a un set).
    verify: outcomes vuoti → "", 3/3 → "", 1/3 → testo con 1 e 3; KEEP_AWAKE sempre supportato, DND segue `dnd_available`; avvio app reale: scena con microfono assente notifica "1 of 2" | dip: T1 (stesso `summary.py`) | par: seq | rollback: revert

T9. Undo del "Svuota" della shelf in `services/shelf/pending_clear.py` - file: nuovo `src/sysbar/services/shelf/pending_clear.py`, `services/shelf/shelf_service.py`, `ui/shelf/shelf_window.py`, nuovo `tests/services/shelf/test_pending_clear.py`, `tests/services/shelf/test_shelf_service.py` - rischio: medio - 30 min
    Estrai: `PendingClear(service)` con `clear() -> bool` (committa l'eventuale pendente, stacca tutto, False se non c'era niente), `undo()`, `commit()`; testato con `ShelfService(tmp_path)` reale (preferire il reale al fake). Più `ShelfService.add_dropped_text(value)` che sceglie URL o testo (`_URL_SCHEMES` si sposta con lei): la classificazione appartiene al servizio.
    Lascia: `_on_drop` (dispatch su tipi Gdk), `_make_prepare`/`_open_item` (decisioni da 2 `if` legate a `Gio.File.get_uri` e ai launcher GTK: estrarle con `Path.as_uri` cambierebbe l'escaping dell'URI, cioè il comportamento).
    verify: clear su shelf vuota → False e nessun toast; clear, undo → elementi ripristinati; clear, clear → il primo lotto è scartato davvero (file in staging rimossi); clear, commit, undo → no-op; `"https://x"` → URL, `"httpx"` → testo; smoke `test_shelf_window_builds` verde; runtime: Svuota → Annulla ripristina le tile | dip: T0 | par: ok | rollback: revert

T10. Uninstaller: target, sottotitolo residui, esito rimozione - file: `services/uninstall/identifier.py`, `app/uninstall_content.py`, `ui/uninstall/uninstaller_window.py`, `tests/services/uninstall/test_identifier.py`, `tests/app/test_uninstall_content.py` - rischio: medio - 25 min
    Estrai: `target_from_app(name, desktop_id, exec_path, query) -> AppTarget` in `identifier.py` accanto a `identify` (suffisso `.desktop` tolto, id vuoto → None; `shutil.which` resta nella finestra e passa `exec_path`). Se servono più di 4 parametri, `desktop_id`/`exec_path` keyword-only. In `uninstall_content.py`: `leftover_subtitle(leftover, *, home)` e `removal_message(result) -> str` (con o senza falliti).
    Lascia: `_fill_app_list` (icona di fallback), `_selected`/`_update_summary` (già delegati a `removal_summary`).
    verify: `"org.gnome.Foo.desktop"` → `"org.gnome.Foo"`, `""` → None, nessun exec → `exec_path=None`; `removal_message` con 0 e 2 falliti; smoke `test_uninstaller_window_builds`, `test_uninstaller_scans_nothing_until_an_app_is_chosen` verdi | dip: T0 | par: ok | rollback: revert

T11. Interruttore degli avvisi - file: `app/settings_content.py`, `ui/settings/alerts_page.py`, `tests/app/test_settings_content.py` - rischio: basso - 15 min
    Estrai: `threshold_on_switch(spec, *, enabled, current) -> int | None` (acceso con soglia <= 0 → `spec.suggested`; spento con soglia > 0 → 0; altrimenti None = nessuna scrittura). È la codifica "0 = spento" della soglia, oggi visibile solo nella pagina.
    Lascia: `_on_changed` (filtro su due chiavi), `widgets.py` (`ComboBinding._current_index` è `list.index` con fallback 0; `_write_spin` è una guardia anti-eco di una riga).
    verify: 4 combinazioni enabled × current; smoke `test_settings_window_builds` verde; runtime: attivare un avviso a 0 lo porta al suggerito | dip: T0 | par: ok | rollback: revert

T12. Target-state dei toggle sui servizi - file: `services/quick_toggles/microphone.py`, `services/quick_toggles/desktop_toggles.py`, `app/features/toggles.py`, `tests/services/quick_toggles/test_microphone.py`, `tests/services/quick_toggles/test_desktop_toggles.py` - rischio: basso - 15 min
    Estrai: `MicrophoneToggle.set_muted(muted)` e `DoNotDisturbToggle.set_active(active)` (porta allo stato voluto, no-op se già lì; oggi in `TogglesFeature.set_microphone_muted`/`set_do_not_disturb`). La feature delega e tiene solo il null-check dell'interfaccia totale.
    Lascia: `state()` (mappa di null-check, è l'interfaccia totale voluta da CLAUDE.md), `toggle_*`.
    verify: con backend fake: muted=True su già mutato → nessun toggle registrato; su non mutato → un toggle; idem DND | dip: T0 | par: ok | rollback: revert

T13. Stato del tray: menu live ed etichetta - file: `app/tray_state.py`, `app/tray_controller.py`, `tests/app/test_tray_state.py` - rischio: basso - 15 min
    Estrai: `menu_has_live_content(config, *, toggles_available) -> bool` (oggi in `_on_menu_about_to_show`: decide se l'host rilegge il layout, cioè il churn D-Bus) e `tray_label(segments) -> str` (filtra i vuoti, unisce con " · ").
    Lascia: `register`, `refresh_*`, `_build_menu` (composizione di valori già puri).
    verify: nessuna metrica, nessun toggle, nessuna batteria periferica → False; uno qualsiasi dei tre → True; `tray_label(("", "CPU 5%"))` → `"CPU 5%"` | dip: T0 | par: ok | rollback: revert

T14. Portale scorciatoie: percorso della Request e risposta di sessione - file: nuovo `src/sysbar/services/hotkey/portal_protocol.py`, `services/hotkey/portal.py`, `tests/test_source_limits.py`, nuovo `tests/services/hotkey/test_portal_protocol.py` - rischio: medio - 20 min
    Estrai: `request_path(unique_name, handle_token) -> str` (derivazione fissata dalla spec del portale: `:1.42` → `.../request/1_42/<token>`) e `session_handle_from(response_code, results) -> str | None`. `_create_session` scende sotto 30 righe: rimuovere la voce da `_LONG_FUNCTION_ALLOWLIST` (il quarto test del ratchet lo impone).
    Lascia: la macchina bind/pending/requested (due flag e una lista, un solo consumatore: una classe in più sarebbe indirezione), tutto ciò che costruisce `GLib.Variant`.
    verify: `request_path(":1.42", "sysbar_shortcuts")` == `"/org/freedesktop/portal/desktop/request/1_42/sysbar_shortcuts"`; codice 1 → None; codice 0 senza `session_handle` → None; `tests/test_source_limits.py` verde senza la voce | dip: T0 | par: contratto su `tests/test_source_limits.py` con T15 → seq | rollback: revert

T15. `parse_upower_devices` sotto 30 righe - file: `services/system_monitor/parsers.py`, `tests/test_source_limits.py` - rischio: basso - 10 min
    Estrai il predicato `_is_reportable(props) -> bool` (non alimentatore, presente, percentuale > 0: il concetto "periferica con una lettura vera" del docstring). Già misurato e coperto: i test esistenti di `parse_upower_devices` sono la caratterizzazione. Rimuovere la voce dall'allowlist.
    verify: test esistenti verdi; rottura: `percent < 0.0` al posto di `<= 0.0` → test rosso; voce rimossa e ratchet verde | dip: T14 | par: seq (stesso file di test) | rollback: revert

T16. Inibitore combinato logind + ScreenSaver - file: nuovo `src/sysbar/services/keep_awake/combined_inhibitor.py`, `services/keep_awake/inhibitor.py`, `services/keep_awake/ports.py`, `app/features/keep_awake.py`, nuovo `tests/services/keep_awake/test_combined_inhibitor.py` - rischio: medio - 30 min
    Estrai: `CombinedInhibitor(sleep, screensaver)` con la logica oggi in `SystemInhibitor.acquire/release`: ScreenSaver solo per `WHAT_IDLE_SLEEP`, token None se falliscono entrambi, rilascio di ciascuna parte presente. `inhibitor.py` resta in omit con due adapter D-Bus dietro due `Protocol` stretti in `ports.py` (DI per isolare l'I/O: bisogno presente, non speculativo). La feature costruisce `CombinedInhibitor(LogindSleepInhibitor(), ScreenSaverInhibitor())`.
    Lascia: chiamate D-Bus, cache dei bus.
    verify: fake: idle-sleep → entrambi acquisiti, rilascio chiude fd e uninhibit cookie; "handle-lid-switch" → ScreenSaver mai chiamato; entrambi falliscono → None; solo cookie → token valido e rilascio non tocca fd; runtime: keep-awake attivo, `systemd-inhibit --list` mostra Sysbar | dip: T0 | par: ok | rollback: revert

T17. Stato vuoto della cronologia appunti (Could) - file: nuovo `src/sysbar/app/clipboard_content.py`, `ui/clipboard/clipboard_window.py`, nuovo `tests/app/test_clipboard_content.py` - rischio: basso - 15 min
    Estrai: `empty_state(query) -> (title, description)` (ricerca senza risultati vs primo uso, requisito C1) e `pin_presentation(pinned) -> (icon, tooltip)`. Si fa solo se il budget regge: il guadagno è soprattutto nel gate traduzioni di T18.
    Lascia: `_on_clear` (confronto di lunghezze; la semantica di undo sta nel servizio).
    verify: query vuota → "Nothing copied yet"; query "x" → "No entries match"; smoke `test_clipboard_window_builds` verde | dip: T0 | par: ok | rollback: revert

T18. Gate traduzioni sui rami dei moduli puri - file: `tests/ui/test_translation_coverage.py`, eventualmente `data/locale/it/LC_MESSAGES/sysbar.po` - rischio: medio - 20 min
    Una funzione `_exercise_content()` che chiama ogni ramo che emette stringhe di `panel_rows`, `palette_content`, `scenes_content`, `summary.partial_note/trigger_announcement`, `uninstall_content.removal_message`, `clipboard_content` (se T17 fatto). Oggi rami come "Nothing matches “{query}”" e "{applied} of {total} actions…" non sono garantiti esercitati dal gate. Ogni msgid mancante che emerge si aggiunge al `.po` con traduzione, in commit separato `fix(i18n): ...`.
    verify: `xvfb-run -a uv run pytest tests/ui -o addopts=""` verde; elenco dei msgid aggiunti nel corpo del commit | dip: T3, T4, T6, T7, T8, T10, T17 | par: seq | rollback: revert (il `.po` è solo additivo)

T19. Misura finale e checklist runtime - file: nessuno - rischio: basso - 20 min
    verify: i 4 comandi della baseline, diff con `baseline-*.log`: test > 1164, line 100%, branch >= baseline, parziali solo i 5 irraggiungibili; `grep -c` delle allowlist; checklist runtime eseguita | dip: tutti | par: seq | rollback: n/a

Stima: 6,5-8,5 h di lavoro + 20% di buffer (refactor di codice esistente, smoke deboli) = 8-10 h.
Must: T0-T8, T10, T14, T15, T18, T19. Should: T9, T11, T12, T13, T16. Could: T17.

## Fuori scope (moduli omessi lasciati, con motivo)

- `ui/onboarding/onboarding_window.py`: la logica è già in `app/onboarding_content.py`; resta un `join` con fallback.
- `ui/panel/overview_section.py`: un confronto di id per decidere il rebuild e un toggle di classe CSS.
- `ui/panel/mixer_section.py`: sincronizzazione per chiave di 8 righe; estrarla produce un diff generico con un consumatore, e il fallimento (riga orfana) si vede nello smoke.
- `ui/panel/sparkline.py`, `ui/settings/settings_window.py`, `features_page.py`, `monitor_page.py`, `ui/onboarding/whats_new_window.py`: <= 7 nodi, costruzione widget e binding GSettings.
- `ui/settings/widgets.py`: `list.index` con fallback e guardia anti-eco; un test misurerebbe la stdlib.
- `app/application.py`: il routing per prefisso di `_on_settings_changed` è la convenzione "due righe per feature" di CLAUDE.md; spostarlo in una tabella cambia la regola di non-ricrescita.
- `app/features/audio.py`, `clipboard.py`, `shelf.py` (reconcile), `keep_awake.py` (countdown), `panel.py`, `monitor.py`, `palette.py`, `hotkeys.py`, `onboarding.py`, `updates.py`, `uninstaller.py`, `auto_quit.py`, `trigger_sources.py`: null-check dell'interfaccia totale e reconcile vuole/ha con effetti GLib; la decisione è un `and` di due booleani, il rischio sta nell'effetto.
- `app/tray/status_notifier.py`, `app/tray/tray.py`: tabella di proprietà SNI e vtable GIO; un test riscriverebbe la tabella. Le firme larghe in allowlist sono imposte da GIO.
- `app/tray_controller.py` oltre T13, `app/remote.py`: composizione di valori già puri, client D-Bus.
- `services/notifier.py`, `services/quick_toggles/adapters.py`, `services/auto_quit/shell_extension_source.py`, `services/clipboard/monitor.py`: adapter di confine puri I/O.
- `app/tray/menu_builder.py::build_menu_items` (allowlist): il corpo è di 15 righe, la lunghezza viene dal docstring NumPy; spezzare la funzione per il conteggio sarebbe forzare. Nota a margine, non corretta qui: il docstring documenta 4 degli 8 parametri.
- `--cov-branch` in `pyproject.toml` e una soglia `fail_under`: cambiano il badge e la CI, decisione dell'utente da proporre a fine lavoro.
- Finding non correttivi emersi in research, da riportare e non toccare: `inhibitor.py:99` ingoia `GLib.Error` dell'inhibit ScreenSaver senza log (silent failure); `ShelfItem.open_uri` e `ShelfWindow._open_item` decidono due volte cosa è apribile.

## File impattati

| File | Tipo | Scopo |
|---|---|---|
| `src/sysbar/app/panel_rows.py` | nuovo | righe metriche, processi, ventole |
| `src/sysbar/app/palette_content.py` | nuovo | decisioni della palette |
| `src/sysbar/app/device_choices.py` | nuovo | dispositivi audio come scelte di combo |
| `src/sysbar/app/scenes_content.py` | nuovo | form e lista scene |
| `src/sysbar/app/clipboard_content.py` | nuovo (Could) | stato vuoto appunti |
| `src/sysbar/services/shelf/pending_clear.py` | nuovo | undo dello svuotamento |
| `src/sysbar/services/hotkey/portal_protocol.py` | nuovo | path Request e risposta sessione |
| `src/sysbar/services/keep_awake/combined_inhibitor.py` | nuovo | composizione delle inibizioni |
| `services/scenes/{apply,summary,editing,adapters}.py` | modifica | assert_never, messaggi, disponibilità toggle |
| `services/shelf/shelf_service.py`, `services/uninstall/identifier.py`, `services/quick_toggles/{microphone,desktop_toggles}.py`, `services/keep_awake/{inhibitor,ports}.py`, `services/system_monitor/parsers.py`, `services/hotkey/portal.py` | modifica | metodi/predicati estratti |
| `app/{settings_content,uninstall_content,tray_state,tray_controller}.py`, `app/features/{scenes,toggles,keep_awake}.py` | modifica | funzioni estratte e deleghe |
| `ui/panel/{metrics_section,panel_window,device_section}.py`, `ui/palette/palette_window.py`, `ui/scenes/{scene_editor,scenes_window}.py`, `ui/shelf/shelf_window.py`, `ui/uninstall/uninstaller_window.py`, `ui/settings/alerts_page.py`, `ui/clipboard/clipboard_window.py` | modifica | chiamano i moduli puri |
| `tests/app/test_{panel_rows,palette_content,device_choices,scenes_content,clipboard_content}.py`, `tests/services/...` | nuovo/modifica | test comportamentali |
| `tests/test_source_limits.py` | modifica | rimozione 2 voci allowlist |
| `tests/ui/test_translation_coverage.py`, `data/locale/it/LC_MESSAGES/sysbar.po` | modifica | gate sui rami nuovi |
| `pyproject.toml` | modifica solo se T1 lo richiede | nessuna regola larga |

## Rischi e mitigazioni

1. **Msgid alterati o mai esercitati.** Poiché il gate registra solo le stringhe che passano a runtime (causa), una `_()` spostata con un carattere diverso (virgolette tipografiche “ ”, ellissi …) o un ramo mai esercitato può perdere la traduzione italiana senza che nessun test fallisca (rischio), e l'utente vede testo inglese in una UI dichiarata "fully Italian" (effetto, +0,5-1 h di caccia se scoperto tardi). Mitigazione: copia verbatim, `grep -c` sul `.po` prima e dopo ogni task, T18 esercita tutti i rami.
2. **Smoke test deboli come unica rete sul glue.** Poiché gli smoke costruiscono le finestre ma non azionano combo, tasti e toast (causa), un off-by-one nella mappatura indice↔valore (T5, T6) o una decisione collegata al ramo sbagliato (T4, T9) passa sia gli unit sia gli smoke (rischio), e si scopre solo in uso (effetto: regressione silenziosa su scene salvate con il device sbagliato). Mitigazione: test sulle tabelle parallele (`len(labels) == len(choices)`), prova di rottura per ogni test, checklist runtime di T19 con esito per controllo.
3. **Esclusione dalla coverage troppo larga in T1.** Poiché coverage.py segnala parziale il fall-through dei `match` esaustivi (causa), la tentazione è una regex su `case _:` in `exclude_lines` (rischio), che nasconderebbe anche i wildcard con logica e farebbe salire il branch coverage per finzione (effetto: metrica non più credibile, il contrario dell'obiettivo). Mitigazione: niente regex generiche, pragma riga per riga solo sui 3 `assert_never`, report prima/dopo con lo stesso comando.
4. Gate dimensionale sui moduli nuovi: `form_draft` e `target_from_app` hanno molti input → `FormValues` dataclass e parametri keyword-only; `test_source_limits.py` lo verifica a ogni commit.
5. Cambio di comportamento nascosto in un refactor "invariato" (es. `run_decision` che non invoca più `activate()`): ogni equivalenza dichiarata cita la riga che la prova (`services/palette/models.py:104`); dove l'equivalenza non è dimostrabile (URI della shelf) si lascia.

## Criteri di verifica

- Dopo ogni commit: i due comandi pytest, `ruff`, `mypy` verdi.
- Fine piano: confronto `baseline-*.log` vs finale con lo stesso comando `--cov-branch`; parziali residui = esattamente i 5 classificati irraggiungibili.
- Checklist runtime su sessione GNOME reale (esito per voce): palette (frecce, Enter su voce eseguibile, Enter su voce con fix, Esc, perdita focus); editor scene (nuova scena, modifica preset, scelta "Battery drops below" mostra la percentuale, device scollegato torna a "Leave unchanged"); shelf (Svuota → Annulla, Svuota → attesa → elementi spariti); uninstaller (scelta app, sottotitoli residui, esito); avvisi (accensione di un avviso a 0); keep-awake (`systemd-inhibit --list`); tray (etichetta con countdown e metriche).
- Handoff: `tdd-guide` per T1-T18 (test-first su piano già ragionato, delegabile con `[DELEGATE-CODEX]` in blocchi da 2-4 task e `SCOPE:` dei file della tabella); `code-reviewer` a fine blocco; `a11y-gate` N/A (nessun cambio di render atteso), click-through della checklist sì.
