from input_type import SchedulerForm,PreferenzeValidate, VincoliStrutturati
from llm import llm_call
from halo import Halo

campi_vincoli = "\n".join([f"  - {nome}: {desc}" for nome, desc in VincoliStrutturati.model_fields.items()])

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

    testo_preferenze = state.input.strip()   
    vincoli_estratti = state.vincoli_soft.__str__() if state.vincoli_soft else "Nessun vincolo estratto"

    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco l'input originale con le preferenze espresse dai dipendenti:\n{testo_preferenze}\n\nEcco le preferenze estratte dal tuo collega:\n{vincoli_estratti}""")
    ]
    
    spinner = Halo(
        text='Verifica delle preferenze in corso',
        spinner='line',
        color='cyan'
    )
    spinner.start()

    risultato_verifica = llm_call(
        prompts=prompts,
        prompt_variables={
            "campi_vincoli_strutturati": campi_vincoli,
            "testo_preferenze": testo_preferenze,
            "vincoli_estratti": vincoli_estratti
        },
        structured_output=PreferenzeValidate,
        temperature=0.5
    )
    

    spinner.succeed("Verifica delle preferenze completata.")

    return {"preferenze_valide": risultato_verifica.model_dump()}