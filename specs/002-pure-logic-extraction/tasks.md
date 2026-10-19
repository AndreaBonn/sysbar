# Tasks 002

| id | titolo | dip | req | par | rollback | stato |
|---|---|---|---|---|---|---|
| T0 | baseline misurata con --cov-branch | - | R4 | ok | n/a | fatto |
| T1 | assert_never su 3 match | T0 | R5,R4 | ok | revert | fatto (dd303b4) |
| T2 | test refresh_enabled mapping parziale/vuoto | T0 | R4 | ok | revert | fatto (4c40ca1) |
| T3 | app/panel_rows.py | T0 | R1,R2 | ok | revert | fatto (bdfddbc, 1cb255d) |
| T4 | app/palette_content.py | T0 | R1,R2 | ok | revert | fatto (2e8c041, e00ca38) |
| T5 | app/device_choices.py | T0 | R1,R2 | ok | revert | fatto (8623980, 80399cb) |
| T6 | app/scenes_content.py: form editor | T5 | R1,R2 | seq | revert | fatto (f16ca34, 871f337) |
| T7 | scenes_content: righe lista scene | T6 | R1,R2 | seq | revert | fatto (b307660, 3ff1772) |
| T8 | summary.partial_note/trigger_announcement, toggle_supported | T1 | R1,R2 | seq | revert | fatto (6c89e48) |
| T9 | services/shelf/pending_clear.py + add_dropped_text | T0 | R1,R2 | ok | revert | fatto (6eb0582, a2d3cc1) |
| T10 | uninstaller: target_from_app, leftover_subtitle, removal_message | T0 | R1,R2 | ok | revert | fatto (2782368, a2d3cc1) |
| T11 | settings_content.threshold_on_switch | T0 | R1 | ok | revert | fatto (40e3338, 9a01d5e) |
| T12 | set_muted / set_active sui servizi toggle | T0 | R1 | ok | revert | fatto (06f4f17) |
| T13 | tray_state.menu_has_live_content / tray_label | T0 | R1 | ok | revert | fatto (f82779f) |
| T14 | services/hotkey/portal_protocol.py, esce _create_session | T0 | R1,R3 | contratto | revert | fatto (d90b6b1) |
| T15 | parsers._is_reportable, esce parse_upower_devices | T14 | R3 | seq | revert | fatto (4d99e23) |
| T16 | CombinedInhibitor + log dell'errore ScreenSaver ingoiato | T0 | R1,R9 | ok | revert | fatto (2751599) |
| T17 | app/clipboard_content.py (Could) | T0 | R1 | ok | revert | fatto (a8b4da1) |
| T18 | gate traduzioni sui rami dei moduli puri | T3-T17 | R8 | seq | revert | fatto (a2c693b, 5cdf166) |
| T19 | misura finale + checklist runtime | tutti | R4 | seq | n/a | |
| T20 | riscrittura test DA RISCRIVERE/DEBOLE di test-audit.md | T0 | R7 | ok | revert | |
| T21 | isolamento dconf della suite | - | R6 | ok | revert | fatto (f7f08b5) |
| T22 | fix blocco della combo dispositivi audio (set_model rientrante in notify::selected), emerso in T5 | - | R9 | - | revert | fatto (07c9041) |

Note per T18: `ui/panel/mixer_section.py` `set_unavailable` mostra "PipeWire/PulseAudio not available" senza `_()` e il msgid non è nel `.po`: stringa inglese nella UI italiana, da correggere con msgid e traduzione.
