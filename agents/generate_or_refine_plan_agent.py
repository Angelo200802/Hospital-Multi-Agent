from input_type import SchedulerForm, Piano
from llm import llm_call

CALENDARIO = """

## Calendario da Seguire per la Pianificazione dei Turni:

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
Sei un agente intelligente incaricato di generare o raffinare un piano di turni per un gruppo di dipendenti di una struttura ospedaliera, tenendo conto delle loro preferenze e dei vincoli operativi. 
Il tuo obiettivo è creare/raffinare un piano che sia il più possibile equo e soddisfacente per tutti i dipendenti, rispettando al contempo le esigenze dell'organizzazione.
"""

PROMPT_GENERATE = """
## Cosa Devi Fare:
Devi **generare per la prima volta** un piano di turni basato sui vincoli e le preferenze estratte dall'Agente di Estrazione Preferenze.
Il piano deve essere conforme ai vincoli hard e cercare di massimizzare la soddisfazione delle preferenze dei dipendenti, tenendo conto dei vincoli soft.

{hard_constraints}

## Il tuo Output:
Devi restituire un piano di turni completo per tutti i dipendenti per ogni giorno del periodo di pianificazione (7 Dicembre - 7 Gennaio).
Per ogni dipendente devi creare una lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese, dove 'M' = Mattina, 'P' = Pomeriggio, 'N' = Notte, 'R' = Riposo.
Restituisci il piano nel formato strutturato indicato.
"""

PROMPT_REFINE = """
## Cosa Devi Fare:
Devi raffinare il piano di turni esistente in base al feedback ricevuto dagli altri agenti.
- Se ricevi feedback sui vincoli hard violati, devi correggere il piano per rispettare quei vincoli.
- Se ricevi informazioni sul dipendente più sfortunato e il suo fairness score, devi cercare di migliorare la sua situazione nel piano, ad esempio assegnandogli più turni desiderati o riducendo i turni meno desiderati, sempre nel rispetto dei vincoli hard.

{hard_constraints}

## Il tuo Input:
- Feedback sui vincoli hard violati forniti dall'Agente di Verifica Vincoli Hard (se presenti).
- Informazioni sul dipendente più sfortunato e il suo fairness score fornite dall'Agente di Valutazione Fairness (se presenti).
- Il piano attuale generato nella precedente iterazione.

## Il tuo Output:
Devi restituire un nuovo piano di turni che tenga conto del feedback ricevuto sui vincoli hard violati oppure che migliori la situazione del dipendente più sfortunato.
Per ogni dipendente devi dunque creare una nuova lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese, dove 'M' = Mattina, 'P' = Pomeriggio, 'N' = Notte, 'R' = Riposo.
Restituisci il piano nel formato strutturato indicato.
"""

HARD_CONSTRAINTS = """
## Vincoli Hard da Rispettare Assolutamente:
- Ogni dipendente può lavorare al **massimo un turno al giorno**.
- Non sono permessi turni consecutivi a cavallo di due giorni (es. Notte -> Mattina).
- Dopo un turno di notte, il dipendente deve avere **almeno 2 giorni di riposo**.
- Requisiti di copertura per ogni turno:
    - Se ci sono dipendenti specializzati, ogni turno deve avere **almeno 1 specializzato** e **almeno 3 persone in totale**.
    - Se non ci sono dipendenti specializzati, ogni turno deve avere **almeno 2 lavoratori qualsiasi**.
- Ogni dipendente deve lavorare esattamente **25 turni mensili** (considerando la notte come carico di lavoro doppio).
- Ogni dipendente può lavorare per un **massimo di 36 ore settimanali** (ogni turno dura 6 ore tranne la notte che dura 12 ore).
- All'interno del mese di lavoro ogni dipendente deve avere **almeno un giorno di riposo garantito**.
"""

def generate_or_refine_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": HARD_CONSTRAINTS,
                        "vincoli_soft": state.vincoli_soft.__str__()  
                    }
    prompts = []

    if state.retry:
        print('Raffinamento del piano in corso')
        
        prompts.append(("system", SYSTEM_PROMPT +"\n"+ PROMPT_REFINE))
        user_input = "Piano da Raffinare:\n{piano_attuale}\n"
        
        if not state.hard_constraints_valid:
            prompt_variables["feedback_errori_hard"] = state.feedback_errori_hard
            user_input += "Agente Verifica Vincoli Hard Violati [Output]:\n{feedback_errori_hard}\n"
        
        if state.dipendente_piu_sfortunato:
            prompt_variables["dipendente_piu_sfortunato"] = state.dipendente_piu_sfortunato
            user_input += "Agente Valutazione Fairness [Output]:\nDipendente più sfortunato: {dipendente_piu_sfortunato}\n"
        
        user_input += "Calendario da seguire: {calendario}\nAgente Estrattore Preferenze [Output]: {vincoli_soft}"
        piano : str = state.piano_attuale.__str__()
        prompt_variables["piano_attuale"] = piano

        prompts.append(("user", user_input))
    else:
        print('Generazione del piano in corso')
           
        prompts.append(("system", SYSTEM_PROMPT +"\n"+ PROMPT_GENERATE))
        prompts.append(("user", "Calendario da seguire: {calendario}\nAgente Estrattore Preferenze [Output]: {vincoli_soft}"))
        
    piano_attuale = llm_call(
        prompts=prompts,
        prompt_variables=prompt_variables,
        structured_output=Piano,
        temperature=0.6
    )

    print(f"Fine {'generazione' if not state.retry else 'raffinamento'} del piano.")

    return {"piano_attuale": piano_attuale.model_dump()}