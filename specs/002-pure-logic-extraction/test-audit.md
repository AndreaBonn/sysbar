# Audit qualitativo della suite di test di sysbar

Data: 2026-10-19. Perimetro: tests/ (93 file .py: 87 file test_*.py + 6 helper conftest/__init__), 1164 funzioni di test (1246 item pytest con i parametri). Nessun file modificato fuori dallo scratchpad.

## BASIS

- Copertura dell'audit: BASIS: measured. 87/87 file test aperti e letti per intero (le stampe con righe vuote rimosse non perdono contenuto; ho verificato le code dei file lunghi). Le 6 helper (conftest.py x2, __init__.py x4) sono state lette dove contengono codice (2 conftest).
- Pre-filtro AST (scan.py nello scratchpad): 1164 funzioni, flag NOASSERT/ALLWEAK/TIME/SKIP. Falsi positivi dei flag TIME/SKIP (match su "sleep"/"socket"/"skips" nel nome): confermato che non esiste sleep, orologio reale, rete o random nei test (grep: unico `monotonic` e' un fake in test_speedtest.py:29).
- Suite eseguita: `xvfb-run uv run pytest -q -p no:randomly --no-cov`: tutti i punti verdi, nessun F/E (BASIS: measured, log in full.log).
- Mutazioni: 1 confermata con una sottoclasse nello scratchpad (src/ intatto), 2 tautologie dimostrate con calcolo diretto. Le altre mutazioni sono solo descritte (BASIS: inferred).
- "Nessun test copre X" non e' stato verificato in nessun punto: i gap segnalati sono `inferred`.

## Giudizio d'insieme

Suite di buona qualita': 1111 test su 1164 BUONI (95,4%). Pattern dominanti positivi: fake in-memory al posto dei mock, orologio iniettato (`_Clock`, `FakeClock`), tmp_path per ogni scrittura, nomi che descrivono il comportamento, valori attesi concreti, test di regressione con docstring che spiegano il bug evitato (store, scenes, clipboard). Nessun sleep, nessuna rete, nessun random.

Problemi reali, in ordine di gravita': (1) un'intera famiglia di test scrive su dconf reale dell'utente; (2) 10 test non possono fallire o non asseriscono nulla; (3) 43 test deboli (asserzione su sola cardinalita'/presenza, accoppiamento a privati, duplicati).

## Tabella per file

| file_test | n_test | buoni | deboli | da_riscrivere | note |
|---|---|---|---|---|---|
| tests/app/commands/test_actions.py | 15 | 14 | 1 | 0 |  |
| tests/app/commands/test_catalogue.py | 16 | 16 | 0 | 0 |  |
| tests/app/commands/test_command_palette_entries.py | 13 | 13 | 0 | 0 |  |
| tests/app/commands/test_wiring.py | 12 | 10 | 2 | 0 | fake con __getattr__ accetta qualsiasi metodo: nome errato sulla feature reale non verrebbe visto |
| tests/app/test_context.py | 5 | 4 | 1 | 0 |  |
| tests/app/test_onboarding_content.py | 9 | 9 | 0 | 0 |  |
| tests/app/test_palette_entries.py | 14 | 8 | 6 | 0 |  |
| tests/app/test_panel_summary.py | 15 | 15 | 0 | 0 |  |
| tests/app/test_settings_content.py | 9 | 8 | 1 | 0 |  |
| tests/app/test_shortcuts.py | 7 | 7 | 0 | 0 |  |
| tests/app/test_tray_renderer.py | 38 | 38 | 0 | 0 |  |
| tests/app/test_tray_state.py | 26 | 23 | 3 | 0 |  |
| tests/app/test_uninstall_content.py | 7 | 7 | 0 | 0 |  |
| tests/app/test_whats_new.py | 5 | 5 | 0 | 0 |  |
| tests/app/test_windows.py | 10 | 9 | 1 | 0 |  |
| tests/app/tray/test_dbus_menu.py | 37 | 34 | 2 | 1 | molti test su metodi privati (_build_item, _props_variant, _get_layout) |
| tests/app/tray/test_menu_builder.py | 27 | 26 | 0 | 1 |  |
| tests/app/tray/test_menu_model.py | 11 | 10 | 1 | 0 |  |
| tests/app/tray/test_scene_slots.py | 7 | 5 | 2 | 0 |  |
| tests/core/test_branding.py | 8 | 8 | 0 | 0 |  |
| tests/core/test_capabilities.py | 29 | 29 | 0 | 0 |  |
| tests/core/test_config.py | 28 | 27 | 1 | 0 |  |
| tests/core/test_errors.py | 8 | 7 | 1 | 0 |  |
| tests/core/test_i18n.py | 3 | 3 | 0 | 0 |  |
| tests/core/test_localization.py | 18 | 14 | 4 | 0 | 5 skip condizionali su msgfmt; path relativi 'data/locale' dipendono dalla cwd |
| tests/core/test_logging_setup.py | 8 | 8 | 0 | 0 |  |
| tests/core/test_validation.py | 21 | 21 | 0 | 0 |  |
| tests/packaging/test_debian_rules.py | 2 | 1 | 1 | 0 |  |
| tests/services/audio/test_app_volume_mixer.py | 10 | 10 | 0 | 0 |  |
| tests/services/audio/test_device_switcher.py | 6 | 6 | 0 | 0 |  |
| tests/services/audio/test_models.py | 9 | 9 | 0 | 0 |  |
| tests/services/audio/test_pulse_backend.py | 14 | 12 | 2 | 0 | object.__new__ + attributi privati; manca copertura di set_volume/set_mute/list_sinks |
| tests/services/auto_quit/test_os_terminator.py | 9 | 9 | 0 | 0 | 2 test 'must not raise' accoppiati a test positivi: BUONI |
| tests/services/auto_quit/test_service.py | 14 | 12 | 2 | 0 |  |
| tests/services/auto_quit/test_source_selection.py | 3 | 3 | 0 | 0 |  |
| tests/services/auto_quit/test_wnck_source.py | 10 | 10 | 0 | 0 | 2 test 'noop senza callback' accoppiati a test positivi: BUONI |
| tests/services/clipboard/test_clipboard_service.py | 23 | 21 | 2 | 0 |  |
| tests/services/clipboard/test_sensitive_text.py | 15 | 15 | 0 | 0 |  |
| tests/services/hotkey/test_manager.py | 4 | 4 | 0 | 0 |  |
| tests/services/keep_awake/test_manager.py | 15 | 15 | 0 | 0 |  |
| tests/services/keep_awake/test_scheduler.py | 2 | 2 | 0 | 0 |  |
| tests/services/metrics/test_metric_format.py | 15 | 15 | 0 | 0 |  |
| tests/services/metrics/test_speedtest.py | 7 | 6 | 1 | 0 |  |
| tests/services/palette/test_palette_matcher.py | 32 | 31 | 1 | 0 |  |
| tests/services/palette/test_palette_models.py | 9 | 9 | 0 | 0 |  |
| tests/services/palette/test_palette_sources.py | 21 | 21 | 0 | 0 |  |
| tests/services/quick_toggles/test_desktop_toggles.py | 8 | 8 | 0 | 0 |  |
| tests/services/quick_toggles/test_microphone.py | 6 | 6 | 0 | 0 |  |
| tests/services/scenes/test_scene_actions.py | 17 | 17 | 0 | 0 |  |
| tests/services/scenes/test_scene_adapters.py | 11 | 8 | 0 | 3 | Config() senza backend: scrive su dconf reale (finding F1) |
| tests/services/scenes/test_scene_apply.py | 11 | 11 | 0 | 0 |  |
| tests/services/scenes/test_scene_editing.py | 29 | 29 | 0 | 0 |  |
| tests/services/scenes/test_scene_engine.py | 17 | 17 | 0 | 0 |  |
| tests/services/scenes/test_scene_models.py | 24 | 23 | 0 | 1 |  |
| tests/services/scenes/test_scene_service.py | 17 | 17 | 0 | 0 | _SCENES lista di modulo condivisa tra test |
| tests/services/scenes/test_scene_store.py | 42 | 41 | 1 | 0 |  |
| tests/services/scenes/test_scene_summary.py | 7 | 7 | 0 | 0 |  |
| tests/services/scenes/test_scene_triggers.py | 29 | 28 | 1 | 0 |  |
| tests/services/shelf/test_shake_detector.py | 5 | 4 | 0 | 1 | test_reset_clears_state non puo' fallire (mutazione misurata) |
| tests/services/shelf/test_shake_monitor.py | 12 | 10 | 2 | 0 |  |
| tests/services/shelf/test_shelf_service.py | 24 | 24 | 0 | 0 |  |
| tests/services/system_monitor/test_adapters.py | 47 | 47 | 0 | 0 | GpuReaderChain: patch di helper dello stesso modulo (_nvml_value, _amd_*_path) |
| tests/services/system_monitor/test_alerting.py | 17 | 17 | 0 | 0 |  |
| tests/services/system_monitor/test_history.py | 11 | 11 | 0 | 0 |  |
| tests/services/system_monitor/test_monitor.py | 15 | 15 | 0 | 0 | asserisce _timer_id privato oltre alle chiamate GLib mockate |
| tests/services/system_monitor/test_net_per_process.py | 10 | 10 | 0 | 0 |  |
| tests/services/system_monitor/test_parsers.py | 26 | 26 | 0 | 0 |  |
| tests/services/system_monitor/test_processes.py | 8 | 8 | 0 | 0 |  |
| tests/services/system_monitor/test_sampler.py | 13 | 13 | 0 | 0 |  |
| tests/services/system_monitor/test_termination.py | 5 | 5 | 0 | 0 |  |
| tests/services/test_autostart.py | 5 | 5 | 0 | 0 |  |
| tests/services/test_update_service.py | 12 | 12 | 0 | 0 |  |
| tests/services/uninstall/test_app_uninstaller.py | 7 | 7 | 0 | 0 |  |
| tests/services/uninstall/test_command_query.py | 15 | 15 | 0 | 0 |  |
| tests/services/uninstall/test_identifier.py | 4 | 4 | 0 | 0 |  |
| tests/services/uninstall/test_leftover_scanner.py | 8 | 8 | 0 | 0 |  |
| tests/services/uninstall/test_package_remover.py | 10 | 10 | 0 | 0 |  |
| tests/services/uninstall/test_trash.py | 3 | 3 | 0 | 0 |  |
| tests/services/uninstall/test_uninstall_models.py | 2 | 2 | 0 | 0 |  |
| tests/support/test_selftest.py | 6 | 6 | 0 | 0 |  |
| tests/support/test_sensors_dump.py | 6 | 6 | 0 | 0 |  |
| tests/test_cli_actions.py | 12 | 12 | 0 | 0 |  |
| tests/test_main.py | 10 | 9 | 1 | 0 |  |
| tests/test_source_limits.py | 4 | 4 | 0 | 0 | gate AST sul sorgente per convenzione di progetto: BUONO |
| tests/test_version.py | 3 | 2 | 0 | 1 |  |
| tests/ui/test_translation_coverage.py | 1 | 0 | 1 | 0 | Config()/AutostartManager() reali, home=/tmp; nessun assert su recorder.seen |
| tests/ui/test_windows_smoke.py | 19 | 15 | 2 | 2 | smoke per costruzione (dichiarato); 2 test senza assert; Config()/AutostartManager() reali |
| TOTALE (87 file) | 1164 | 1111 | 43 | 10 | funzioni di test; 1246 item pytest con i parametri |

## Finding

Formato: ID, categoria, path:riga, motivo, versione corretta proposta. BASIS in coda quando non e' `measured`.

### DA RISCRIVERE (10)

**F1. tests/services/scenes/test_scene_adapters.py:17, :30, :46** - isolamento rotto.
`Config()` senza `backend=` usa il backend di default, che in questa macchina e' `DConfSettingsBackend` (measured: `Gio.SettingsBackend.get_default()`). I tre test scrivono `alert-enabled=True`, `monitor-interval-seconds=5`, `active-scene='focus'` sul dconf reale dell'utente. `dconf dump /io/github/AndreaBonn/Sysbar/` riporta proprio `active-scene='focus'`, `alert-enabled=true`, `monitor-interval-seconds=5` (measured), mentre il default dello schema e' 2 (test_config.py:test_defaults_match_schema). Il nesso causale con la suite non e' isolato (potrebbe essere anche l'app in uso): BASIS: inferred. Contraddice CLAUDE.md di progetto ("Mai Gio.Settings diretto" nei test: gli altri file usano `Config(backend=Gio.memory_settings_backend_new())`).
Correzione:
```python
@pytest.fixture
def config(compiled_schema: str) -> Config:
    return Config(backend=Gio.memory_settings_backend_new())
# i tre test: writer = ConfigSettingsWriter(config), stesse asserzioni.
```
Gli altri due test del file che usano `Config()` (refuses_a_key_the_schema_does_not_have, refuses_a_key_whose_type) non scrivono ma vanno spostati sulla stessa fixture.

**F2. tests/services/shelf/test_shake_detector.py:40** `test_reset_clears_state` non puo' fallire (measured). Sequenza 30, -30, reset, 30: anche con `reset()` ridotto a no-op il quarto campione restituisce `False` perche' servono 4 inversioni. Mutazione provata su sottoclasse con `reset` no-op: l'asserzione resta vera (mutants.py nello scratchpad).
Correzione: portare il detector a 3 inversioni, chiamare `reset()`, poi inviare l'unico campione che chiuderebbe la quarta inversione e asserire `False`; in un secondo test paired, senza reset, lo stesso campione ritorna `True`.

**F3. tests/app/tray/test_menu_builder.py:55** `test_has_one_slot_per_tray_metric`: `len(items[:N]) == N` e' vero per qualsiasi lista con almeno N elementi (tautologia dimostrata). Correzione: asserire che gli id/etichette dei primi N slot siano quelli di `TRAY_METRICS` nell'ordine (`[slot.item_type for slot in metric_slots]` tutti non-separator e `len(items) >= N`), oppure rimuoverlo: `test_hidden_metric_slot_keeps_position_for_stable_ids` copre gia' la posizione.

**F4. tests/app/tray/test_dbus_menu.py:312** `test_set_model_skips_emit_when_not_connected` asserisce `server._connection is None`, cioe' la precondizione: senza connessione non c'e' nulla che registri un'emissione, quindi il test passa anche se `set_model` provasse a emettere. Correzione: dare al server una `FakeConnection` poi `unregister()`, chiamare `set_model`, asserire `connection.emitted == []` (con il test gemello `test_set_model_emits_layout_and_properties_updates_when_connected` come caso positivo, gia' presente).

**F5. tests/test_version.py:12** `test_version_is_not_the_stale_hardcoded_value`: la prima asserzione duplica `test_version_matches_installed_package_metadata` (:8); la seconda `__version__ != "1.0.0" or version("sysbar") == "1.0.0"` e' vera per qualsiasi stringa (dimostrato su 0.0.1, 1.0.0, 9.9.9). Correzione: eliminarlo; la regressione ("hardcoded e driftato") la copre gia' :8 se la versione installata e' quella di pyproject (verificare che l'install sia editable: altrimenti confrontare con `tomllib` su pyproject.toml).

**F6. tests/ui/test_windows_smoke.py:58 e :72** `test_panel_window_sparklines_update`, `test_panel_window_net_processes_update`: nessuna asserzione. Passano se i metodi non sollevano. Correzione: dopo `update_history`, asserire lo stato osservabile (es. numero di punti nel widget sparkline, o `window._...` pubblico equivalente); dopo `update_net_processes`, asserire che esista una riga con testo "firefox".

**F7. tests/services/scenes/test_scene_models.py:168** `test_a_built_in_scene_name_is_translated`: confronta `scene_display_name(preset)` con `_(preset.name)`, cioe' ricalcola l'atteso con la stessa funzione. Con `NullTranslations` e' vero anche se `scene_display_name` restituisse `preset.name`. Correzione: installare una traduzione fake `{"Focus": "Concentrazione"}` (come `_FakeTranslation` in test_i18n.py) e asserire `scene_display_name(preset) == "Concentrazione"`, piu' il caso utente gia' presente (:175) che resta verbatim.

### DEBOLE (43)

**Cardinalita' o presenza come unica prova**
- tests/app/tray/test_dbus_menu.py:407, :416 - `len(invocation.returned) == 1` senza guardare il payload. Asserire `returned[0].unpack()` (entries/valore "A").
- tests/app/test_tray_state.py:149 `len(rows) == 2`; :213 `startswith("▶ ")` e `!= "▶"` senza il testo formattato (atteso concreto, es. "▶ 1:30"); :125 `"42" in values["cpu"]`.
- tests/app/test_palette_entries.py:151, :163, :180, :199 (kind presente nell'insieme), :218, :230 (`len == 2`). I test "activate" accoppiati verificano il contenuto: valutare di fonderli, e asserire titolo/id nella stessa riga. :151 duplica `test_an_empty_session_still_lists_the_commands`.
- tests/services/clipboard/test_clipboard_service.py:76 (`"keep" in texts`; asserire la lista completa), :123 (`len(search("  ")) == 2`; asserire i testi).
- tests/core/test_config.py:178 e tests/core/test_errors.py:29 - solo `isinstance`. Per :29 meglio `with pytest.raises(AppError): raise ValidationError("x")`.
- tests/ui/test_windows_smoke.py:134 (`get_title() is not None`, vero per qualsiasi finestra costruita), :170 (`row is not None`; asserire il titolo della riga).
- tests/core/test_localization.py:61 (`result in _LOCALE_CANDIDATES`, quasi tautologico), :55 (con "en" l'atteso e' la msgid anche se `install_language` non facesse nulla; accoppiarlo a un test che prova il rebind su "it", gia' presente).
- tests/test_main.py:10 `SystemExit` senza codice ne' output (asserire `code == 0` e `capsys` contiene la versione).

**Negative senza positivo appaiato o vacue**
- tests/ui/test_translation_coverage.py:309 - `assert not missing` passa se i quattro `_exercise_*` non registrano nulla. Aggiungere `assert {"Quit", "Settings"} <= recorder.seen` (o equivalente) prima del confronto. Inoltre `Config()`, `AutostartManager()` e `home=Path("/tmp")` sono reali (lettura di dconf, `~/.config/autostart`, /tmp): dipendenza dall'host.
- tests/app/tray/test_scene_slots.py:141 e :105 - negativi senza appaiato (`"Riunione col cliente" not in recorder.seen` passa se il recorder non cattura nulla; `f"Scene {MAX}" not in labels`). Aggiungere `assert "Scenes" in recorder.seen` e `labels == [f"Scene {i}" for i in range(MAX)]`.
- tests/services/scenes/test_scene_store.py:461 - `test_an_already_private_manifest_is_left_alone` asserisce 0o600 su un file che era gia' 0o600: non distingue "lasciato stare" da "riscritto". Spiare `Path.chmod` (monkeypatch contatore) e asserire zero chiamate.
- tests/services/scenes/test_scene_triggers.py:275 - `assert evaluate(...).activate` solo truthy. Asserire `== "power-saving"`.

**Accoppiamento a privati o a implementazione**
- tests/services/audio/test_pulse_backend.py:167, :181 - `object.__new__`, `_running`, `_callback` privati; patch di `threading.Thread`. Testare attraverso un evento reale con un `FakePulse` che invoca il callback.
- tests/services/shelf/test_shake_monitor.py:137 (`isinstance(monitor._detector, ShakeDetector)`, tautologia sul costruttore), :108 (spia su `reset`).
- tests/services/auto_quit/test_service.py:180, :190 - mutano `_window_app`/`_app_pid` per raggiungere rami difensivi (il commento ammette che nessuna API pubblica li produce): coverage-chasing, o si rendono raggiungibili o si tolgono i rami.
- tests/app/commands/test_actions.py:154 - `test_glib_itself_drops...` testa GLib (docstring: "removing the check would not show up here"). Eliminarlo.
- tests/app/commands/test_wiring.py:146 - il `_Recorder.__getattr__` accetta qualsiasi nome: una feature reale con metodo rinominato lascerebbe il test verde (BASIS: inferred, non ho aperto le feature reali). Correzione: `spec=` sulle classi reali (`mocker.create_autospec(ScenesFeature)`), o un `Protocol` verificato da mypy.
- tests/services/system_monitor/test_monitor.py:28 e altri 5 - asseriscono `_timer_id` privato oltre ai mock GLib (che sono la vera prova). Togliere le asserzioni su `_timer_id`.

**Duplicati / ridondanti**
- tests/app/test_windows.py:88 identico a :71 (stesso corpo).
- tests/app/tray/test_menu_model.py:28 implicato da `test_ids_are_contiguous_from_zero`.
- tests/app/commands/test_wiring.py:202 implicato da `test_the_handler_map_covers_the_whole_enum`.
- tests/app/test_context.py:49 testa l'assegnazione di un campo dataclass.
- tests/services/palette/test_palette_matcher.py:141 `first == second` chiama due volte la stessa funzione: non fissa l'ordine. Con tre `_entry` di pari punteggio asserire l'ordine esatto atteso `["Alpha command", "Beta command", "Gamma command"]`.

**Altro**
- tests/services/metrics/test_speedtest.py:54 - `== 0.004` su float con `==` (regola: `pytest.approx`).
- tests/app/test_settings_content.py:17 - ricopia la costante `PLACEMENT_OPTIONS` (test-che-ripete-il-dato); testare `ui` che consuma le opzioni o eliminarlo.
- tests/core/test_localization.py:188, :208 - `Path("data/locale/...")` relativo alla cwd: fallisce se pytest parte da un'altra directory. Usare `Path(__file__).resolve().parents[2]`. 5 skip condizionali su `msgfmt` (righe 93, 101, 117, 172, 181 e skipif :207): senza gettext la suite verde nasconde 6 funzioni di test (una parametrizzata su 10 casi).
- tests/packaging/test_debian_rules.py:21 - confronto di posizione di stringhe nel Makefile `rules`: stringa, non comportamento. Accettabile come guard di regressione dichiarato nel docstring, ma si rompe a ogni riformattazione del comando. Alternativa: eseguire `dh_auto_install` dry-run, oppure un test di installazione in tmp.

### Osservazioni senza classificare (BUONI ma da sapere)

- "Must not raise" (test_os_terminator.py:43, :48; test_wnck_source.py:43, :69; test_scene_adapters.py:109): accoppiati a test positivi stessa fixture, quindi validi.
- tests/services/system_monitor/test_adapters.py:208-: `GpuReaderChain` e' testato patchando `_nvml_value` e `_amd_*_path` dello stesso modulo (mock di codice sotto test). Giustificato perche' i due helper hanno test propri, ma e' l'unico punto in cui il criterio "mai il codice sotto test" e' violato in modo strutturale.
- tests/services/scenes/test_scene_service.py: `_SCENES` e' una lista di modulo passata a `SceneService`; se il servizio non copia la lista, i test condividono stato (non verificato: BASIS: unknown).
- tests/test_source_limits.py e' un gate AST sul sorgente per convenzione di progetto: coerente con CLAUDE.md di progetto, non e' un difetto.
- tests/ui/test_windows_smoke.py: dichiarato smoke per costruzione; 6 test verificano solo `get_title()` truthy. Accettabile come rete di sicurezza, ma non e' comportamento.
- Gap (BASIS: inferred, da dimensione dei file e import): nessun test per `services/hotkey/portal.py` e per i metodi `set_volume/set_mute/list_sinks` di `PulseAudioBackend`; `omit` in coverage dichiara che GUI e glue D-Bus sono verificati a mano.

## Mutazioni descritte e non applicate (BASIS: inferred)

1. `Capabilities.refresh`: non emettere `changed` al primo giro -> `test_refresh_emits_changed_when_state_flips` (len 2) fallisce: sensibile.
2. `ClipboardService._evict`: ignorare `pinned` -> `test_pinned_entry_is_not_evicted` passa solo se "keep" e' sopravvissuto: fallisce, ma non rileva se viene evinto un altro elemento (peso della debolezza :76).
3. `DBusMenuServer._handle_method`: restituire `value=None` per `GetProperty` -> `test_handle_method_get_property_returns_value` (:416) resta verde perche' conta solo `len(returned)`.
4. `AppVolumeMixer.refresh`: rimuovere l'epsilon -> `test_persisted_volume_within_epsilon_is_not_reapplied` fallisce: sensibile.
5. `SceneStore.load`: non chiamare `chmod` -> `test_a_manifest_with_wide_permissions_is_narrowed_on_load` fallisce; `test_an_already_private...` resta verde con qualsiasi implementazione (riga :461).
