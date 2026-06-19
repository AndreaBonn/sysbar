[English](SECURITY.md) | **Italiano**

# Politica di sicurezza

## Versioni supportate

| Versione | Supportata |
|---|---|
| 0.3.x | Sì, ultima release |
| < 0.3 | No |

Sysbar è in sviluppo attivo. Le correzioni di sicurezza sono applicate
all'ultima release e al `main` corrente.

## Segnalare una vulnerabilità

Per segnalare una vulnerabilità di sicurezza, usa i [GitHub Security
Advisories](https://github.com/AndreaBonn/sysbar/security/advisories/new).

Includi:
- Descrizione della vulnerabilità
- Passi per riprodurla
- Comportamento atteso e comportamento osservato
- Valutazione dell'impatto (cosa potrebbe ottenere un attaccante)

Tempi di risposta:
- Presa in carico: entro 72 ore
- Fix per problemi critici: entro 30 giorni
- Divulgazione pubblica coordinata dopo il rilascio del fix

## Misure di sicurezza implementate

Sono le misure verificate nel codice, non dichiarazioni di intenti.

- **Superficie di rete minima**: l'unica chiamata di rete dell'app è un controllo
  aggiornamenti opzionale verso la GitHub Releases API su HTTPS, disabilitabile
  tramite l'impostazione `auto-check-updates` e limitato da un timeout di 5
  secondi (`src/sysbar/services/update_service.py`). L'altra uscita di rete è la
  metrica di velocità della rete (`src/sysbar/services/metrics/speedtest.py`).
  Nessun account, nessuna telemetria.
- **Nessuna shell injection**: i comandi esterni passano da `subprocess` con
  argomenti come lista, mai `shell=True` (verificato su tutto `src/`;
  `src/sysbar/services/uninstall/command_query.py`,
  `src/sysbar/services/uninstall/package_remover.py`).
- **Operazioni privilegiate dietro polkit**: la rimozione dei pacchetti è
  delegata al package manager di sistema sotto autorizzazione polkit, non
  eseguita come chiamata privilegiata diretta
  (`src/sysbar/services/uninstall/package_remover.py`).
- **Nessun secret**: l'app non memorizza credenziali o token. La configurazione
  runtime vive in GSettings; in produzione non servono variabili d'ambiente
  (`.env.example`).
- **Pinning delle dipendenze**: l'insieme di dipendenze risolto è committato in
  `uv.lock`.

## Best practice per gli utenti

- Installa solo dalla [pagina delle release
  ufficiali](https://github.com/AndreaBonn/sysbar/releases) o dal repository APT
  firmato, e verifica lo SHA256 pubblicato del `.deb` prima di installare.
- Mantieni aggiornati i binding GTK di sistema tramite la tua distribuzione.

## Fuori ambito

I seguenti casi non sono considerati vulnerabilità per questo progetto:

- Attacchi di ingegneria sociale
- Attacchi fisici alla macchina
- Vulnerabilità in dipendenze di terze parti già divulgate pubblicamente
  (segnalale al maintainer upstream)
- Denial of service tramite uso legittimo eccessivo

## Riconoscimenti

I ricercatori di sicurezza che divulgano responsabilmente le vulnerabilità
saranno elencati qui.

---

[Torna al README](./README.it.md)
