from input_type import SchedulerForm, Piano
from llm import llm_call
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_GEN")

CALENDARIO = """

Dicembre 2026
 L|  M|  M|  G|  V|  S|  D
 7|  8|  9| 10| 11| 12| 13
14| 15| 16| 17| 18| 19| 20
21| 22| 23| 24| 25| 26| 27
28| 29| 30| 31|  -|  -|  -

Gennaio 2027
 L| M| M| G| V| S| D|
 -| -| -| -| 1| 2| 3
 4| 5| 6 

**Giorni festivi**: 8 Dicembre, 25 Dicembre, 26 Dicembre, 1 Gennaio, 6 Gennaio
"""

SYSTEM_PROMPT = """
## Il tuo Ruolo:
Sei un agente intelligente incaricato di generare un piano di turni per un gruppo di dipendenti di una struttura ospedaliera.
Devi produrre un piano valido per tutti i dipendenti indicati nell'input.

## Cosa Devi Fare:
Genera un piano turni che rispetti prima di tutto i vincoli hard.
Solo dopo aver rispettato i vincoli hard, prova a soddisfare le preferenze soft dei dipendenti.
I vincoli hard sono obbligatori.
Le preferenze soft sono desiderabili, ma possono essere ignorate se entrano in conflitto con i vincoli hard.

{hard_constraints}

{strategy}

## Il tuo input:
- Il calendario da seguire con evidenziati i giorni festivi.
- Le preferenze soft estratte dall'Agente di Estrazione Preferenze.
- Il piano generato precedentemente (se presente, altrimenti ignora questo punto).
- Eventuali errori hard riscontrati nel piano precedente (se presenti, altrimenti ignora questo punto).

## Il tuo Output:
Devi restituire un piano di turni completo per tutti i dipendenti per ogni giorno del periodo di pianificazione (7 Dicembre - 7 Gennaio).
Restituisci il piano nel formato strutturato indicato.

"""


def generate_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": state.input['hard_constraints'].__str__(),
                        "strategy": state.planner_strategy ,
                        "vincoli_soft": state.vincoli_soft.__str__()  
                    }

    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", "##Calendario da seguire: {calendario}\n##Agente Estrattore Preferenze [Output]: {vincoli_soft}")
    ]
    if state.piano_attuale:
        prompt_variables["piano_precedente"] = state.piano_attuale.__str__()
        prompts[1] = ("user",prompts[1][1] + "\n##Piano generato precendentemente:\n{piano_precedente}")
    
    if state.feedback_errori_hard:
        prompt_variables["feedback_errori_hard"] = state.feedback_errori_hard.__str__()
        prompts[1] = ("user",prompts[1][1] + "\n##Feedback errori hard del piano precedente:\n{feedback_errori_hard}")
    
    print('Generazione del piano in corso')      
        
    piano_attuale = llm_call(
        prompts=prompts,
        model = GEMINI_MODEL_NAME,
        prompt_variables=prompt_variables,
        thinking_level = "high",
        structured_output=Piano,
        temperature=0.0
    )

    print(f"Fine generazione del piano.")

    return {"piano_attuale": piano_attuale.model_dump(), 
            "n_iter_piano": state.n_iter_piano + 1}
