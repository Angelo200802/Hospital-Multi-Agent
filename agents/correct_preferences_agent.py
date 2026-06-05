from input_type import SchedulerForm, VincoliStrutturati
from langchain_google_genai import ChatGoogleGenerativeAI
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

## Output Atteso:
Un set di preferenze che riguardano **esclusivamente** i dipendenti segnalati come non validi, corrette secondo i suggerimenti forniti o secondo la tua analisi, e strutturate in un formato JSON/Dict coerente con l'output dell'agente di estrazione preferenze.
"""

def correct_preferences_node(state: SchedulerForm):
    
    testo_preferenze = state.input.strip()   
    vincoli_estratti = state.vincoli_soft if state.vincoli_soft else {}
    preferenze_valide = state.preferenze_valide
    print([ s.dipendente_id for s in preferenze_valide.suggerimenti] if preferenze_valide and preferenze_valide.suggerimenti else "Nessun suggerimento specifico fornito." )
    correzioni = preferenze_valide.__str__()
    preferenze_sbagliate: str = VincoliStrutturati(
        preferenze_dipendenti=[
            pref for pref in vincoli_estratti.preferenze_dipendenti 
            if pref in [s.dipendente_id for s in preferenze_valide.suggerimenti]]
    ).__str__()

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL, 
        google_api_key=GEMINI_API_KEY, 
        temperature=0.5
    )

    llm = llm.with_structured_output(VincoliStrutturati)

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco l'input originale con le preferenze espresse dai dipendenti:\n{testo_preferenze}\n\nAgente Verificatore[Output]:\nPreferenze Errate -> \n{preferenze_sbagliate}Correzioni -> \n{correzioni}""")
    ])

    print("Correzione preferenze in corso...")
    risultato_correzione = prompt | llm
    preferenze_corrette = risultato_correzione.invoke({
        "testo_preferenze": testo_preferenze,
        "preferenze_sbagliate": preferenze_sbagliate,
        "correzioni": correzioni
    })

    print("Correzione completata.")

    print("Preferenze corrette (strutturate):\n", preferenze_corrette.__str__())

    nuovi_vincoli = preferenze_corrette.model_dump().get("preferenze_dipendenti", []) + [pref for pref in vincoli_estratti.preferenze_dipendenti if pref not in [s.dipendente_id for s in preferenze_valide.suggerimenti]]
    nuove_preferenze = VincoliStrutturati(preferenze_dipendenti=nuovi_vincoli)
    print([s.id_dipendente for s in nuove_preferenze.preferenze_dipendenti])
    return {"vincoli_soft": nuove_preferenze.model_dump()}
