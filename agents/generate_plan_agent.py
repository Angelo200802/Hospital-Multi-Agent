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
Sei un agente intelligente incaricato di generare un piano di turni per un gruppo di dipendenti di una struttura ospedaliera, tenendo conto delle loro preferenze e dei vincoli operativi. 

## Cosa Devi Fare:
Il tuo obiettivo è creare/modificare un piano che sia il più possibile equo e soddisfacente per tutti i dipendenti, rispettando al contempo le esigenze dell'organizzazione.
Il piano deve essere conforme ai vincoli hard e cercare di massimizzare la soddisfazione delle preferenze dei dipendenti estratte dall'Agente di Estrazione Preferenze.

{hard_constraints}

## Strategia di Ragionamento (Passo-Passo): 
Prima di generare l'output finale, devi elaborare mentalmente il piano seguendo questo ordine rigoroso:
1. Per ogni dipendente crea mentalmente una lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese.
2. Verifica dei 2 giorni post-notte: Controlla che ogni 'N' sia categoricamente seguito da due 'R'.
3. Verifica delle 36 ore: Assicurati che nei 7 giorni che compongono la settimana ci sia almeno un turno di riposo per rietrare nel vincolo di 36 ore settimanli.
4. Calcolo dei 25 turni: Per ogni dipendente, conta il carico sommando i turni 'M' e 'P' (valore 1) e i turni 'N' (valore 2) finché non arrivi a ESATTAMENTE 25 per ciascuno, se li ha già raggiunti, non assegnare più turni a quel dipendente.
5. Verifica che per ogni colonna virtuale (giorno della settimana) ci siano i numeri minimi di dipendenti richiesti:
    - 2 M, 2 P, 2 N se non ci sono specializzati.
    - 1 specializzato + 2 qualsiasi se ci sono specializzati.

## Il tuo input:
- Il calendario da seguire con evidenziati i giorni festivi.
- Le preferenze soft estratte dall'Agente di Estrazione Preferenze.
- Il piano generato precedentemente (se presente, altrimenti ignora questo punto).

## Il tuo Output:
Devi restituire un piano di turni completo per tutti i dipendenti per ogni giorno del periodo di pianificazione (7 Dicembre - 7 Gennaio).
Per ogni dipendente devi creare una lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese, dove 'M' = Mattina, 'P' = Pomeriggio, 'N' = Notte, 'R' = Riposo.
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

def generate_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": HARD_CONSTRAINTS,
                        "vincoli_soft": state.vincoli_soft.__str__()  
                    }
    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", "##Calendario da seguire: {calendario}\n##Agente Estrattore Preferenze [Output]: {vincoli_soft}")
    ]
    if state.piano_attuale:
        prompt_variables["piano_precedente"] = state.piano_attuale.__str__()
        prompts[1] = ("user",prompts[1][1] + "\n##Piano generato precendentemente:\n{piano_precedente}")
    print('Generazione del piano in corso')      
        
    piano_attuale = llm_call(
        prompts=prompts,
        model = GEMINI_MODEL_NAME,
        prompt_variables=prompt_variables,
        structured_output=Piano,
        temperature=0.6
    )

    print(f"Fine generazione del piano.")

    return {"piano_attuale": piano_attuale.model_dump()}


if __name__ == "__main__":
    import json
    with open(f"{os.getcwd()}/progetto/output/preferenze_estratte.json", "r") as f:
        state = f.read()

    state = {k:v for k,v in json.loads(state).items() if v is not None}
    state = SchedulerForm.model_validate(state)

    out = generate_plan_node(state)
    print(out)
    out['piano_attuale'] = {"assegnamenti" : [{"id_dipendente" : elem["id_dipendente"], "turni" : [t.value for t in elem["turni_assegnati"]]} for elem in out['piano_attuale']['assegnamenti']]}
    with open(f"{os.getcwd()}/progetto/output/piano_generato.json", "w") as f:
        f.write(json.dumps(out))