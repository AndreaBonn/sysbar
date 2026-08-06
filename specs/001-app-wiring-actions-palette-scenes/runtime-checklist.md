# Checklist di verifica runtime, blocco 0

Il refactor del wiring è a comportamento invariato, ma `src/sysbar/app/application.py` è
escluso dalla coverage: un `connect` perso o un reconcile non ricablato non fa fallire
nessun test. Questa lista enumera i comportamenti che funzionano **prima** dello split, per
poterli riverificare **dopo**, uno per uno.

Compilata leggendo `application.py` al commit di partenza del branch `refactor/app-wiring`.
Ogni riga cita il metodo che oggi realizza il comportamento, così la verifica sa dove
guardare quando fallisce.

## Avvio e tray

- [ ] L'icona compare nel tray dopo l'avvio (`_setup_tray`, richiede la connessione al
      session bus; senza bus logga "no session bus connection" e non crasha).
- [ ] Le icone brandizzate sono registrate: la finestra non mostra l'ingranaggio generico
      di GNOME (`register_app_icons` in `do_startup`).
- [ ] Al primo avvio senza `has-onboarded` parte l'onboarding (`do_activate`).
- [ ] Al secondo avvio, l'istanza già viva apre il pannello invece di duplicarsi
      (`do_activate`, ramo `else`).
- [ ] La lingua segue `app-language` (`install_language` in `do_startup`).

## Etichetta e menu del tray

- [ ] L'etichetta mostra le metriche con placement `bar`, separate da " · "
      (`_refresh_tray_label`).
- [ ] Le metriche con placement `menu` compaiono nel dropdown, quelle `off` no
      (`_menu_metric_values`).
- [ ] Aprendo il menu tre volte di seguito, nessuna voce risulta grigia, duplicata o con
      etichetta di un'altra voce (invariante dbusmenu, `_on_menu_about_to_show`).
- [ ] Con tutte le metriche su `off` e batterie periferiche disattivate, il campionamento
      del tray si ferma (`_update_tray_active` verso `set_tray_active`).
- [ ] Le righe batteria delle periferiche compaiono se `menu-show-device-batteries` è
      attivo e ci sono periferiche (`_menu_device_rows`).
- [ ] Le voci microfono, Do Not Disturb e dark mode compaiono solo con la capability
      presente, e la loro etichetta riflette lo stato corrente (`_quick_toggle_state`).
- [ ] Il sottomenu Scene elenca le tre preset con la spunta su quella attiva, e "Nessuna"
      la azzera (`_scene_menu_entries`, `_clear_scene`).
- [ ] La riga di credito in fondo apre il profilo GitHub (`_open_github`).

## Finestre

- [ ] Pannello: si apre dal click sul tray e dalla voce di menu, si richiude, si riapre
      (`_open_panel`, `_on_panel_closed` azzera il riferimento).
- [ ] Pannello aperto: il mixer per applicazione compare se PipeWire o PulseAudio è
      presente, altrimenti mostra il messaggio di indisponibilità (`set_mixer_unavailable`).
- [ ] Pannello aperto: il selettore di device input e output è popolato (`bind_devices`,
      `_device_switcher.refresh()`).
- [ ] Pannello aperto: le sparkline si disegnano per le metriche con `monitor-graph-*`
      attivo, e cambiano subito se si commuta la chiave (`_on_settings_changed`).
- [ ] Pannello aperto: la lista processi si aggiorna e il pulsante di terminazione chiede
      conferma prima di agire (`_confirm_kill_process`).
- [ ] Pannello aperto: la sezione "rete per processo" si popola quando `ss` è disponibile
      (`_update_net_processes`).
- [ ] Pannello chiuso: il monitor riduce il campionamento (`set_panel_open(False)`).
- [ ] Impostazioni: si aprono, si chiudono, si riaprono, e le metriche non disponibili
      sull'hardware corrente risultano disabilitate (`_unavailable_metrics`).
- [ ] Shelf: si apre dal menu e dalla hotkey, accetta un file trascinato, lo mantiene dopo
      la chiusura e riapertura (`_open_shelf`).
- [ ] Clipboard: si apre dal menu e dalla hotkey, la history si popola copiando testo,
      cliccando una voce la ricopia (`_on_clipboard_text`, `_copy_to_clipboard`).
- [ ] Uninstaller: si apre e elenca le applicazioni installate (`_open_uninstaller`).

## Keep awake

- [ ] Il toggle dal menu attiva e disattiva l'inibizione (`_toggle_keep_awake`).
- [ ] Con `show-countdown` attivo e una durata impostata, il countdown scorre nell'etichetta
      del tray ogni secondo (`_reconcile_countdown`, `_on_countdown_tick`).
- [ ] Alla scadenza del timer arriva la notifica di fine sessione (`_on_session_ended`).
- [ ] Disattivando keep awake il timer del countdown viene rimosso e non resta appeso
      (`_reconcile_countdown`, ramo di spegnimento).

## Scene

- [ ] Attivare Focus accende keep awake, attiva Do Not Disturb e muta il microfono
      (`_scene_set_keep_awake`, `_scene_set_dnd`, `_scene_set_mic`).
- [ ] La scena attiva sopravvive al riavvio (`active-scene` in GSettings).
- [ ] La hotkey Focus commuta: se Focus è attiva la azzera, altrimenti la attiva
      (`_toggle_focus_scene`).

## Alert

- [ ] Con `alert-enabled` e una soglia superata arriva una notifica, una sola volta finché
      il valore non rientra (`_evaluate_alerts`, fronte di salita in `AlertEngine`).
- [ ] Disattivando `alert-enabled` il monitor smette di valutare
      (`_reconcile_alerting` verso `set_alerting_active`).

## Reconcile su cambio impostazioni

- [ ] Cambiando una chiave `shelf-*` il servizio shelf e lo shake monitor si riallineano
      senza riavvio (`_on_settings_changed` verso `_reconcile_shelf`).
- [ ] Cambiando una chiave `clipboard-*` il servizio clipboard si riallinea
      (`_reconcile_clipboard`).
- [ ] Cambiando una chiave `alert-*` l'alerting si riallinea (`_reconcile_alerting`).
- [ ] Cambiando un placement di metrica l'etichetta del tray si aggiorna subito
      (`_update_tray_active`).

## Hotkey globali

- [ ] Le quattro shortcut (keep awake, shelf, clipboard, scena Focus) si registrano solo se
      la rispettiva chiave `hotkey-*-enabled` è attiva (`_hotkey_bindings`).
- [ ] Senza il portal GlobalShortcuts l'app parte comunque, senza hotkey e con un warning
      nel log (`_setup_hotkey`, blocco `except`).

## Auto-quit

- [ ] Su X11 il tracciamento finestre usa libwnck, su Wayland l'estensione GNOME Shell, e
      in assenza di entrambe la feature si disattiva senza crash (`_create_window_source`).

## Aggiornamenti

- [ ] Con `auto-check-updates` attivo, il controllo parte in un thread e non blocca
      l'avvio; la notifica arriva sul main loop (`_setup_update_check`, `GLib.idle_add`).

## Capability dinamiche

- [ ] Le capability vengono rilette periodicamente e l'abilitazione dell'estensione Shell
      viene rilevata senza riavviare l'app (`_refresh_capabilities`, ogni 5 secondi).

## Comando di verifica rapida

```
pgrep -af sysbar
busctl --user call io.github.AndreaBonn.Sysbar /io/github/AndreaBonn/Sysbar org.gtk.Actions List
journalctl --user -f | grep -i sysbar    # nessun traceback durante la sessione di prova
```
