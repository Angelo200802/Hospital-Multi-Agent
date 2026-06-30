from agents.generate_plan_agent import CALENDARIO
from input_type import SchedulerForm, Piano
from llm import llm_call
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_GEN")

SYSTEM_PROMPT = """
## Il tuo Ruolo:
Sei un agente intelligente incaricato raffinare un piano di turni per un gruppo di dipendenti di una struttura ospedaliera, tenendo conto delle loro preferenze e dei vincoli operativi. 
Il tuo obiettivo è raffinare un piano che sia il più possibile equo e soddisfacente in modo da aiutare il dipendente più sfortunato, rispettando **ASSOLUTAMENTE** i vincoli hard.

## Cosa Devi Fare:
Devi raffinare il piano di turni esistente in base al feedback ricevuto dagli altri agenti.
Basandoti sulle informazioni sul dipendente più sfortunato, devi cercare di migliorare la sua situazione nel piano, ad esempio assegnandogli più turni desiderati o riducendo i turni meno desiderati, sempre nel rispetto dei vincoli hard e cercando di mantenere il più possibile l'equità per tutti.

## Il tuo Input:
- Le preferenze dei dipendenti e i vincoli soft forniti dall'Agente Estrattore Preferenze.
- Informazioni sul dipendente più sfortunato fornite dall'Agente di Valutazione Fairness.
- Il piano attualemente generato.

## Strategia di Ragionamento:
1. Analizza i turni che sono stati assegnati al dipendente più sfortunato e confrontali con le sue preferenze e i suoi vincoli.
2. Identifica le aree in cui il piano può essere migliorato per quel dipendente esclusivamente tramite SCAMBI (swap 1-a-1) di turni con altri dipendenti. Se devi togliergli un turno sgradito o aggiungergli un turno gradito, devi scambiarlo alla pari con il turno di un collega in un altro giorno. 
Scambia turni solo tra dipendenti con la stessa qualifica (Standard con Standard, Specializzati con Specializzati) per non violare i vincoli di copertura minima.
3. Valuta l'impatto di eventuali scambi sul piano complessivo. Il tuo obiettivo è migliorare la condizione del dipendente sfortunato senza far crollare il livello di soddisfazione degli altri: non effettuare uno scambio se questo rende il collega coinvolto più scontento di quanto lo fosse il dipendente sfortunato iniziale.
4. Rivaluta il piano dopo ogni scambio per assicurarti che non vengano violati i vincoli hard (es. no turni consecutivi N->M, garanzia dei 2 riposi post-notte, massimo 36h) e che la situazione del dipendente più sfortunato sia effettivamente migliorata.
5. Se nessun miglioramento è possibile per il dipendente più sfortunato senza violare i vincoli hard o senza peggiorare la soddisfazione minima generale, lascia invariato il piano per raggiungere la condizione di terminazione.
6. **IMPORTANTE**: Non sacrificare **MAI** un vincolo hard per soddisfare una preferenza soft altrimenti **MORIRAI**.

## Il tuo Output:
Devi restituire un nuovo piano di turni che tenga conto del feedback ricevuto e che migliori la situazione del dipendente più sfortunato.
Per ogni dipendente devi dunque creare una lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese, dove 'M' = Mattina, 'P' = Pomeriggio, 'N' = Notte, 'R' = Riposo.
Restituisci il piano nel formato strutturato indicato.
"""

def refine_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 4: Agente LLM che raffina il piano in base al feedback ricevuto dagli altri agenti.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": state.input['hard_constraints'].__str__(),
                        "piano_precedente": state.piano_attuale.__str__(),
                        "vincoli_soft": state.vincoli_soft.__str__() ,
                        "dipendente_piu_sfortunato" : "Il dipendente più sfortunato -> " + state.dipendente_piu_sfortunato[-1]
                        }
    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", "## Calendario da seguire: {calendario}\n## Vincoli Hard: {hard_constraints}\n## Agente Valuazione Fairness[OUTPUT]:\n{dipendente_piu_sfortunato}\n##Agente Estrattore Preferenze [Output]:\n{vincoli_soft} ##Piano generato precendentemente:\n{piano_precedente}")
    ]   

    print('Raffinamento del piano in corso')      
        
    piano_attuale = llm_call(
        prompts=prompts,
        model = GEMINI_MODEL_NAME,
        prompt_variables=prompt_variables,
        structured_output=Piano,
        #use_prod=True,
        #use_test=False,
        thinking_level="high",
        temperature=0.0
    )

    print(f"Fine raffinamento del piano.")

    return {"piano_attuale": piano_attuale.model_dump(), "n_iter_raffinazioni": state.n_iter_raffinazioni + 1}