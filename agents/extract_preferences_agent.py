from input_type import SchedulerForm, VincoliStrutturati
from llm import llm_call
from dotenv import load_dotenv
import re, os

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_GEN")
OUTPUT_CSP_PATH = os.getenv("OUTPUT_CSP_PATH")  


SYSTEM_PROMPT = """
## Il tuo ruolo:
Sei un assistente intelligente incaricato di estrarre e strutturare le preferenze dei dipendenti di una struttura ospedaliera per la pianificazione dei turni. 

## Input Ricevuto:
Riceverai in input un testo in cui sono espresse le preferenze degli impiegati in linguaggio naturale, ad esempio:
   - "Il dipendente A preferisce i turni di mattina ed evitare i notturni"
   - "Il dipendente B è disponibile in emergenza max 2 volte"

## Cosa Devi Fare:   
Dovrai analizzare queste frasi e tradurle in un formato strutturato (JSON/Dict) che rappresenti chiaramente:
   - Quali turni sono preferiti o da evitare per ciascun dipendente
   - Eventuali richieste specifiche per date particolari (es. "non lavorare il venerdì")
   - Eventuali giorni di indisponibilità assoluta
   - Limiti specifici come il numero massimo di turni di emergenza accettati

## Esempio di output atteso:

Il dipendente C è un infermiere standard, preferisce lavorare la mattina, mentre odia i turni di notte e vorrebbe evitare il più possibile di lavorare di venerdì. 
Vorrebbe che il suo riposo mensile cadesse di domenica. 
Per le vacanze, il 24 e 25 dicembre 2026 è fuori città quindi non ci sarà per l'intera giornata. 
Invece il 31 dicembre vorrebbe fare il turno di mattina. 
Non vuole fare turni festivi consecutivi e può coprire al massimo 1 emergenza.
Il dipendente D è operatore specializzato, vuole evitare di lavorare nei fine settimana e durante i festivi, 
mentre preferisce concentrare i turni il lunedì e il martedì. 
Come giorno di riposo obbligatorio richiede esplicitamente la data del 26 dicembre 2026. 
A livello di indisponibilità non ha giorni interi di ferie, ma il 15 dicembre non può assolutamente fare né il pomeriggio né la notte. 
Non ha alcun limite per le emergenze, ma non tollera fare turni di notte consecutivi.

->

[

{{
  "id_dipendente": "C",
  "is_specialised": false,
  "turni_desiderati": ["mattina"],
  "turni_da_evitare": ["notte"],
  "giorni_settimana_graditi": [],
  "giorni_settimana_sgraditi": ["venerdì"],
  "richieste_specifiche": [
    {{
      "data": "2026-12-24",
      "turno": ["tutti"],
      "desiderato": false
    }},
    {{
      "data": "2026-12-25",
      "turno": ["tutti"],
      "desiderato": false
    }},
    {{
      "data": "2026-12-31",
      "turno": ["mattina"],
      "desiderato": true
    }}
  ],
  "max_emergenze": 1,
  "tolleranza_turni_consecutivi": ["festivo"],
  "giorno_riposo_preferito": "domenica"
}},

{{
  "id_dipendente": "D",
  "is_specialised": true,
  "turni_desiderati": [],
  "turni_da_evitare": ["weekend", "festivo"],
  "giorni_settimana_graditi": ["lunedì", "martedì"],
  "giorni_settimana_sgraditi": [],
  "richieste_specifiche": [
    {{
      "data": "2026-12-15",
      "turno": ["pomeriggio", "notte"],
      "desiderato": false
    }}
  ],
  "max_emergenze": null,
  "tolleranza_turni_consecutivi": ["notte"],
  "giorno_riposo_preferito": "2026-12-26"
}}

]

"""

SYSTEM_PROMPT_CSP = """
## Il tuo Ruolo:
Sei il Workers Agent per la pianificazione dei turni di una struttura ospedaliera.
Il tuo compito ESCLUSIVO è interpretare le esigenze dei lavoratori e le regole operative, generando un file Python contenente la specifica OR-Tools del problema (CSP). Devi focalizzarti RIGOROSAMENTE SOLO SUI VINCOLI HARD (vincoli di legge, coperture, e indisponibilità assolute come le ferie). Non devi implementare preferenze soft.

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

Per creare il CSP, DEVI usare ESCLUSIVAMENTE questi parametri passati in input, rispettando rigorosamente i loro tipi di dato:
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

2. Massimo 36 ore settimanali (Finestra fissa di 7 giorni):
    # CoT:
    # 1. Mattina=6h, Pomeriggio=6h, Notte=12h.
    # 2. Ciclo con start_d in range(0, 31, 7) e calcolo le ore totali nella settimana.
    # 3. Impongo che la somma delle ore sia <= 36.

3. Vincoli Hard Specifici (Estratti dal Testo in Input):
Estrai le ferie o indisponibilità assolute dichiarate dai lavoratori.
    # CoT:
    # 1. Il dipendente C ha dichiarato ferie il 25 Dicembre 2026.
    # 2. Il 7 Dicembre è d=0. La differenza è 18 giorni, quindi d=18.
    # 3. Forza model.Add(shifts[('C', 18, 0)] == 0), e lo stesso per s=1 e s=2.

**IMPORTANTE**: Fai attenzione, la variabile `specializzati` è una variabile booleana che rappresenta se sono presenti dipendenti specializzati o meno, deve essere usata per distinguere i vincoli che presentano lavoratori specializzati da quelli standard, in modo da rispettare i vincoli hard che differiscano tra le due categorie.

Scrivi il blocco Python completo rispettando queste istruzioni e applicando il CoT su ogni vincolo hard di legge e su ogni indisponibilità estratta dal testo.
"""

def generate_csp(preferenze:str, hard_constraints:str) -> None:
    print("Estrazione delle preferenze e generazione del file Python OR-Tools in corso...")
    

    prompts = [
        ("system", SYSTEM_PROMPT_CSP),
        ("user", "Hard Constraints:\n\n{hard_constraints}\n\nTesto delle preferenze espresso dai lavoratori:\n\n{preferenze}\n\nGenera il file Python.")
    ]

    prompt_variables = { "preferenze": preferenze, "hard_constraints": hard_constraints }

    risposta_llm = llm_call(
        prompts=prompts,
        prompt_variables=prompt_variables,  
        model=GEMINI_MODEL_NAME,
        temperature=0.0,
        thinking_level="high"
    )

    if isinstance(risposta_llm.content, list):
        # Unisce tutti i frammenti di testo ignorando eventuali altri media
        testo_risposta = "".join(
            blocco.get("text", "") if isinstance(blocco, dict) else str(blocco) 
            for blocco in risposta_llm.content
        )
    else:
        testo_risposta = str(risposta_llm.content)

    codice_estratto = testo_risposta
    
    # Ora passiamo in sicurezza la stringa garantita alla regex
    match = re.search(r"```python\n(.*?)\n```", testo_risposta, re.DOTALL)
    if match:
        codice_estratto = match.group(1)

    with open(OUTPUT_CSP_PATH, "w", encoding="utf-8") as f:
        f.write("# File generato automaticamente dallo Stage 1 (Workers Agent)\n")
        f.write("# Contiene la specifica OR-Tools e il modello di soddisfazione (Fairness)\n\n")
        f.write(codice_estratto)

    print(f"Completato. File '{OUTPUT_CSP_PATH}' creato con successo.")

def extract_preferences_node(state: SchedulerForm) -> SchedulerForm:
    """
    Agente LLM responsabile della Fase 1: raccolta e traduzione delle preferenze.
    Converte le frasi in linguaggio naturale in vincoli strutturati (soft/hard).
    """
    
    testo_preferenze = state.input["preferences"].strip()
    hard_constraints = state.input["hard_constraints"].strip()
    
    generate_csp(testo_preferenze, hard_constraints)

    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco le preferenze espresse dai dipendenti:\n{preferenze_testuali}""")
    ]
    
    print('Estrazione delle preferenze in corso')
    
    risultato_estrazione = llm_call(
        prompts=prompts,
        prompt_variables={"preferenze_testuali": testo_preferenze},
        temperature=0.1,
        structured_output=VincoliStrutturati
    )
    
    vincoli_dict = risultato_estrazione.model_dump()
    
    print("Estrazione delle preferenze completata.")

    return {"vincoli_soft": vincoli_dict}