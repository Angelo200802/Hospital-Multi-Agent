from agents.generate_plan_agent import CALENDARIO, HARD_CONSTRAINTS
from input_type import SchedulerForm, Piano
from llm import llm_call
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_GEN")

SYSTEM_PROMPT = """
## Il tuo Ruolo:
Sei un agente intelligente incaricato raffinare un piano di turni per un gruppo di dipendenti di una struttura ospedaliera, tenendo conto delle loro preferenze e dei vincoli operativi. 
Il tuo obiettivo è raffinare un piano che sia il più possibile equo e soddisfacente per tutti i dipendenti, rispettando al contempo le esigenze dell'organizzazione.

## Cosa Devi Fare:
Devi raffinare il piano di turni esistente in base al feedback ricevuto dagli altri agenti.
- Se ricevi feedback sui vincoli hard violati, devi correggere il piano per rispettare quei vincoli.
- Se ricevi informazioni sul dipendente più sfortunato, devi cercare di migliorare la sua situazione nel piano, ad esempio assegnandogli più turni desiderati o riducendo i turni meno desiderati, sempre nel rispetto dei vincoli hard.

{hard_constraints}

## Il tuo Input:
- Feedback sui vincoli hard violati forniti dall'Agente di Verifica Vincoli Hard (se presenti).
- Informazioni sul dipendente più sfortunato fornite dall'Agente di Valutazione Fairness (se presenti).
- Il piano attuale generato nella precedente iterazione.

##Strategia di Ragionamento (Passo-Passo):
1. Analizza il feedback sui vincoli hard violati e identifica esattamente quali vincoli sono stati infranti e in quali parti del piano generato precedentemente.
2. Analizza le informazioni sul dipendente più sfortunato per capire quali sono le sue preferenze e quali aspetti del piano attuale stanno contribuendo alla sua situazione sfortunata.
3. Elabora un piano raffinato che corregga i vincoli hard violati, assicurandoti di rispettarli rigorosamente.
4. Esempi di correzioni:
    - Se dopo un turno 'N' non ci sono 2 giorni di 'R', inserisci 'R' nei giorni successivi.
    - Se un dipendente ha più di 25 turni, riduci il numero di turni assegnati a quel dipendente mettendo un numero di 'R' pari al numero di turni in eccesso.
    - Se un dipendente specializzato è necessario per un turno ma non è assegnato inseriscilo in quel turno

## Il tuo Output:
Devi restituire un nuovo piano di turni che tenga conto del feedback ricevuto sui vincoli hard violati oppure che migliori la situazione del dipendente più sfortunato.
Per ogni dipendente devi dunque creare una nuova lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese, dove 'M' = Mattina, 'P' = Pomeriggio, 'N' = Notte, 'R' = Riposo.
Restituisci il piano nel formato strutturato indicato.
"""

def refine_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 4: Agente LLM che raffina il piano in base al feedback ricevuto dagli altri agenti.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": HARD_CONSTRAINTS,
                        "piano_precedente": state.piano_attuale.__str__(),
                        "vincoli_soft": state.vincoli_soft.__str__()  
                        }
    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", "## Calendario da seguire: {calendario}\n##Agente Estrattore Preferenze [Output]:\n{vincoli_soft} ##Piano generato precendentemente:\n{piano_precedente}")
    ]

    if state.feedback_errori_hard:
        prompt_variables["feedback_errori_hard"] = state.feedback_errori_hard
        prompts[1] = ("user",prompts[1][1] + "\n## Feedback sui vincoli hard violati:\n{feedback_errori_hard}")
    if state.dipendente_piu_sfortunato:
        prompt_variables["dipendente_piu_sfortunato"] = state.dipendente_piu_sfortunato
        prompts[1] = ("user",prompts[1][1] + "\n## Informazioni sul dipendente più sfortunato:\n{dipendente_piu_sfortunato}")
    
    

    print('Raffinamento del piano in corso')      
        
    piano_attuale = llm_call(
        prompts=prompts,
        model = GEMINI_MODEL_NAME,
        prompt_variables=prompt_variables,
        structured_output=Piano,
        temperature=0.6
    )

    print(f"Fine raffinamento del piano.")

    return {"piano_attuale": piano_attuale.model_dump()}