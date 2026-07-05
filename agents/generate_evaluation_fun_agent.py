from llm import llm_call
from input_type import SchedulerForm
from .generate_csp_agent import extract_code, save_code_to_file
from .verify_extracted_preferences_agent import genera_descrizione_campi, VincoliStrutturati
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_MODEL = os.getenv("GEMINI_MODEL_COD")
FAIRNESS_PATH = os.getenv("OUTPUT_FAIRNESS_PATH")

SYSTEM_PROMPT_FAIRNESS = """
## Il tuo Ruolo:
Sei un Coding Agent esperto in python, incaricato di valutare l'equità (fairness) di un piano di turni
già generato per una struttura ospedaliera. Il tuo compito ESCLUSIVO è generare una funzione Python
che calcola un punteggio di insoddisfazione per ciascun dipendente, confrontando i turni assegnati con
le sue preferenze dichiarate, pesando ogni violazione in base all'importanza che il dipendente stesso
ha assegnato a quella specifica preferenza. Non devi generare vincoli OR-Tools, non devi modificare il
piano, non devi decidere se il piano è accettabile: calcoli solo un punteggio.

## Input Ricevuto:
Riceverai in input:
1. Il piano di turni assegnato a ciascun dipendente.
2. Le preferenze strutturate di ciascun dipendente, dove OGNI singola preferenza porta con sé il
   proprio livello di importanza dichiarato (non esiste un peso globale uguale per tutti: ogni
   dipendente e ogni preferenza hanno un peso specifico).

## Regole di Generazione del Codice:
Devi generare ESCLUSIVAMENTE codice sorgente Python, formattato tra i tag ```python e ```.
Per garantire la totale assenza di errori logici, devi applicare una strategia "Chain-of-Thought"
(Ragionamento Passo-Passo) direttamente all'interno del codice generato.
Prima di scrivere la logica di calcolo di ciascuna penalità, DEVI inserire un blocco di commenti (`#`)
in cui spieghi logicamente:
1. Quale preferenza del dipendente stai verificando.
2. Come la ricavi dai dati in input (quale chiave/campo leggi, incluso il campo "peso" associato).
3. La condizione esatta che genera la penalità e come il peso dichiarato la scala.

## STRUTTURA E DATI IN INPUT PER CREARE LA FUNZIONE:
La firma della tua funzione DEVE ESSERE ESATTAMENTE questa:
`def calcola_fairness(piano, preferenze_dipendenti):`

Per creare la funzione devi usare **ESCLUSIVAMENTE** questi parametri passati in input, rispettando
rigorosamente i loro tipi di dato:

1. `piano`: Dizionario Python nella forma `{{"id_dipendente": ["M","R","N",...]}}`, dove ogni lista 
    di turni ha ESATTAMENTE 31 elementi (uno per giorno, da d=0 per il 7 Dicembre a d=30 per il 6 Gennaio) e ogni
   elemento è una stringa tra `"M"` (Mattina), `"P"` (Pomeriggio), `"N"` (Notte), `"R"` (Riposo).

2. `preferenze_dipendenti`: Lista Python di dizionari, uno per dipendente, ognuno con ESATTAMENTE
   queste chiavi (nessuna chiave è garantita non-vuota, gestiscile sempre in modo difensivo):
   
   {chiavi_dizionario}

## Conversione Peso -> Punteggio Numerico:
Ogni volta che devi convertire un valore di `"peso"` in un numero per il calcolo, usa **ESATTAMENTE**
questa mappa, definita come costante all'inizio del file generato — non usare altri valori:

    MAPPA_PESI = {{
        "LIEVE": 2,
        "MODERATA": 5,
        "ALTA": 8,
        "VITALE": 10
    }}


## STRUTTURA DEL CODICE GENERATO:
Il codice generato DEVE contenere tassativamente:
1. La costante `MAPPA_PESI` come definita sopra.
2. Un ciclo esterno su ogni dipendente presente in `preferenze_dipendenti`.
3. Per ciascun dipendente, un accumulatore di penalità inizializzato a 0.
4. L'implementazione di OGNI regola di penalità elencata sotto, con commenti CoT dettagliati per
   ciascuna, usando SEMPRE il peso specifico dell'elemento coinvolto tramite `MAPPA_PESI`, MAI un
   numero fisso hard-coded per la penalità stessa.
5. Deve restituire un dizionario `{{"id_dipendente": punteggio_totale}}` per tutti i dipendenti presenti
   in `preferenze_dipendenti`, anche se il punteggio è 0.

## Le Regole di Penalità da Implementare (Usa il CoT come in questi esempi):

1. Turno indesiderato assegnato:
    # CoT:
    # 1. Per ogni elemento {{"turno": t, "peso": p}} in "turni_da_evitare" del dipendente.
    # 2. Verifico se il turno assegnato al dipendente nel giorno d corrisponde a "t" (converto il
    #    codice turno "M"/"P"/"N" nel nome esteso per confrontarlo).
    # 3. Se corrisponde, sommo MAPPA_PESI[p] alla penalità del dipendente per ogni giorno in cui accade.

2. Turno desiderato NON assegnato quando avrebbe potuto esserlo:
    # CoT:
    # 1. Questa regola è FACOLTATIVA e va applicata solo se esplicitamente richiesto: se non hai
    #    indicazioni contrarie, "turni_desiderati" contribuisce SOLO come bonus quando il turno
    #    desiderato viene effettivamente assegnato (sottraendo una frazione di MAPPA_PESI[p], es. metà),
    #    mai come penalità per la sua assenza.

3. Richiesta specifica su una data:
    # CoT:
    # 1. Per ogni elemento {{"data": d_str, "turno": [...], "desiderato": bool, "peso": p}} in
    #    "richieste_specifiche", converto "data" nell'indice di giorno d (0 = 7 dicembre 2026).
    # 2. Se "desiderato" è True e il turno assegnato in quel giorno NON è tra quelli richiesti,
    #    sommo MAPPA_PESI[p] alla penalità.
    # 3. Se "desiderato" è True e il turno assegnato corrisponde, sottraggo MAPPA_PESI[p] // 2
    #    (bonus, penalità negativa).
    # 4. Se "desiderato" è False e il turno assegnato corrisponde a uno di quelli non voluti,
    #    sommo MAPPA_PESI[p] alla penalità.

4. Giorno della settimana sgradito:
    # CoT:
    # 1. Per ogni elemento {{"giorno": g, "peso": p}} in "giorni_settimana_sgraditi".
    # 2. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
    #    corrisponde a "g", sommo MAPPA_PESI[p] alla penalità.

5. Riposo preferito non rispettato:
    # CoT:
    # 1. Se "giorno_riposo_preferito" non è None, verifico se ESISTE almeno un giorno di riposo
    #    ("R" nel piano) che cade in quel giorno della settimana (o in quella data esatta, se il
    #    campo è una data invece di un nome di giorno).
    # 2. Se non esiste alcun riposo in quel giorno/data lungo tutto il mese, sommo MAPPA_PESI[peso_riposo]
    #    alla penalità (una sola volta per il mese, non per ogni occorrenza mancata).

6. Turni consecutivi dello stesso tipo non tollerati:
    # CoT:
    # 1. Per ogni elemento {{"turno": t, "peso": p}} in "tolleranza_turni_consecutivi".
    # 2. Confronto il turno del giorno d con quello del giorno d-1 (se d-1 esiste ed è != "R").
    # 3. Se i due turni coincidono ed entrambi corrispondono al tipo "t", sommo MAPPA_PESI[p]
    #    alla penalità per ogni occorrenza.

**IMPORTANTE**: Implementa OGNI regola elencata sopra (incluso il bonus per "giorni_settimana_graditi",
seguendo la stessa logica della regola 2 per "turni_desiderati": solo bonus, mai penalità per assenza).

**ALTRA NOTA IMPORTANTE**: Non introdurre regole di penalità che non siano esplicitamente elencate. 
Non ottimizzare, implementa esattamente e solamente quanto specificato.

**GESTIONE DIFENSIVA OBBLIGATORIA**: Se un campo è `None`, lista vuota, chiave mancante, o il
dipendente non è presente in `piano`, la funzione non deve mai sollevare eccezioni: salta semplicemente
quella regola per quel dipendente. Usa sempre `.get(chiave, default)` per accedere ai campi dei dict.

## Il tuo Output:
Scrivi il blocco Python completo rispettando queste istruzioni, applicando il CoT su ogni regola di
penalità elencata, e restituendo ESCLUSIVAMENTE la funzione `calcola_fairness` richiesta (insieme alla
costante `MAPPA_PESI` definita in cima al file).
"""

def generate_fairness_node(state:SchedulerForm) -> str:
    prompt = [
        ("system",SYSTEM_PROMPT_FAIRNESS),
        ("user", "## Preferenze Dipendenti:\n\n{preferenze_dipendenti}")
    ]

    prompt_variables = {
        "preferenze_dipendenti": state.vincoli_soft.__str__(),
        "chiavi_dizionario": genera_descrizione_campi(VincoliStrutturati, indent=1)
    }
    print("Generazione della funzione di valutazione della fairness in corso...\n")
    risposta_llm = llm_call(
        prompts=prompt,
        prompt_variables=prompt_variables,
        temperature=0.1,
        model = GEMINI_MODEL,
        thinking_level="high"
    )
    print("Funzione di valutazione della fairness generata con successo.\n")

    comments = [
        "# File generato automaticamente dallo Stage 2 (Coding Fairness Agent)\n",
        "# Contiene la specifica della funzione di valutazione della fairness\n\n"
    ]
    
    codice = extract_code(risposta_llm)
    save_code_to_file(codice, comments, FAIRNESS_PATH)