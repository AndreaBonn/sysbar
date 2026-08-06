# Piano: split del wiring, azioni scriptabili, command palette, scene utente

Slug: `001-app-wiring-actions-palette-scenes`
Stato: in attesa di approvazione
Data: 2026-08-06

## Obiettivo

Portare `src/sysbar/app/application.py` da monolite di wiring (862 righe) a radice di
composizione sotto le 300 righe, e costruirci sopra tre feature che trasformano nove
utility affiancate in un sistema: azioni scriptabili da CLI e D-Bus, una command palette
su hotkey unica, scene definite dall'utente con trigger automatici.

Il blocco 0 non produce valore utente. È un abilitatore dichiarato: senza di esso i tre
blocchi successivi riportano `application.py` oltre le 1200 righe.

## Definition of Done

### Blocco 0, split del wiring

- Nessun file sotto `src/` supera 300 righe, nessuna funzione supera 30 righe, nessun
  costruttore supera 4 parametri. Verificato da un test di gate, non a occhio.
- Nessun tipo `X | None` di una feature attraversa il confine del proprio modulo:
  l'interfaccia esposta è totale (`state()` restituisce sempre un valore, `toggle()` è
  no-op quando la feature è assente).
- `uv run ruff check`, `uv run mypy`, `uv run pytest` verdi, coverage >= 80% sul misurato.
- Ogni modulo nuovo è o testato o dichiarato in `[tool.coverage.run] omit` con motivazione
  scritta nel commento.
- Refactor a comportamento invariato: nessuna modifica utente-visibile, nessun cambio di
  chiave GSettings.
- Verifica runtime: il tray compare, si aprono panel, settings, shelf, clipboard e
  uninstaller, keep-awake commuta, il countdown scorre, il menu aperto tre volte di
  seguito non desincronizza gli stati.

### Blocco 1, azioni e CLI

- `busctl --user call io.github.AndreaBonn.Sysbar /io/github/AndreaBonn/Sysbar org.gtk.Actions List`
  elenca l'intero catalogo (>= 13 azioni: le 6 attuali più open-clipboard, activate-scene(s),
  clear-scene, toggle-microphone, toggle-dnd, toggle-dark-mode, toggle-focus-scene).
- `gapplication list-actions io.github.AndreaBonn.Sysbar` resta vuoto, ed è il
  comportamento accettato: `DBusActivatable=true` e il service file sono stati tolti dallo
  scope durante l'implementazione, con la motivazione registrata in `tasks.md`, sezione
  "Fuori scope dichiarato". La CLI non ne dipende, perché chiama `org.gtk.Actions.Activate`
  sull'istanza viva.
- `sysbar open-panel` con app in esecuzione apre il pannello dell'istanza viva,
  `pgrep -c -f sysbar` resta 1.
- `sysbar activate-scene focus` attiva la scena. `sysbar bogus` esce con 2 elencando le
  azioni valide. Con app spenta, `sysbar open-panel` esce con 1 e un messaggio esplicito.
- `sysbar --list-actions` stampa il catalogo. Un test asserisce che catalogo, azioni
  installate e choices della CLI provengono dalla stessa fonte.
- Le azioni indisponibili per capability assente sono registrate e disabilitate
  (`set_enabled(False)`), non omesse: i consumatori D-Bus hanno bisogno di nomi stabili.

### Blocco 2, command palette

- Una hotkey globale apre la finestra con il focus già nel campo di ricerca. Esc chiude,
  Invio invoca, le frecce navigano.
- Query vuota mostra i comandi principali raggruppati per categoria. Digitando si filtra
  su comandi, toggle, scene, voci di clipboard, item di shelf e device audio.
- Matcher coperto da test: match a sottosequenza, ordinamento per punteggio con bonus sui
  caratteri consecutivi e sull'inizio di parola, insensibile a maiuscole e accenti, nessun
  match produce lista vuota.
- Capability assente (nessun PipeWire) rimuove i comandi microfono e device dai risultati,
  senza crash.
- Le voci di clipboard classificate come probabile segreto sono mascherate di default,
  con rivelazione esplicita.
- La palette si chiude alla perdita di focus.
- Gate traduzioni verde con la nuova finestra aggiunta a `_exercise_windows`.

### Blocco 3, scene utente e trigger

- Creazione, modifica ed eliminazione di una scena dalla UI, con persistenza che sopravvive
  al riavvio.
- I tre preset non sono eliminabili. Modificarne uno crea un override ripristinabile, non
  muta la costante. Id duplicato rifiutato con messaggio.
- Con 0 e con 12 scene utente il conteggio dei nodi del menu dbusmenu è identico (test).
  Le scene oltre il pool restano raggiungibili da palette e CLI, ed è documentato.
- Un nome scena arbitrario (accentato, contenente `%`, assente dal catalogo `.po`) non fa
  fallire il gate traduzioni.
- Trigger "passaggio a batteria" e "monitor esterno collegato" attivano la scena scelta una
  sola volta per transizione. Oscillazioni dell'evento non producono un loop di attivazione.
- Una scena attivata a mano non viene mai sovrascritta da un trigger.
- Quando la condizione decade, la scena viene azzerata solo se la regola lo prevede e solo
  se è ancora quella attivata dal trigger.
- Interruttore globale che disattiva tutti i trigger.
- Nessun trigger può eseguire un comando arbitrario (vedi Vincoli di sicurezza).

## Assunzioni

- Target invariato: Ubuntu/GNOME su X11 e Wayland, GTK4 e libadwaita di sistema, venv
  `--system-site-packages`. Nessuna dipendenza nuova che non sia pure-Python.
- I quattro blocchi sono sequenziali, un branch per blocco, ognuno mergiato prima del
  successivo.
- La palette è una finestra GTK4 normale. Posizionamento esatto, centratura e keep-above
  non sono controllabili in modo portabile: il limite è già registrato per la shelf in
  `docs/DESIGN_DECISIONS.md`. L'accettazione è "si apre con il focus nel campo", non
  "si apre al centro dello schermo".
- Le scene utente non sono sincronizzate tra macchine né esportabili in questa versione.
- La coverage al 80% si applica al codice misurato: il glue GI resta escluso come oggi.

## Decisioni architetturali

### D1. Decomposizione: moduli feature a interfaccia totale

Il problema di `application.py` non è la lunghezza, sono i 20 attributi `| None`
capability-gated: ognuno propaga un `if self._x is not None` a ogni chiamante, quindi ogni
feature nuova costa righe in N punti invece che in 1. Tagliare per dominio senza togliere
gli Optional sposta le righe e basta.

Struttura adottata:

1. `app/features/<dominio>.py`, un modulo per feature (monitor con alerting, keep_awake,
   audio, quick_toggles, scenes, shelf, clipboard, auto_quit, uninstaller, update_check).
   Ognuno possiede la propria costruzione capability-gated e il proprio `| None` interno.
   Vincolo: l'interfaccia esposta è totale. Il degrado resta esplicito ma smette di essere
   un'informazione che viaggia fino ai chiamanti.
2. `app/windows.py`, `WindowSlot` generico su un Protocol `PresentableWindow`: apertura
   lazy e azzeramento su `close-request`. Oggi lo stesso pattern è ripetuto sei volte.
3. `app/tray_state.py`, funzioni pure da stato-feature a `QuickToggleState`,
   `SceneMenuEntry`, valori delle metriche, `TrayOptions`. Oggi sono metodi con `self` che
   leggono solo config e feature: estratte diventano misurabili, ed è il guadagno netto di
   coverage del blocco.
4. `application.py` resta con `do_startup` (lista di costruzione), la tabella di routing dei
   segnali e l'installazione delle azioni. Target 150-200 righe.

Scartate: il container DI con lookup per chiave (sotto mypy strict produce `Any` e `cast`
ovunque, e peggiora i test: popolare un container invece di passare due fake); lo split per
fase del ciclo di vita (l'accoppiamento resta identico, serve un context object gigante
passato in giro, è `application.py` con un altro nome).

La non-ricrescita non viene dall'astrazione, viene da una regola scritta: una feature nuova
è un file in `app/features/` più esattamente due righe in `application.py` (lista di
costruzione, routing dei settings). Se ne tocca tre, il confine è sbagliato. Va nel
`CLAUDE.md` di progetto, che oggi non esiste e viene creato nel blocco 0.

Le dipendenze cross-feature (scenes verso keep_awake, microfono, DND) restano parametri
espliciti del costruttore. Nessuna risoluzione automatica del grafo: sono tre archi.

### D2. Modello e persistenza delle scene

Persistenza su manifest JSON in `~/.local/share/sysbar/scenes/manifest.json`, con
`{"version": 1, "scenes": [...], "triggers": [...]}` in un unico documento: una sola
scrittura atomica, nessuna finestra in cui una regola punta a una scena non ancora salvata.
Scartato GSettings `a{sv}`: la struttura annidata a forma variabile richiede pack e unpack
a mano con controlli di tipo a runtime, lo schema XML non aiuta, e dconf non è ispezionabile
né condivisibile. Il parser va comunque scritto, tanto vale scriverlo su JSON, che è anche
il precedente già collaudato in `ShelfService` e `ClipboardService`.

Regola di progetto resa esplicita: scalari in GSettings, dati strutturati in JSON.
`active-scene` resta in GSettings perché è scalare.

Azioni modellate come unione discriminata di frozen dataclass, una per variante, con tag
`kind: Literal[...]` e dispatch `match/case` esaustivo. Mai `dict[str, object]`, mai `Any`
nei campi di dominio. Il round-trip `to_dict`/`from_dict` è per classe più una tabella
`_BY_KIND` in un solo modulo: l'unico punto non tipizzato è il boundary di parsing.
`from_dict` solleva su dato corrotto, `load()` cattura sull'intero manifest e degrada a
lista vuota con `log.warning`, come già fanno shelf e clipboard.

Varianti in questa versione: `SetToggle` (keep awake, DND, mute microfono), `SetSetting`
(chiave GSettings da whitelist), `SetOutputDevice` (il `DeviceSwitcher` esiste già).
Rinviate: `SetAppVolume`, `LaunchApp`, `CloseApp` e soprattutto `RunCommand`, che porta
quasi tutto il rischio di sicurezza e poco valore. L'unione le accoglie dopo al costo di una
dataclass.

L'applicazione di un'azione è una funzione pura `apply(action, ports) -> ActionOutcome` con
esito `applied | skipped(reason) | failed(reason)`: un'azione che richiede una capability
assente non è un errore, è uno skip dichiarato, e la UI può dire "3 azioni su 5 applicate".
I port sono per capability, non un metodo per booleano: altrimenti crescono a ogni azione.

Preset e scene utente sono lo stesso tipo, discriminati da `origin: StrEnum(BUILT_IN, USER)`,
mai da un flag `modified` che aprirebbe lo stato illegale "preset modificato che non è più un
preset". I preset restano costanti in codice, i loro nomi sono traducibili; il manifest
contiene scene utente e override dei preset in copy-on-write sullo stesso id. "Ripristina
preset" cancella l'override. La modifica di un preset è un fork via `dataclasses.replace`,
mai una mutazione in place.

### D3. Trigger: sorgenti di stato e token di proprietà

Un Protocol `TriggerSource` con `subscribe(on_state)`, N adapter, e un core di valutazione
puro `evaluate(rules, state, ownership) -> list[SceneCommand]`. L'astrazione esiste per
rendere mockabili i boundary, che è un bisogno reale e non speculativo, non per essere
generica: nessun DSL, nessuna condizione scritta dall'utente, set di condizioni chiuso.

Regola: `TriggerRule(id, condition, scene_id, restore_on_exit: bool)`. `condition` è
un'unione discriminata chiusa. Condizione singola, non congiunzione: l'AND richiede una UI a
tabella di verità e rende ambigua la semantica di uscita. È aggiungibile dopo come nodo
`AllOf([...])` nella stessa unione, senza rompere i dati persistiti. I trigger referenziano
la scena per id, mai per embedding: l'integrità referenziale è del service, non del dato.

Semantica di uscita: nessuno stack di ripristino, che si sfascia con regole sovrapposte e
cambi manuali in mezzo. Token di proprietà a slot singolo: la regola che attiva marca
`activated_by = rule_id`; quando la condizione decade, se `restore_on_exit` è vero e la scena
attiva è ancora quella e l'utente non l'ha cambiata a mano, si azzera; altrimenti non si fa
nulla. Zero storia da mantenere, comportamento spiegabile in una riga.

Conflitti: la lista delle regole è la priorità, vince la prima che soddisfa. Deterministico,
nessun ping-pong.

Idempotenza: le sorgenti emettono stato, non fronti. L'engine calcola la transizione, quindi
ri-applicare lo stesso stato non produce comandi per costruzione. Sulle soglie scalari,
isteresi (entra a <= 20%, esce a >= 25%). Sugli eventi discreti, debounce di circa 2 secondi
(l'hotplug di un monitor emette più eventi per un solo collegamento). Rate limit globale: al
massimo un'attivazione ogni N secondi, il resto loggato e scartato.

Sorgenti in questa versione, entrambe a zero nuovi boundary di sistema:

1. Monitor esterno collegato o scollegato, via `Gdk.Display.get_monitors()` e il suo segnale
   `items-changed`. Nessun D-Bus, il display è già nel processo. È il caso d'uso di punta.
2. Alimentazione e livello batteria, dal `SystemSnapshot` che il monitor già produce.
   `AlertEngine` valuta già una soglia batteria: il trigger è un secondo consumatore dello
   stesso stream.

Escluse: SSID via NetworkManager (boundary nuovo, valore marginale), applicazione aperta
(richiederebbe un fan-out del `WindowSource` oggi consumato solo da auto-quit) e fascia
oraria, che è la sorgente che genera più episodi di "il desktop è cambiato da solo". Il
modello `TriggerRule` le accoglie senza rotture quando servissero.

### D4. Catalogo comandi come costante, provider per i dati

La palette vorrebbe un registry dinamico, `menu_builder` ha l'invariante opposto: il
conteggio dei nodi non deve cambiare fra update, altrimenti l'host dbusmenu ricicla gli id
per posizione e lo stato si desincronizza. La tensione si scioglie osservando che
l'invariante riguarda i nodi, non i comandi: se la tabella dei comandi è una costante di
modulo, il conteggio dei nodi è costante per costruzione.

- `app/commands/` puro, senza import GI: `Command(id: CommandId, title, kind, requires)`,
  con `CommandId` enum.
- `application.py` costruisce `handlers: dict[CommandId, Callable]` in fase di wiring. Un
  test asserisce che ogni `CommandId` abbia un handler: esaustività a costo quasi nullo, e
  intercetta un drift che oggi non ha nessun sensore.
- GAction: registrare tutti i comandi allo startup, disabilitando gli indisponibili.
- CLI: `sysbar <command-id>` invoca `org.gtk.Actions.Activate` sull'istanza già viva, più
  `DBusActivatable=true` nel `.desktop`. Nessun IPC nuovo, nessun import di Gtk nel path
  della CLI (coerente con il conflitto GTK3/GTK4 già gestito in `tests/test_main.py`). App
  non in esecuzione significa errore esplicito ed exit 1, mai avvio automatico.
- Tray: `menu_builder` continua a scrivere il proprio albero a mano, consumando le costanti
  del catalogo per label e id. Raggruppamenti, separatori e sottomenu non sono esprimibili
  da una tabella piatta, e derivarli meccanicamente metterebbe a rischio l'invariante per un
  guadagno nullo.
- Cardinalità variabile non è un comando. Voci di clipboard, item di shelf, device audio e
  processi sono argomenti: vivono come provider (`search(query) -> list[PaletteEntry]`)
  consumati solo dalla palette, mai nel tray, mai come GAction.
- Disponibilità in una funzione sola: `availability(command_id, state) -> available |
  hidden | disabled(reason)`. Il tray nasconde, come fa oggi; la palette mostra disabilitato
  con il motivo.

Il tipo della voce di palette non è persistito, quindi non ha serializzazione. Lo stato
"visibile ma non attivabile" si elimina con un'unione `Runnable | Unavailable` sempre
presente sul campo di attivazione, mai con `available: bool` accoppiato a `Callable | None`.

## Vincoli di sicurezza non negoziabili

Derivano dalla review preventiva e valgono come criteri di accettazione:

- Il manifest delle scene è creato con permessi `0o600`.
- L'azione `RunCommand` è fuori dallo scope di questa versione. Quando verrà introdotta:
  disabilitata di default, tokenizzata con `shlex.split` in fase di salvataggio e non a
  runtime su stringa grezza, eseguita solo via `subprocess.run(lista, shell=False, timeout=...)`,
  con conferma esplicita legata all'hash del comando e non alla sola prima esecuzione.
- Nessun trigger automatico potrà mai innescare esecuzione di comandi o azioni distruttive
  senza interazione umana. L'enforcement vive nel service layer, non nella UI, altrimenti il
  canale D-Bus lo aggira per costruzione.
- Ogni azione D-Bus parametrica valida tipo e valore del parametro lato ricevente, con
  rifiuto esplicito e non trap silenzioso. Non vanno esposte come GAction le azioni la cui
  peggior conseguenza sia esecuzione di codice arbitrario o terminazione di processo
  arbitrario. `org.freedesktop.Application.ActivateAction` è lo stesso canale sotto altro
  nome e riceve la stessa validazione.
- La palette maschera di default le voci di clipboard classificate come probabile segreto e
  si chiude alla perdita di focus.
- Se emergesse il requisito "esegui comandi automaticamente su evento", la risposta corretta
  è rimandare a systemd user timers e units, che hanno tooling di audit standard, non
  costruire uno scheduler interno con permessi impliciti dentro un'app tray.

## Rischi

| Rischio | Mitigazione |
|---|---|
| Il refactor del blocco 0 rompe il wiring in silenzio: un `connect` perso non fa fallire nessun test, perché `application.py` è fuori coverage | Checklist di verifica runtime scritta prima dello split, con i comportamenti oggi funzionanti elencati uno per uno. Un commit per controller, così il bisect isola la regressione |
| `application.py` torna a gonfiarsi durante i blocchi 1-3 | Il size gate è un test, non una convenzione: fallisce in CI al primo sforamento |
| Il menu dbusmenu si desincronizza con scene a cardinalità variabile. Oggi l'invariante regge solo perché i preset sono tre e fissi | Pool fisso `MAX_SCENE_ROWS` con extra a `visible=False`, più un test che confronta il conteggio nodi a 0, 3 e 12 scene. Le scene oltre il pool restano raggiungibili da palette e CLI, documentato |
| Il gate traduzioni si rompe sui nomi definiti dall'utente: `menu_builder.py:186` passa `_(entry.name)`, quindi la CI pretenderebbe un msgid per ogni nome scena | Risolvere il display name a monte: preset tradotti, nomi utente verbatim. Test anti-regressione dedicato. Il difetto è latente già oggi e va corretto per primo |
| Coverage sotto soglia perché i moduli estratti non sono testati | Regola operativa: nessun modulo nuovo esce da un blocco senza essere o testato o in `omit` con commento. `--cov-report=term-missing` è già attivo |
| Palette inusabile su Wayland per focus, posizione o keep-above | L'accettazione è il focus nel campo, non la posizione. Verifica su entrambe le sessioni prima di chiudere il blocco. Se il focus non arriva, degradare dichiarando il limite come già fatto per la shelf |
| `DBusActivatable=true` cambia il modo in cui GNOME lancia l'app, con rischio di doppie istanze o avvio fallito senza service file | Il sub-task include il service file `dbus-1` e un test di packaging, più la verifica manuale del lancio da dock e da autostart |
| I trigger combattono l'utente | Token di proprietà, mai override di un'attivazione manuale, ripristino solo opt-in per regola, notifica a ogni scatto, interruttore globale |
| Esplosione dello scope dei trigger | Due sole sorgenti, entrambe già nel processo. Qualunque richiesta di SSID, app aperte o orario va ripianificata, non assorbita |
| `ShelfItem` (`src/sysbar/services/shelf/models.py:19`) permette di costruire stati illegali, con invariante affidata alla sola docstring | Difetto pre-esistente fuori scope. Segnalato, non corretto in questo piano salvo richiesta |

## Stima

Circa 9-12 giorni di lavoro sui quattro blocchi, con il buffer già incorporato. Il rischio
principale non è il codice ma la verifica runtime GTK, che non è automatizzabile e va
ripetuta su X11 e su Wayland.

Punto di decisione naturale: i blocchi 0 e 1 valgono circa 3-4 giorni, non introducono UI
nuova e rendono Sysbar scriptabile da subito. Sono consegnabili e valutabili prima di
impegnarsi su palette e scene.

## Criteri di verifica

```
uv run ruff check . && uv run mypy && uv run pytest          # floor a ogni blocco
uv run pytest --cov=sysbar --cov-report=term-missing         # >= 80% sul misurato
xvfb-run -a uv run pytest -m ui                              # gate traduzioni e smoke finestre
wc -l $(find src -name '*.py') | sort -rn | head             # nessun file oltre 300
busctl --user call io.github.AndreaBonn.Sysbar /io/github/AndreaBonn/Sysbar org.gtk.Actions List
gapplication list-actions io.github.AndreaBonn.Sysbar
sysbar --list-actions && sysbar open-panel && sysbar bogus; echo $?
```

Più le verifiche osservabili non automatizzabili elencate nelle DoD: menu aperto tre volte
senza desincronizzazione, palette su X11 e su Wayland, scena utente sopravvissuta al
riavvio, trigger batteria e monitor che scattano una volta sola per transizione.
