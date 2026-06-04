# 🏥 Progetto AI - Scheduler Turni Ospedalieri

Questo progetto implementa un flusso multi-agente per la pianificazione dei turni ospedalieri, combinando:

- estrazione semantica delle preferenze da testo naturale (LLM),
- generazione/raffinamento iterativo del piano,
- verifica dei vincoli hard con approccio simbolico,
- valutazione della fairness del risultato.

L’orchestrazione è gestita con `LangGraph`.

---

## Struttura del progetto

- `main.py`: entrypoint del workflow.
- `input_type.py`: modelli Pydantic, enum e stato condiviso (`SchedulerForm`).
- `csp.py`: logica OR-Tools per vincoli hard.
- `agents/`:
	- `extract_preferences_agent.py`: parsing preferenze tramite Gemini.
	- `generate_or_refine_plan_agent.py`: generazione/raffinamento piano.
	- `verify_evaluate_agent.py`: verifica hard + fairness.
	- `return_output_agent.py`: formattazione output finale.
- `input/preferences.txt`: file di esempio con preferenze in linguaggio naturale.

---

## Requisiti

- Python 3.10+ (consigliato 3.11)
- `pip`
- Chiave API Google/Gemini valida

---

## Installazione in locale

1. Clona il repository:

	```bash
	git clone <URL_DEL_REPOSITORY>
	cd <NOME_CARTELLA_PROGETTO>
	```

2. Crea e attiva un ambiente virtuale:

	```bash
	python3 -m venv .venv
	source .venv/bin/activate
	```

3. Installa le dipendenze:

	```bash
	pip install --upgrade pip
	pip install -r requirements.txt
	```

4. Crea il file `.env` nella root del progetto.
4. Crea il file `.env` nella root del progetto.

---

## Variabili `.env` da configurare

Nel file `.env` inserisci:

```env
# OBBLIGATORIA: nome del file in input
INPUT_FILE_NAME = nome_file.estensione
# OBBLIGATORIA: chiave API Gemini/Google
GEMINI_API=la_tua_api_key
# OPZIONALE: modello da usare (se omessa usa il default nel codice)
GEMINI_MODEL=gemini-2b
```

Se necessario, aggiorna anche il percorso del file di input in `main.py` in base alla posizione del file di testo.

## Avvio del progetto

Con ambiente virtuale attivo e `.env` configurato:

```bash
python main.py
```

Il workflow leggerà il file input indicato in `main.py` e stamperà il risultato finale.

---
