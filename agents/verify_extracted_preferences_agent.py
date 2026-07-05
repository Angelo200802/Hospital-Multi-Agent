from input_type import SchedulerForm,PreferenzeValidate, VincoliStrutturati
from typing import get_origin, get_args, Union
from pydantic import BaseModel
from llm import llm_call

def genera_descrizione_campi(model: type[BaseModel], indent: int = 0) -> str:
    """
    Genera ricorsivamente una lista testuale "- nome_campo: descrizione" a partire
    dai field di un modello Pydantic, includendo i modelli annidati (dentro List[...]
    o Optional[...]) con indentazione crescente.
    """
    righe = []
    prefix = "  " * indent

    for nome_campo, field in model.model_fields.items():
        descrizione = field.description or "Nessuna descrizione fornita"
        righe.append(f'{prefix}- "{nome_campo}": {descrizione}')

        annotazione = field.annotation
        origin = get_origin(annotazione)
        args = get_args(annotazione)

        candidati = args if origin in (list, Union) else (annotazione,)
        for candidato in candidati:
            if isinstance(candidato, type) and issubclass(candidato, BaseModel):
                righe.append(f'{prefix}  Struttura di "{nome_campo}":')
                righe.append(genera_descrizione_campi(candidato, indent + 2))

    return "\n".join(righe).replace("{", "{{").replace("}", "}}")


SYSTEM_PROMPT = """ 
## Il tuo ruolo:
Sei un agente specializzato nella verifica delle preferenze per la pianificazione dei turni di una struttura ospedaliera. 
Il tuo compito è valutare se le preferenze estratte da un agente LLM sono valide e coerenti con l'input originale fornito dall'utente.

## Cosa devi Fare:
- Per ogni dipendente, confronta le preferenze estratte con le frasi originali.
- Se le preferenze riportate dal tuo collega non sono coerenti con l'input originale, identifica le discrepanze specifiche e fornisci suggerimenti chiari su cosa correggere per renderle valide.
- Se tutte le preferenze sono valide, conferma che sono coerenti con l'input originale.

## Il tuo input:
- Testo originale con le preferenze espresse dai dipendenti (linguaggio naturale)
- Preferenze estratte dal tuo collega in formato strutturato, per ogni dipendente devi valutare le seguenti informazioni:
{campi_vincoli_strutturati}

## Il tuo output:
L'output deve seguire rigorosamente lo schema strutturato richiesto, che prevede:
- un flag booleano di validità.
- una lista di suggerimenti in caso di errori, dove ogni elemento specifica l'ID del dipendente e il messaggio di correzione.

{{
    "valide": bool,
    "suggerimenti": [
        {{
            "dipendente_id": str,
            "messaggio": str
        }},
        ...
    ]
}}

"""

def verify_extracted_preferences_node(state: SchedulerForm):

    testo_preferenze = state.input["preferences"].strip()   
    vincoli_estratti = state.vincoli_soft.__str__() if state.vincoli_soft else "Nessun vincolo estratto"

    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco l'input originale con le preferenze espresse dai dipendenti:\n{testo_preferenze}\n\nEcco le preferenze estratte dal tuo collega:\n{vincoli_estratti}""")
    ]
    
    print('Verifica delle preferenze in corso')

    risultato_verifica = llm_call(
        prompts=prompts,
        prompt_variables={
            "campi_vincoli_strutturati": genera_descrizione_campi(VincoliStrutturati),
            "testo_preferenze": testo_preferenze,
            "vincoli_estratti": vincoli_estratti
        },
        structured_output=PreferenzeValidate,
        temperature=0.5
    )
    

    print(f"Verifica delle preferenze completata. {risultato_verifica}")

    return {"preferenze_valide": risultato_verifica.model_dump()}