# Tasks 002

| id | titolo | dip | req | par | rollback | stato |
|---|---|---|---|---|---|---|
| T0 | baseline misurata con --cov-branch | - | R4 | ok | n/a | fatto |
| T1 | assert_never su 3 match | T0 | R5,R4 | ok | revert | |
| T2 | test refresh_enabled mapping parziale/vuoto | T0 | R4 | ok | revert | |
| T3 | app/panel_rows.py | T0 | R1,R2 | ok | revert | |
| T4 | app/palette_content.py | T0 | R1,R2 | ok | revert | |
| T5 | app/device_choices.py | T0 | R1,R2 | ok | revert | |
| T6 | app/scenes_content.py: form editor | T5 | R1,R2 | seq | revert | |
| T7 | scenes_content: righe lista scene | T6 | R1,R2 | seq | revert | |
| T8 | summary.partial_note/trigger_announcement, toggle_supported | T1 | R1,R2 | seq | revert | |
| T9 | services/shelf/pending_clear.py + add_dropped_text | T0 | R1,R2 | ok | revert | |
| T10 | uninstaller: target_from_app, leftover_subtitle, removal_message | T0 | R1,R2 | ok | revert | |
| T11 | settings_content.threshold_on_switch | T0 | R1 | ok | revert | |
| T12 | set_muted / set_active sui servizi toggle | T0 | R1 | ok | revert | |
| T13 | tray_state.menu_has_live_content / tray_label | T0 | R1 | ok | revert | |
| T14 | services/hotkey/portal_protocol.py, esce _create_session | T0 | R1,R3 | contratto | revert | |
| T15 | parsers._is_reportable, esce parse_upower_devices | T14 | R3 | seq | revert | |
| T16 | CombinedInhibitor + log dell'errore ScreenSaver ingoiato | T0 | R1,R9 | ok | revert | |
| T17 | app/clipboard_content.py (Could) | T0 | R1 | ok | revert | |
| T18 | gate traduzioni sui rami dei moduli puri | T3-T17 | R8 | seq | revert | |
| T19 | misura finale + checklist runtime | tutti | R4 | seq | n/a | |
| T20 | riscrittura test DA RISCRIVERE/DEBOLE di test-audit.md | T0 | R7 | ok | revert | |
| T21 | isolamento dconf della suite | - | R6 | ok | revert | fatto (f7f08b5) |
