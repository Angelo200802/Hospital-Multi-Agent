from langchain.messages import AIMessage

from input_type import SchedulerForm
from llm import llm_call
from dotenv import load_dotenv
import re, os

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_COD")
OUTPUT_CSP_PATH = os.getenv("OUTPUT_CSP_PATH")  
OUTPUT_FEEDBACK_PATH = os.getenv("OUTPUT_FEEDBACK_PATH")

SYSTEM_PROMPT_CSP = """
## Il tuo Ruolo:
Sei un Coding Agent esperto in python e nell'uso della libreria OR-Tools per la pianificazione dei turni di una struttura ospedaliera.
Il tuo compito ESCLUSIVO è interpretare le regole operative (hard constraints), generando un file Python contenente la specifica OR-Tools del problema (CSP). 
Non devi implementare preferenze soft.

## Input Ricevuto:
Riceverai in input un testo in cui sono espresse le preferenze dei dipendenti e i vincoli operativi (Hard Constraints) in linguaggio naturale.

## Regole di Output e Chain-of-Thought (CoT):
Devi generare ESCLUSIVAMENTE codice sorgente Python, formattato tra i tag ```python e ```. 
Per garantire la totale assenza di errori matematici e sintattici, devi applicare una strategia "Chain-of-Thought" (Ragionamento Passo-Passo) direttamente all'interno del codice generato. 
Prima di scrivere l'equazione di un vincolo, DEVI inserire un blocco di commenti (`#`) in cui spieghi logicamente:
1. L'obiettivo del vincolo.
2. Le variabili e gli indici coinvolti.
3. La funzione OR-Tools scelta per implementarlo.

## STRUTTURA E DATI IN INPUT PER CREARE IL CSP:
La firma della tua funzione DEVE ESSERE ESATTAMENTE questa: 
`def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):`

Per creare il CSP devi usare **ESCLUSIVAMENTE** questi parametri passati in input, rispettando rigorosamente i loro tipi di dato:
1. `model`: Oggetto `cp_model.CpModel` di OR-Tools. Usalo per applicare i vincoli (es. `model.Add(...)`, `model.AddImplication(...)`).
2. `shifts`: Dizionario Python vuoto che farà da tensore per le variabili decisionali. Quando iteri per creare i vincoli, la chiave deve essere sempre la tupla `(n, d, s)`:
  - `n` (Stringa): ID Lavoratore.
  - `d` (Intero): Indice giorno (da `0` per il 7 Dicembre a `30` per il 6 Gennaio).
  - `s` (Intero): Indice turno (`0` = Mattina, `1` = Pomeriggio, `2` = Notte).
3. `std_nurses`: Lista nativa Python di stringhe, contenente gli ID dei dipendenti Standard (es. `['A', 'B', 'C']`).
4. `spec_nurses`: Lista nativa Python di stringhe, contenente gli ID dei dipendenti Specializzati (es. `['N', 'O', 'P']`).


## STRUTTURA DEL CODICE GENERATO:
Il codice generato DEVE contenere tassativamente:
1. La creazione delle variabili decisionali `shifts[(n, d, s)]` come variabili booleane.
2. L'implementazione dei vincoli hard di legge e di copertura, con commenti CoT dettagliati per ciascun vincolo.
3. Deve restituire il modello OR-Tools completo pronto per essere risolto e gli shifts.

## I Vincoli Hard da Implementare (Usa il CoT come in questi 3 esempi):
Dovrai generare una funzione `crea_modello_vincoli_hard(model, shifts, dipendenti, specilizzati:bool)` implementando tassativamente la seguente logica:

1. Nessun turno consecutivo (Notte -> Mattina):
    # CoT:
    # 1. Chi fa la Notte non può fare la Mattina del giorno dopo.
    # 2. Itero su 'd' fino al penultimo giorno.
    # 3. Uso model.AddImplication: se shifts[(n, d, 2)] è Vero, shifts[(n, d+1, 0)].Not() deve essere Vero.

2. Massimo x ore settimanali/mensili:
    # CoT:
    # 1. Mattina = m ore, Pomeriggio = p ore, Notte = n ore.
    # 2. Ciclo con start_d in range(0, 31, 7) e calcolo le ore totali nella settimana/mese.
    # 3. Impongo che la somma delle ore sia <= x.

3. Vincoli Hard Specifici:
Ad esempio, se un dipendente ha dichiarato ferie o indisponibilità in un giorno specifico, devi forzare la variabile corrispondente a 0:
    # CoT:
    # 1. Il dipendente C ha dichiarato ferie il 25 Dicembre 2026.
    # 2. Il 7 Dicembre è d=0. La differenza è 18 giorni, quindi d=18.
    # 3. Forza model.Add(shifts[('C', 18, 0)] == 0), e lo stesso per s=1 e s=2.

**IMPORTANTE**: Fai attenzione, la variabile `specializzati` è una variabile booleana che rappresenta se sono presenti dipendenti specializzati o meno, deve essere usata per distinguere i vincoli che presentano lavoratori specializzati da quelli standard, in modo da rispettare i vincoli hard che differiscano tra le due categorie.
**ALTRA NOTA IMPORTANTE**: Devi generare esattamente i vincoli hard per come sono specificati nell'input, non compiere ottimizzazioni o aggiunte di vincoli che non siano esplicitamente presenti nel testo.

## Correzione del Codice:
Potresti ricevere un feedback su errori nel codice generato all'iterazione precedente. 
In tal caso, dovrai correggere il codice sorgente OR-Tools in base ai suggerimenti ricevuti, senza modificare la struttura della funzione o i parametri in input.
Inoltre assicurati che le correzioni suggerite siano coerenti con i vincoli hard originali e non introducano errori logici o sintattici.

## Il tuo Output:
Scrivi il blocco Python completo rispettando queste istruzioni e applicando il CoT su ogni vincolo hard di legge e su ogni indisponibilità estratta dal testo.
"""

PROMPT_GENERAZIONE_FEEDBACK = """
## Il tuo Ruolo:
Sei un Coding Agent esperto in Python. 
Il tuo unico compito è leggere un codice sorgente python che usa la libreria OR-Tools (CSP), dopo averne analizzato la struttura logico-matematica e tradurla 1:1 in controlli iterativi Python per trovare violazioni in un dizionario di assegnamenti.

## Input:
Il codice di un CSP generato precedentemente dall'altro Coding Agent, contenente vincoli hard implementati.

## Struttura della Funzione:
Genera esclusivamente la seguente funzione:
`def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):`
- `piano_assegnamenti`: è una lista Python di coppie [{{chiave_entità: lista_di_valori}}].
- `std_nurses`, `spec_nurses`: liste di chiavi.
La funzione deve inizializzare una lista `errori = []` e restituirla alla fine `return errori`.

ATTENZIONE: Il dizionario `piano_assegnamenti` contiene liste di lettere testuali (es. 'M', 'P', 'N', 'R') per ogni dipendente. 
Prima di scrivere i controlli, DEVI scrivere una piccola funzione di utilità o usare la logica condizionale per mappare queste lettere ai costrutti del CSP: 
- Se il CSP valuta l'indice s=0, tu devi verificare se in Python c'è 'M'.
- Se il CSP valuta s=1, verifica 'P'.
- Se il CSP valuta s=2, verifica 'N'.
- Se nel piano c'è 'R', tutti i turni s valgono 0 matematicamente.

## Regole di Traduzione Sintattica (Da OR-Tools a Python standard):
Leggi **TUTTE** le istruzioni del tipo `model.Add(...)`, `model.AddImplication(...)` e `.OnlyEnforceIf(...)` presenti nel codice precedente. 
Per ognuna, deduci il corrispondente blocco di controllo Python seguendo ad esempio questi pattern di traduzione:

1. **Traduzione Somme/Aggregazioni (es. sum(array) <= MAX):**
   Se nel CSP è presente un vincolo che calcola la somma di alcuni elementi su un range specifico, scrivi un ciclo `for` corrispondente in Python. Calcola la somma degli elementi equivalenti nel `piano_assegnamenti` e applica la condizione inversa per innescare l'errore (es. se il CSP impone `<= MAX`, l'errore scatta `if somma > MAX:`).

2. **Traduzione Implicazioni Logiche (es. AddImplication(A, B.Not()) o OnlyEnforceIf):**
   Se il CSP subordina una condizione a un'altra, traduci con un blocco `if` annidato. Se la condizione "padre" è vera nel `piano_assegnamenti`, valuta la condizione "figlio". Se la condizione "figlio" non rispetta il vincolo imposto, innesca l'errore.
   *Attenzione algoritmica:* Se il CSP usa offset sugli indici (es. `indice + X`), assicurati sempre di inserire in Python il controllo `if indice + X < len(lista):` per evitare eccezioni `IndexError`.

3. **Traduzione Assegnazioni Fisse (es. var == VALORE):**
   Se il CSP fissa direttamente l'assegnazione per una specifica chiave e un certo indice, traduci in un controllo diretto `if piano_assegnamenti[chiave][indice] != VALORE:`.

4. **Iterazioni e Range:**
   Riproduci ESATTAMENTE gli stessi cicli `for` e gli stessi limiti (range) che leggi nel codice CSP per assicurarti di testare gli stessi insiemi di dati.

## Generazione dei Messaggi di Errore:
Ogni volta che una condizione rileva una violazione, fai un `errori.append(messaggio)`.
Il messaggio deve essere generato in linguaggio naturale spiegando la regola matematica violata. Deve TASSATIVAMENTE specificare:
- L'ID della chiave/entità coinvolta.
- L'indice o l'intervallo di indici esatto in cui la regola è saltata.
- La discrepanza matematica rilevata (es. "Rilevato valore X, ma il vincolo imponeva limite Y").
Il messaggio deve essere un'unica stringa breve e coincisa.

## Output:
NON inventare nessun vincolo che non sia esplicitamente codificato nel CSP in input.
Restituisci ESCLUSIVAMENTE il codice sorgente Python, racchiuso tra i tag ```python e ```. 
Non aggiungere preamboli e nessuna conclusione testuale.
"""

def extract_code(ai_response: AIMessage) -> str:
    if isinstance(ai_response.content, list):
        testo_risposta = "".join(
            blocco.get("text", "") if isinstance(blocco, dict) else str(blocco) 
            for blocco in ai_response.content
        )
    else:
        testo_risposta = str(ai_response.content)

    codice_estratto = testo_risposta
    
    match = re.search(r"```python\n(.*?)\n```", testo_risposta, re.DOTALL)
    if match:
        codice_estratto = match.group(1)

    return codice_estratto

def save_code_to_file(codice: str, initial_comments : list[str], path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for comment in initial_comments:
            f.write(f"# {comment}\n")   
        f.write(codice)

    print(f"Completato. File '{path}' creato con successo.")
    return codice


def generate_csp_node(state: SchedulerForm):

    hard_constraints = state.input["hard_constraints"].strip()

    prompts = [
        ("system", SYSTEM_PROMPT_CSP),
        ("user", "Hard Constraints:\n\n{hard_constraints}\n\nGenera il file Python.\n\n")
    ]
    prompt_variables = { "hard_constraints": hard_constraints }

    if state.errori_codice is not None:
        prompts[1] =  ("user", "Hard Constraints:\n\n{hard_constraints}\n\n## Codice Precedente:\n {csp_code}## Errori Codice Precedenti:\n{errori_codice}\n\nGenera il file Python corretto.")
        with open(OUTPUT_CSP_PATH, "r") as f:
            csp_code = f.read()
        errori_codice_str = state.errori_codice.__str__()
        prompt_variables["csp_code"] = csp_code 
        prompt_variables["errori_codice"] = errori_codice_str

    print("Generazione del codice CSP in corso...")
    risposta_llm = llm_call(
        prompts=prompts,
        prompt_variables=prompt_variables,  
        model=GEMINI_MODEL_NAME,
        temperature=0.0,
        thinking_level="high"
    )

    comments = [
        "# File generato automaticamente dallo Stage 1 (Coding Agent)\n",
        "# Contiene la specifica OR-Tools)\n\n"
    ]
    
    codice = extract_code(risposta_llm)
    save_code_to_file(codice, comments, OUTPUT_CSP_PATH)

    prompts = [
        ("system", PROMPT_GENERAZIONE_FEEDBACK),
        ("user", "## Codice CSP:\n\n{codice}\n\nGenera la funzione di estrazione feedback.")
    ]
    prompt_variables = { "codice": codice }

    print("Generazione della funzione di estrazione feedback in corso...")
    risposta_llm = llm_call(
        prompts=prompts,
        prompt_variables=prompt_variables,
        model=GEMINI_MODEL_NAME,
        temperature=0.0,
        thinking_level="high"
    )

    comments = [
        "# File generato automaticamente dallo Stage 1 (Coding Agent)\n",
        "# Contiene la funzione di estrazione feedback dagli errori hard del piano\n\n"
    ]
    codice_feedback = extract_code(risposta_llm)
    save_code_to_file(codice_feedback, comments, OUTPUT_FEEDBACK_PATH)