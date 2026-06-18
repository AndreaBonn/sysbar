# Report Attività - sysbar

Progetto: sysbar
Data creazione: 2026-06-18

---

## [2026-06-18] - Sessione #1 [FEATURE]

### Richiesta

Implementare la distribuzione configurabile delle metriche di sistema nella tray. Prima ogni metrica aveva un semplice interruttore on/off; ora l'utente sceglie tra tre destinazioni per ciascuna metrica: nascosta, visibile nella barra, o visibile nel menu a tendina.

### Azioni Eseguite

- Definite nuove costanti per i valori di placement (off/bar/menu) e l'elenco delle metriche configurabili
- Aggiunta funzione di sanitizzazione per validare il placement ricevuto dalla configurazione
- Aggiornata la lettura della configurazione per supportare il placement per metrica, con migrazione automatica dalle vecchie impostazioni booleane (chi aveva una metrica attiva la ritrova in "Bar")
- Modificato il renderer della tray per filtrare le metriche in base alla destinazione: testo barra separato da righe menu
- Aggiornata la costruzione del menu in `application.py` con le metriche in cima e refresh live a ogni campionamento
- Riscritta la sezione "Tray metrics" della finestra impostazioni con menu a tendina a 3 scelte in luogo degli interruttori
- Aggiunte 6 nuove chiavi di placement allo schema GSettings; le vecchie chiavi booleane sono conservate per la migrazione ma marcate come deprecate
- Aggiornati i test per `core` e `app` in linea con le nuove interfacce
- Tutti i test passano, copertura al 100%, nessun errore ruff

### File Modificati

| File | Tipo | Descrizione |
|------|------|-------------|
| src/sysbar/core/constants.py | modifica | Nuove costanti placement (off/bar/menu) e lista metriche tray |
| src/sysbar/core/validation.py | modifica | Funzione sanitizzazione valore placement |
| src/sysbar/core/config.py | modifica | Lettura placement per metrica + migrazione automatica da booleani |
| src/sysbar/app/tray_renderer.py | modifica | Filtro per destinazione: testo barra e righe menu separati |
| src/sysbar/app/application.py | modifica | Costruzione menu con metriche in cima, refresh live ogni campionamento |
| src/sysbar/ui/settings/settings_window.py | modifica | Sezione "Tray metrics" con menu a tendina a 3 scelte |
| data/io.github.AndreaBonn.Sysbar.gschema.xml | modifica | 6 nuove chiavi placement, vecchie chiavi booleane conservate per migrazione |
| tests/core/ | modifica | Test aggiornati per constants, validation, config |
| tests/app/ | modifica | Test aggiornati per tray_renderer e application |

### Note per il Cliente

Prima era possibile scegliere solo se mostrare o nascondere ciascuna metrica (CPU, GPU, memoria, rete, batteria, consumo energetico). Ora si può scegliere dove mostrarla: nella barra sempre visibile accanto all'icona, oppure nel pannello che si apre cliccando sull'icona, oppure nasconderla del tutto.

Chi aveva già configurato le metriche non deve fare nulla: all'avvio le impostazioni vengono convertite automaticamente e le metriche che erano accese si ritrovano nella barra come prima.

### Riepilogo

Complessità: alta - la modifica tocca configurazione, rendering, UI e schema GSettings con compatibilità verso le impostazioni esistenti.
Stato: completato - suite test verde al 100%, lint pulito, migrazione automatica verificata.
