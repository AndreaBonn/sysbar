# Spec 002: logica pura fuori dai moduli omessi dalla coverage

Richiesta: audit della qualità dei test e scomposizione dei moduli che concentrano logica non
misurata, per portare la copertura effettiva (non solo metrica) al massimo raggiungibile senza
separare gruppi logici coesi. Commit atomici su `main`, suite verde dopo ogni passo.

## Requisiti

- R1: ogni decisione con almeno due esiti osservabili oggi in un modulo escluso dalla coverage e
  elencata come "estrai" in `plan.md` vive in un modulo misurato, con test comportamentali a
  valori concreti visti rossi prima del verde.
- R2: nessun comportamento osservabile cambia: smoke UI sotto xvfb, gate traduzioni e suite unit
  restano verdi dopo ogni commit; i msgid spostati sono identici byte per byte.
- R3: nessuna voce nuova in `[tool.coverage.run] omit` né nelle allowlist di
  `tests/test_source_limits.py`; le voci `_create_session` e `parse_upower_devices` escono.
- R4: line coverage 100% sul codice misurato; branch coverage (`--cov-branch`) non inferiore alla
  baseline; i rami parziali residui sono solo quelli classificati irraggiungibili.
- R5: i `match` che il type checker non verifica (apply.py, summary.py, editing.py) falliscono a
  typecheck su una variante nuova (`assert_never`).
- R6: la suite non tocca lo stato reale della sessione (dconf, home) di chi la esegue.
- R7: i test classificati DA RISCRIVERE e DEBOLE in `test-audit.md` sono riscritti, rimossi se
  duplicati, o lasciati con motivo dichiarato.
- R8: il gate traduzioni esercita ogni ramo dei moduli puri nuovi che emette stringhe utente.
- R9: i problemi di correttezza emersi durante il lavoro (es. errore ingoiato in
  `keep_awake/inhibitor.py`) sono corretti con test, o segnalati con motivo se fuori portata.
