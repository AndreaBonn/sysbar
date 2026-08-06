# Scomposizione: 001-app-wiring-actions-palette-scenes

Una riga per sub-task. `Dip.` elenca gli id da cui dipende. `DoD` traccia il criterio di
accettazione del piano che il task soddisfa.

Legenda tipo: `test` scritto per primo e rosso, `puro` modulo misurato dalla coverage,
`glue` modulo GI in `omit`, `ui` finestra, `dati` schema o manifest, `doc` documentazione.

## Blocco 0, split del wiring (branch `refactor/app-wiring`)

| Id | Task | Tipo | Min | Dip. | DoD |
|---|---|---|---|---|---|
| 0.1 | `tests/test_source_limits.py`: nessun file `src/**/*.py` oltre 300 righe, nessuna funzione oltre 30. Rosso su `application.py` | test | 40 | - | limiti dimensionali |
| 0.2 | Checklist di verifica runtime pre-split: elencare per iscritto ogni comportamento oggi funzionante, in `specs/001-.../runtime-checklist.md` | doc | 30 | - | refactor invariato |
| 0.3 | `app/context.py`: `AppContext` frozen (config, capabilities, notifier, autostart) più test | puro | 30 | 0.1 | limite di 4 parametri |
| 0.4 | `app/windows.py`: `WindowSlot` generico su Protocol `PresentableWindow`, open-or-present e azzeramento su close, più test con fake | glue | 45 | 0.3 | dedup 6 coppie open/close |
| 0.5 | Migrare panel, settings, shelf, clipboard, uninstaller e onboarding a `WindowSlot` | glue | 45 | 0.4 | refactor invariato |
| 0.6 | Pacchetto `app/features/` più voce `omit` in `pyproject.toml` con commento di motivazione | glue | 20 | 0.3 | ogni modulo testato o in omit |
| 0.7 | `app/tray_state.py`: funzioni pure stato-feature verso `QuickToggleState`, `SceneMenuEntry`, valori metrica, `TrayOptions`, più test | puro | 60 | 0.6 | guadagno coverage |
| 0.8 | `MonitorFeature`: monitor, snapshot, history, net-per-process, alerting. Interfaccia totale | glue | 60 | 0.6 | nessun Optional attraversa il confine |
| 0.9 | `KeepAwakeFeature`, incluso countdown ed etichetta tray | glue | 45 | 0.6 | interfaccia totale |
| 0.10 | `AudioFeature`: mixer e device switcher | glue | 30 | 0.6 | interfaccia totale |
| 0.11 | `TogglesFeature`: microfono, DND, dark mode. `state()` restituisce sempre un valore | glue | 40 | 0.7 | interfaccia totale |
| 0.12 | `ScenesFeature`: `SceneService` più applier a callback | glue | 30 | 0.11 | interfaccia totale |
| 0.13 | `ShelfFeature`: reconcile più shake monitor | glue | 35 | 0.5 | interfaccia totale |
| 0.14 | `ClipboardFeature`: reconcile, monitor, copy-back | glue | 35 | 0.5 | interfaccia totale |
| 0.15 | `AutoQuitFeature` più scelta della window source | glue | 30 | 0.6 | interfaccia totale |
| 0.16 | `UninstallerFeature` e `UpdateCheckFeature` | glue | 30 | 0.5 | interfaccia totale |
| 0.17 | `HotkeyFeature`: i binding sono raccolti dalle feature, non hardcoded in `application.py` | glue | 30 | 0.9, 0.12, 0.13, 0.14 | estendibilità blocco 2 |
| 0.18 | `TrayFeature`: build e refresh del menu, etichetta, `about-to-show` | glue | 60 | 0.7, 0.8-0.16 | menu non desincronizza |
| 0.19 | Riscrivere `do_startup` come composizione più dispatch di `settings-changed` alle feature | glue | 45 | 0.18 | `application.py` sotto 300 righe |
| 0.20 | `CLAUDE.md` di progetto: regola di non-ricrescita (una feature = un file in `app/features/` più due righe in `application.py`), regola scalari-in-GSettings / strutturati-in-JSON | doc | 30 | 0.19 | non-ricrescita |
| 0.21 | Verifica runtime completa contro la checklist 0.2, più fix | - | 60 | 0.19 | DoD blocco 0 |
| 0.22 | Commit atomici per feature, poi `code-reviewer` | - | 30 | 0.21 | gate pre-completamento |

Sottototale: circa 12 ore nette, 2-3 giorni.

## Blocco 1, azioni e CLI (branch `feature/actions-cli`)

| Id | Task | Tipo | Min | Dip. | DoD |
|---|---|---|---|---|---|
| 1.1 | Correggere `menu_builder.py:186`: togliere `_()` dal nome scena, risolvere il display name a monte (preset tradotti, nomi utente verbatim), più test anti-regressione sul gate `.po` | puro | 40 | 0.22 | gate traduzioni con nomi arbitrari |
| 1.2 | `MAX_SCENE_ROWS` in `constants.py` più pool fisso di slot nel sottomenu scene, sul modello di `_device_slots`, più test conteggio nodi a 0, 3 e 12 scene | puro | 45 | 1.1 | invariante dbusmenu |
| 1.3 | `app/commands/models.py`: `Command(id, title, category, param_type, requires)`, `CommandId` enum, `availability()` che restituisce available / hidden / disabled(reason), più test | puro | 45 | 1.2 | fonte unica |
| 1.4 | `app/commands/catalogue.py`: catalogo come costante di modulo, più test di completezza (ogni `CommandId` ha una voce) | puro | 45 | 1.3 | fonte unica |
| 1.5 | `_install_actions` derivata dal catalogo, con azioni parametriche `("s")` per le scene e `set_enabled(False)` sugli indisponibili. Test: ogni `CommandId` ha un handler | glue | 50 | 1.4 | catalogo completo su D-Bus, nomi stabili |
| 1.6 | Validazione del parametro lato ricevente per ogni azione parametrica, con rifiuto esplicito su tipo o valore inatteso, più test | puro | 30 | 1.5 | vincolo di sicurezza D-Bus |
| 1.7 | `app/remote.py`: invocazione `org.gtk.Actions.Activate` dietro Protocol, senza import Gtk, più test con fake | puro | 45 | 1.3 | CLI senza seconda istanza |
| 1.8 | CLI: positional `action` più `--list-actions`, choices derivate dal catalogo, più test del parser | puro | 45 | 1.7 | `sysbar --list-actions` |
| 1.9 | Exit code ed errori: azione ignota esce 2 elencando le valide, app non attiva esce 1 con messaggio. Più test | puro | 30 | 1.8 | exit code |
| 1.10 | `MenuActions` costruita per lookup dal catalogo, elimina la duplicazione con le GAction | glue | 30 | 1.4 | fonte unica |
| 1.11 | `DBusActivatable=true` nei `.desktop`, file `dbus-1/services`, regola in `packaging/debian/rules`, test in `tests/packaging/` | dati | 45 | 1.5 | `gapplication list-actions` non vuoto |
| 1.12 | README, README.it e CHANGELOG: sezione uso da CLI | doc | 30 | 1.9 | documentazione |
| 1.13 | Verifica runtime (lancio da dock e da autostart, nessuna doppia istanza), poi `code-reviewer` | - | 40 | 1.11 | DoD blocco 1 |

Sottototale: circa 8 ore nette, 1,5 giorni.

## Blocco 2, command palette (branch `feature/command-palette`)

| Id | Task | Tipo | Min | Dip. | DoD |
|---|---|---|---|---|---|
| 2.1 | `services/palette/models.py`: `PaletteEntry` con attivazione a unione `Runnable \| Unavailable`, Protocol `EntryProvider`, più test | puro | 40 | 1.13 | nessuno stato visibile-ma-non-attivabile |
| 2.2 | `services/palette/matcher.py`: match a sottosequenza con punteggio, puro, più test su bonus consecutivi, inizio parola, insensibilità a maiuscole e accenti | puro | 60 | 2.1 | matcher coperto |
| 2.3 | Ordinamento, cap dei risultati, raggruppamento per categoria, più test | puro | 45 | 2.2 | query vuota mostra i principali |
| 2.4 | Provider comandi, dal catalogo 1.4 filtrato per disponibilità | puro | 30 | 2.3 | capability assente non crasha |
| 2.5 | Provider voci clipboard, riusa `ClipboardService.search`, con mascheratura di default delle voci classificate come segreto | puro | 45 | 2.3 | vincolo di sicurezza palette |
| 2.6 | Provider item shelf | puro | 30 | 2.3 | filtro su shelf |
| 2.7 | Provider scene | puro | 20 | 2.3 | filtro su scene |
| 2.8 | Provider device audio, input e output, attivazione imposta il default | puro | 30 | 2.3 | filtro su device |
| 2.9 | Provider quick toggle con etichetta dipendente dallo stato | puro | 20 | 2.3 | filtro su toggle |
| 2.10 | `ui/palette/palette_window.py`: entry più `ListView` con righe titolo e sottotitolo | ui | 90 | 2.4-2.9 | finestra |
| 2.11 | Navigazione da tastiera: focus all'apertura, frecce, Invio, Esc, chiusura su perdita di focus | ui | 50 | 2.10 | accettazione focus, vincolo sicurezza |
| 2.12 | Chiave GSettings `hotkey-palette-enabled`, costanti shortcut, binding via `HotkeyFeature`, riga in Settings | dati | 45 | 2.10 | hotkey globale |
| 2.13 | `PaletteFeature`: costruzione lazy, provider interrogati all'apertura e non in startup | glue | 40 | 2.12 | nessun costo a startup |
| 2.14 | Catalogo `.po` italiano, finestra aggiunta a `_exercise_windows` e allo smoke test | test | 40 | 2.11 | gate traduzioni verde |
| 2.15 | Verifica manuale su X11 e su Wayland, limiti annotati in `DESIGN_DECISIONS.md` | doc | 45 | 2.13 | accettazione Wayland |
| 2.16 | `code-reviewer` più skill `a11y-gate` sulla finestra renderizzata | - | 45 | 2.15 | gate pre-completamento |

Sottototale: circa 11 ore nette, 2,5-3,5 giorni.

## Blocco 3, scene utente e trigger (branch `feature/user-scenes`)

| Id | Task | Tipo | Min | Dip. | DoD |
|---|---|---|---|---|---|
| 3.1 | `services/scenes/actions.py`: unione discriminata `SetToggle \| SetSetting \| SetOutputDevice`, tag `kind: Literal`, `to_dict`/`from_dict` per classe più tabella `_BY_KIND`, più test round-trip e su dato corrotto | puro | 70 | 2.16 | nessun `dict[str, object]` |
| 3.2 | `Scene` con `origin: StrEnum(BUILT_IN, USER)` e lista di azioni, fork-on-edit via `dataclasses.replace`, più test | puro | 45 | 3.1 | nessun flag `modified` |
| 3.3 | `apply(action, ports) -> ActionOutcome` con esito applied / skipped(reason) / failed(reason), port per capability, più test | puro | 60 | 3.1 | "3 azioni su 5 applicate" |
| 3.4 | `services/scenes/store.py`: manifest JSON `{version, scenes, triggers}`, permessi `0o600`, dir iniettabile, più test su file assente, JSON corrotto, id duplicato | puro | 70 | 3.2 | persistenza, vincolo `0o600` |
| 3.5 | Merge preset più override utente in copy-on-write, ripristino preset, rifiuto collisioni id, più test | puro | 40 | 3.4 | preset non eliminabili |
| 3.6 | `SceneService` alimentato dallo store, CRUD ed emissione `changed` | glue | 40 | 3.5 | CRUD |
| 3.7 | `ui/scenes/scenes_window.py`: lista scene, preset non eliminabili | ui | 60 | 3.6 | UI |
| 3.8 | Form editor: nome, azioni toggle, chiave GSettings da whitelist, device di output | ui | 90 | 3.7 | UI |
| 3.9 | Validazione (nome vuoto, chiave fuori whitelist, valore fuori range) più messaggi | ui | 30 | 3.8 | messaggi |
| 3.10 | Wiring finestra più voce di catalogo, azione, CLI e palette per aprirla | glue | 30 | 3.8 | fonte unica |
| 3.11 | `services/scenes/triggers.py` modelli: `TriggerRule(id, condition, scene_id, restore_on_exit)`, condizione a unione chiusa `ExternalMonitorConnected \| BatteryBelow(percent) \| OnBatteryPower`, serializzazione nel manifest | puro | 50 | 3.4 | modello chiuso |
| 3.12 | `evaluate(rules, state, ownership) -> list[SceneCommand]` puro: token di proprietà a slot singolo, isteresi sulle soglie, priorità per ordine di lista, più test su edge, no-loop, no-override manuale, ripristino solo se ancora proprietario | puro | 80 | 3.11 | semantica trigger |
| 3.13 | Protocol `TriggerSource` più adapter monitor esterno su `Gdk.Display.get_monitors()` con debounce di 2s | glue | 50 | 3.12 | sorgente monitor |
| 3.14 | Adapter alimentazione e batteria dal `SystemSnapshot` esistente | glue | 40 | 3.12 | sorgente batteria |
| 3.15 | Rate limit globale sulle attivazioni, più test | puro | 30 | 3.12 | anti-flapping |
| 3.16 | Wiring della valutazione in `ScenesFeature`, anti-override manuale end-to-end | glue | 45 | 3.13, 3.14, 3.15 | scena manuale mai sovrascritta |
| 3.17 | Chiave GSettings `scene-triggers-enabled` più riga in Settings | dati | 30 | 3.16 | interruttore globale |
| 3.18 | Notifica quando un trigger attiva una scena | glue | 20 | 3.16 | notifica |
| 3.19 | Sezione trigger nell'editor scena | ui | 60 | 3.17 | UI |
| 3.20 | `.po`, `_exercise_windows`, smoke test | test | 30 | 3.19 | gate traduzioni |
| 3.21 | Verifica runtime, `DESIGN_DECISIONS.md`, README, CHANGELOG, `code-reviewer` | - | 60 | 3.20 | DoD blocco 3 |

Sottototale: circa 17 ore nette, 3,5-4 giorni.

## Fuori scope dichiarato

| Elemento | Motivo | Dove ripianificarlo |
|---|---|---|
| Azione `RunCommand` nelle scene | Porta quasi tutto il rischio di sicurezza e poco valore. L'unione discriminata la accoglie dopo al costo di una dataclass | Iterazione successiva, con i vincoli già scritti nel piano |
| Azioni `LaunchApp`, `CloseApp`, `SetAppVolume` | Non necessarie perché la scena sia utile. Estensione a costo di una dataclass ciascuna | Iterazione successiva |
| Trigger su SSID di rete | Richiede un boundary NetworkManager nuovo, valore marginale | Se richiesto |
| Trigger su applicazione aperta | Richiede il fan-out di `WindowSource`, oggi consumato solo da auto-quit | Se richiesto |
| Trigger su fascia oraria | È la sorgente che genera più episodi di "il desktop è cambiato da solo" | Se richiesto |
| Congiunzione di condizioni (`AllOf`) | Richiede una UI a tabella di verità e rende ambigua la semantica di uscita | Aggiungibile come nodo della stessa unione, senza migrazione dati |
| Export, import e sync delle scene tra macchine | Superficie nuova, incluso import da URL che è un vettore | Se richiesto |
| Cifratura della clipboard history | Debito pre-esistente, indipendente da questo piano | Backlog separato |
| Stati illegali costruibili in `ShelfItem` (`services/shelf/models.py:19`) | Difetto pre-esistente, invariante affidata alla sola docstring | Backlog separato |
| Persistenza su disco dello storico metriche | Feature separata, non tocca questi quattro blocchi | Backlog separato |
