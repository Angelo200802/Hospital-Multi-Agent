# 🏥 Smart Scheduler

## 1. Introduzione

Il presente progetto illustra la progettazione e lo sviluppo di un sistema multi-agente avanzato nato per automatizzare e ottimizzare la pianificazione dei turni all'interno di un contesto ospedaliero. L'obiettivo fondamentale del sistema è generare turnazioni bilanciate che rispettino rigorosamente i requisiti istituzionali e legali (vincoli *hard*), tenendo contemporaneamente conto delle preferenze personali e del benessere del personale sanitario per garantire un'equa distribuzione del carico di lavoro (vincoli *soft*).

Nelle sezioni successive verranno discusse nel dettaglio le **scelte progettuali** che hanno guidato lo sviluppo e verranno analizzati i risultati ottenuti in due scenari applicativi distinti: il **Caso d'Uso A** (gestione di lavoratori standard) e il **Caso d'Uso B** (che introduce requisiti di presidio per lavoratori specializzati).
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

## 2. Struttura del Flusso

Il sistema è orchestrato tramite una automa a stati finiti (implementata avvalendosi della libreria `LangGraph`), che modella in modo le iterazioni tra gli agenti LLM e i risolutori simbolici. 

Il grafo di esecuzione (Figura 1) si articola in una serie di nodi (che rappresentano le azioni degli agenti) e archi condizionali (che implementano la logica di *routing* e i cicli di retroazione).

![Figura 1: Flusso del Multi Agente implementato con la libreria `langgraph`.](Smart%20Scheduler/workflow_graph.png)

Figura 1: Flusso del Multi Agente implementato con la libreria `langgraph`.

**1. Fase di Inizializzazione ed Estrazione delle Preferenze (Stage 1)** Il processo inizia dal nodo di ingresso **`__start__`** e procede verso la gestione delle preferenze:

- **extract_preferences_node**: L'LLM analizza il file di testo in linguaggio naturale, estraendo le richieste di ferie, le indisponibilità e i desiderata sui turni dei singoli dipendenti, convertendoli in un formato JSON strutturato.
- **verify_extracted_preferences_node**: Questo nodo funge da validatore semantico e strutturale per le preferenze estratte.
- **correct_preferences_node**: Se il nodo di verifica rileva anomalie o formattazioni errate nell'output dell'LLM, il flusso viene deviato tramite un arco condizionale verso questo nodo di correzione. Si instaura così un *loop* locale che garantisce che il sistema non proceda fino a quando il dizionario delle preferenze non è perfettamente coerente.

**2. Generazione della Bozza (Stage 2)** Una volta validate le preferenze, il grafo transita al:

- **generate_plan_node**: In questa fase il sistema genera la prima allocazione base dei turni. Sfruttando la logica ibrida, questa primissima matrice viene generata in modo da incastrare perfettamente le coperture richieste e i riposi senza violare le normative.

**3. Verifica dei Vincoli e della Fairness (Stage 3)** Il piano appena generato passa al vaglio dei nodi di controllo:

- **verify_hard_constraints_node**: L'agente simbolico (*Verification Agent* basato su OR-Tools) controlla matematicamente il piano. Da qui si snodano tre possibili percorsi (archi condizionali):
    1. Se la primissima bozza fallisce, il sistema torna a **`generate_plan_node`**.
    2. Se una bozza *raffinata* (proveniente dallo Stage 4) fallisce, il sistema ripristina l'ultimo piano valido e forza la terminazione dirigendosi a **`output_finale_node`**.
    3. Se il piano supera i vincoli di legge (è *feasible*), il sistema procede a calcolarne l'equità.
- **evaluate_fairness_node**: Questo nodo quantifica le metriche di soddisfazione (*Fairness*) e individua il dipendente più "sfortunato". Viene aggiornato e salvato il **`best_plan`** e si valuta la condizione di terminazione. Se l'equità può ancora essere migliorata, il flusso viene inviato al raffinamento; se si raggiunge uno stallo (il nuovo sfortunato sta peggio del precedente), il flusso va direttamente all'output finale.

**4. Raffinamento Iterativo (Stage 4)**

- **refine_plan_node**: Il piano valido, unito al feedback sul dipendente più sfortunato, viene passato nuovamente all'LLM. L'agente applica "correzioni chirurgiche"  per migliorare la condizione dello svantaggiato. L'output viene quindi re-immesso nel **`verify_hard_constraints_node`**, creando il **ciclo di ottimizzazione iterativo principale** del sistema.

**5. Terminazione e Output**

- **output_finale_node**: Raggiunto quando il sistema soddisfa uno dei criteri di stop (impossibilità di migliorare la fairness senza peggiorare il benessere generale o generazione di un piano *infeasible*). Il nodo si occupa di recuperare l'ultimo piano ottimale, di salvarlo e concludere l'esecuzione terminando nel nodo **`__end__`**.

## 3. Struttura Dati

#### 3.1 **Gestione dello Stato**

Nell'architettura multi-agente il passaggio di informazioni tra i vari agenti e risolutori avviene attraverso un singolo oggetto di stato condiviso. Questo stato è formalizzato dalla classe **`SchedulerForm`**, un modello Pydantic (**`BaseModel`**) che funge da "memoria globale" del sistema.

```python
from pydantic import BaseModel

class SchedulerForm(BaseModel):
    # Input iniziale
    input: str
    start_time: float = None
    # Fase 1a/4: Estrazione preferenze
    vincoli_soft: VincoliStrutturati = None      
    # Fase 1b/4: Verifica preferenze estratte
    preferenze_valide: PreferenzeValidate = None
    n_iter_correzioni: int = 0
    
    # Fase 2/4: Bozza del piano
    best_plan: Piano = None
    piano_attuale: Piano = None    
    n_iter_piano: int = 0
   
    # Fase 3a/4: Verifica vincoli Hard
    hard_constraints_valid: bool = None    
    feedback_errori_hard: str = None        
    n_iter_raffinazioni : int = 0
    
    # Fase 3b/4: Valutazione Fairness
    dipendente_piu_sfortunato: list[str] = []  
    fairness_score: dict[str, float] = None             

    # Criteri di terminazione
    condizione_di_stop : str = None
    terminazione_raggiunta: bool = None  
```

La struttura dello stato è logicamente suddivisa nelle fasi operative del framework:

- `input`: Contiene il testo grezzo iniziale fornito al sistema
- `start_time`: Utilizzato per il tracciamento delle performance temporali
- `vincoli_soft`: Memorizza l'output strutturato generato dall’ *Agente di Estrazione Preferenze.*
- `piano_attuale`: È la matrice di turnazione in lavorazione, viene sovrascritta a ogni iterazione dall’Agente di Generazione del Piano.
- `best_plan`: Memorizza l'ultimo piano matematicamente valido (*feasible*) che ha ottenuto il punteggio di *fairness* più alto.
- `fairness_score`: Un dizionario che mappa ogni dipendente al proprio indice quantitativo di soddisfazione
- `hard_constraints_valid`**:** ndica in modo inequivocabile se il **`piano_attuale`** rispetta i limiti di legge
- `dipendente_piu_sfortunato`: Una lista che identifica i lavoratori con il punteggio di fairness più basso.
- `terminazione_raggiunta`: Flag booleano che, quando impostato a **`True`**, interrompe il ciclo iterativo e dirigersi al nodo di output finale.
- `condizione_di_stop`: Una stringa di log che documenta il motivo esatto per cui l'algoritmo si è arrestato.

#### **3.2 Formalizzazione delle Preferenze**

Il campo `VincoliStrutturati` è una lista di `PreferenzeDipendente`, essa definisce lo schema dati utilizzato durante lo **Stage 1** dello Scheduler. 

Il loro scopo esclusivo è fungere da "ponte" standardizzato tra le richieste espresse in linguaggio naturale dai lavoratori e la logica computazionale del sistema.

```python
class PreferenzeDipendente(BaseModel):
    id_dipendente: str = Field(
	    ..., 
	    description="L'identificativo del dipendente (es. 'A')"
	  )
    is_specialised: bool = Field(
	    default=False, 
	    description="Indica se il dipendente è specializzato"
	  )
    
    turni_desiderati: List[CategoriaTurno] = Field(
	    default=[], 
		  description="Elenco dei turni preferiti"
		)
    turni_da_evitare: List[CategoriaTurno] = Field(
	    default=[], 
	    description="Elenco dei turni sgraditi"
	  )
    giorni_settimana_graditi: List[GiornoSettimana] = Field(
        default=[], 
        description="""Giorni della settimana ricorrenti in cui il dipendente 
        PREFERISCE lavorare (es. 'lunedì', 'martedì')"""
    )
    
    giorni_settimana_sgraditi: List[GiornoSettimana] = Field(
        default=[], 
        description="""Giorni della settimana ricorrenti in cui il dipendente 
        preferisce NON lavorare (es. 'venerdì', 'domenica')"""
    )
    richieste_specifiche: List[RichiestaSpecifica] = Field(
        default=[], 
        description="""Richieste esatte per date specifiche. 
        Se il dipendente non vuole lavorare in un giorno ricorrente 
        (es. 'venerdì'), deve contenere le date tra il 07-12-2026 
        e il 06-01-2027 e inserirle qui."""
    )
    
    max_emergenze: Optional[int] = Field(
	    default=None, 
	    description="Max turni di emergenza accettati"
	  )
    giorno_riposo_preferito: Optional[Union[GiornoSettimana, str]] = Field(
        default=None, 
        description="""Il riposo desiderato. 
        Può essere un giorno della settimana (es. 'domenica') 
        OPPURE una data specifica in formato YYYY-MM-DD (es. '2026-12-24')."""
    )
    tolleranza_turni_consecutivi: List[CategoriaTurno] = Field(
	    default=[], 
	    description="Combinazioni di turni consecutivi sgraditi (es. festivi)"
	   )
	   
	class VincoliStrutturati(BaseModel):
    preferenze_dipendenti: List[PreferenzeDipendente] = Field(
        description="""Lista delle preferenze strutturate per tutti 
        i dipendenti menzionati nell'input"""
    )
    
```

#### 3.3 Formalizzazione della Turnazione

Le classi **`TurniDipendente`** e **`Piano`** definiscono la struttura dati fondamentale per la rappresentazione e manipolazione dell'allocazione dei turni. Il loro scopo è convertire le assegnazioni in un formato standardizzato, tipizzato e orientato al codice, permettendo l'interoperabilità tra l'output generativo dell'LLM e la verifica matematica del risolutore OR-Tools.

```python
class TurniDipendente(BaseModel):
    id_dipendente: str = Field(
	    ..., 
	    description="L'identificativo del dipendente (es. 'A')"
	  )
    turni_assegnati: List[TurnoAssegnato] = Field(
	    default=[], 
	    description="Elenco dei turni assegnati al dipendente"
	  )

class Piano(BaseModel):
    
    assegnamenti: List[TurniDipendente] = Field(
	    default=[], 
	    description="Elenco degli assegnamenti dei turni per ogni dipendente")
```

Il **`Piano`** è modellato associando a ogni singolo lavoratore un array lineare di 31 elementi, in cui ogni cella rappresenta un giorno del mese e contiene un Enum rigido dei turni (**`M`**, **`P`**, **`N`**, **`R`**).

L’uso di questa strutture permette al modello linguistico di leggere una riga per dipendente per volta, permettendo anche ai *thinking tokens* dell'LLM di contare e validare facilmente il carico di lavoro.

Inoltre l'uso rigoroso di array tipizzati e classi di enumerazioni forza l'LLM a generare solo valori validi, garantendo che il JSON sia sempre decodificabile.

## 4. Modelli Usati

**Gemini 2.5 Flash**

Per quanto riguarda lo **Stage 1** del flusso si è optato per il modello `gemini-2.5-flash` che, prima di scrivere il JSON finale, esegue internamente una fase di ragionamento e scomposizione del testo tale da ridurre drasticamente gli errori di logica quando deve estrarre dati da testi ambigui o complessi.

Inoltre mantiene finestra da **1 milione di token** per gestire enormi quantità di testo in una sola richiesta, in questo modo può gestire testi contenenti le preferenze dei dipendenti di grandi dimensioni.

**Gemini 3.5 Flash**

Per la generazione (e raffinazione) delle turnazioni la scelta è ricaduta sul modello `gemini-3.5-flash` . Questa decisione è stata dettata dalla stringente necessità di dotare il sistema di capacità avanzate di ragionamento, fondamentali nel processare i vincoli orizzontali dei dipendenti e nel pianificare operazioni complesse di scambio turni.

Sebbene sul mercato esistano modelli dotati di abilità deduttive di altissima fascia (come **GPT-5.5** o lo stesso **Gemini 3.1 Pro**), l'utilizzo di questi comporta costi API significativamente più elevati rispetto al modello **3.5-Flash** il cui utilizzo è disponibile anche gratuitamente (seppur in modo limitato).

Dalla Figura 2, si può notare come il modello usato riesce ad ottenere prestazioni simili ai modelli migliori sui task di ragionamento, garantendo inoltre prestazioni anche più elevate sui task agentici.

![Figura 2: Confronto tra Gemini 3.5 Flash ed altri modelli con ragionamento.](Smart%20Scheduler/22a0156a-ba34-491c-a457-d30720782d24.png)

Figura 2: Confronto tra Gemini 3.5 Flash ed altri modelli con ragionamento.

## 5. Implementazione Agenti

### 5.1a Agente Estrazione Preferenze

Per gestire testi in input lunghi e narrativi, il prompt utilizza la tecnica della **Task Decomposition,** che invece di richiedere genericamente una strutturazione del testo, suddivide il compito in quattro step operativi esatti: 

- Individuare turni preferiti,
- Date Specifiche
- Indisponibilità Assolute
- Limiti per le Emergenze

Questa suddivisione guida l'LLM ed evita che il modello ometta di estrarre informazioni numeriche critiche.

Viene usato il **Few-Shot Prompting (In-Context Learning)** che in questo contesto serve a dimostrare all'LLM come mappare espressioni umane vaghe nei rispettivi array e valori booleani, garantendo che il modello capisca esattamente come nidificare i dizionari.

E’ stata impostata la **temperatura a 0.1** in modo da ottenere un comportamento strettamente deterministico, impedendo allucinazioni come l'invenzione di preferenze di ferie mai espresse o l'aggiunta di dipendenti inesistenti. Si fa un uso stringente della strutturazione dell'output (**`structured_output=VincoliStrutturati`**), imponendo uno schema JSON preciso

#### 5.1b Agente di Verifica Preferenze

Per garantire la massima affidabilità dei dati prima di passare alle fasi succesive, è stato introdotto il pattern di **Reflection (Multi-Agent)** anche alla fase di estrazione iniziale, configurando un setup di tipo *Dual Agent* (Correttore-Critico).

L'LLM assume il ruolo di revisore o "critico", questo serve a focalizzare l'attenzione del modello non sulla generazione di nuovi vincoli, ma sulla ricerca di discrepanze tra il testo umano e il JSON prodotto dall’agente precedente.

Anche in questo caso viene implementato il pattern della **Task Decomposition** in modo tale da costruire del feedback costruttivo per l’agente che dovrà svolgere le correzioni.

Viene inoltre introdotta la **Context Injection**, che inietta dinamicamente nel prompt la struttura esatta prevista dal modello `Pydantic` in questo modo, l'agente sa esattamente *quali* entità informative deve cercare e validare per ogni dipendente, impedendogli di valutare parametri fuori contesto.

Rispetto al caso precedente viene innalzato il parametro della temperatura in modo tale da garantire all’agente critico una formulazione dei suggerimenti linguisticamente chiara e utile, oltre ad una maggiore flessibilità semantica.

#### 5.1c Agente di Correzione Preferenze

### 5.2 Agente Generazione Piano

### 5.3a Agente Validatore

### 5.3b Agente Valutazione Fairness

### 5.4 Agente Raffinatore

## 6. Analisi dell’Output

Alla fine del processo di generazione del piano un ultimo agente simbolico viene incaricato di strutturare e salvare due file di output:

- **Audit Log:** un file JSON contenente informazioni di log sul processo generativo, come ad esempio il numero di iterazioni per generare il piano oppure il vettore dei payoff dell’assegnamento finale.
- **Tabella Excel:** file excel che contiene come righe i tre turni (Mattina, Pomeriggio e Notte) e come colonne i giorni che compongono l’arco temporale coperto dal piano. Ogni cella contiene l’id dei dipendenti che partecipano a quel turno.

### 6.1 Use Case A (Dipendenti Standard)

```json
{
    "dipendenti": [
        "A",
        "B",
        "C",
        "D",
        "E",
        "F",
        "G",
        "H",
        "I",
        "J",
        "K",
        "L",
        "M"
    ],
    "iterazioni_correzioni_preferenze": 3,
    "iterazioni_piano": 2,
    "iterazioni_raffinazioni": 1,
    "tempo_totale": 3363.464711666107,
    "fairness_score": {
        "E": 20.0,
        "D": 70.0,
        "G": 20.0,
        "J": 70.0,
        "A": 20.0,
        "B": 0.0,
        "C": 15.0,
        "F": 0.0,
        "H": 0.0,
        "I": 18.0,
        "K": 0.0,
        "L": 0.0,
        "M": 20.0
    },
    "dipendente_piu_sfortunato": [
        "D"
    ],
    "condizione_di_stop": "Fairness Score Peggiorato"
}
```

### 5.2 Use Case B (Dipendenti Specializzati)

```json
{
    "dipendenti": ["A","B","C","D","E","F","G","H","I","J","K","L","M","N","O",
    "P","Q","R","S"],
    "iterazioni_correzioni_preferenze": 1,
    "iterazioni_piano": 5,
    "iterazioni_raffinazioni": 1,
    "tempo_totale": 2280.049247741699,
    "fairness_score": {
        "G": 90.0,
        "S": 50.0,
        "A": 20.0,
        "B": 0.0,
        "C": 15.0,
        "D": 120.0,
        "E": 20.0,
        "F": 0.0,
        "H": 0.0,
        "I": 20.0,
        "J": 15.0,
        "K": 15.0,
        "L": 0.0,
        "M": 60.0,
        "N": 20.0,
        "O": 50.0,
        "P": 0.0,
        "Q": 0.0,
        "R": 0.0
    },
    "dipendente_piu_sfortunato": [
        "D"
    ],
    "condizione_di_stop": "Fairness Score Non Migliorato"
}
```