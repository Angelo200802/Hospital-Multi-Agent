from input_type import SchedulerForm, PreferenzeValidate, VincoliStrutturati
from langchain_google_genai import GoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash-lite")

SYSTEM_PROMPT = f""" 
## Il tuo ruolo:
Sei un agente specializzato nella correzione delle preferenze per la pianificazione dei turni di una struttura ospedaliera. 
Il tuo compito è correggere le preferenze estratte da un agente LLM per renderle valide e coerenti con l'input originale fornito dall'utente.

## Cosa devi Fare:
- Devi analizzare le preferenze segnalate come non valide dall'agente di verifica, confrontarle con l'input originale e applicare le correzioni suggerite per renderle valide.
- Se le preferenze sono già valide, non devi apportare alcuna modifica.
- Se le preferenze non sono valide, ma non ci sono suggerimenti specifici, devi identificare autonomamente le discrepanze e correggerle basandoti sull'input originale. 
"""

def correct_preferences_node(state: SchedulerForm):
    
    testo_preferenze = state.get("input", "").strip()   
    vincoli_estratti = state.get("vincoli_soft", {})
    preferenze_valide = state.get("preferenze_valide", PreferenzeValidate(valide=False, suggerimenti={}))

    correzioni = preferenze_valide.__str__()
    preferenze_sbagliate: str = VincoliStrutturati(
        preferenze_dipendenti=[
            pref for pref in vincoli_estratti.preferenze_dipendenti if pref in preferenze_valide.suggerimenti.keys()]
    ).__str__()

    llm = GoogleGenerativeAI(
        model=GEMINI_MODEL, 
        google_api_key=GEMINI_API_KEY, 
        temperature=0.5
    )

    llm.with_structured_output(VincoliStrutturati)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco l'input originale con le preferenze espresse dai dipendenti:\n{testo_preferenze}\n\nAgente Verificatore[Output]:\n{preferenze_sbagliate}\n{correzioni}""")
    ])

    print("Correzione preferenze in corso...")
    risultato_correzione = prompt | llm
    preferenze_corrette = risultato_correzione.invoke({
        "testo_preferenze": testo_preferenze,
        "preferenze_sbagliate": preferenze_sbagliate,
        "correzioni": correzioni
    })

    print("Correzione completata.")

    nuovi_vincoli = preferenze_corrette.preferenze_dipendenti + [pref for pref in vincoli_estratti.preferenze_dipendenti if pref not in preferenze_valide.suggerimenti.keys()]
    nuove_preferenze = VincoliStrutturati(preferenze_dipendenti=nuovi_vincoli)

    return {"vincoli_soft": nuove_preferenze.model_dump()}
