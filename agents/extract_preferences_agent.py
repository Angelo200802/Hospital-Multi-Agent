from input_type import SchedulerState
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
import os


load_dotenv()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2b")
GEMINI_API = os.getenv("GEMINI_API")

CALENDARIO = """
Dicembre 2026
L M M G V S D
7 8 9 10 11 12 13
14 15 16 17 18 19 20
21 22 23 24 25 26 27
28 29 30 31 - - -
Gennaio 2027
L M M G V S D 
- - - - 1 2 3
4 5 6 7

Giorni festivi: 8 Dicembre, 25 Dicembre, 26 Dicembre, 1 Gennaio, 6 Gennaio
"""

SYSTEM_PROMPT = """
## Il tuo ruolo:
Sei un assistente intelligente incaricato di estrarre e strutturare le preferenze dei dipendenti di una struttura ospedaliera per la pianificazione dei turni. 

## Input Ricevuto:
Riceverai in input una lista di preferenze espresse in linguaggio naturale, ad esempio:
   - "Il dipendente A preferisce i turni di mattina ed evitare i notturni"
   - "Il dipendente B è disponibile in emergenza max 2 volte"

## Cosa Devi Fare:   
Dovrai analizzare queste frasi e tradurle in un formato strutturato (JSON/Dict) che rappresenti chiaramente:
   - Quali turni sono preferiti o da evitare per ciascun dipendente
   - Eventuali giorni di indisponibilità assoluta
   - Limiti specifici come il numero massimo di turni di emergenza accettati

## Esempio di output atteso:

["Il dipendente A preferisce i turni di mattina ed evitare i notturni, dando disponibilità tutti i giorni tranne il venerdì"] ->

[{
  "id_dipendente": "A",
  "turni_desiderati": ["mattina"],
  "turni_da_evitare": ["notte"],
  "giorni_indisponibilita": ["venerdì"],
  "max_emergenze": null
}]

"""
from datetime import datetime
class PreferenzeDipendente(BaseModel):
    id_dipendente: str = Field(..., description="L'identificativo del dipendente (es. 'A', 'B', 'C')")
    turni_desiderati: List[str] = Field(default=[], description="Elenco dei turni preferiti (es. 'mattina')")
    turni_da_evitare: List[str] = Field(default=[], description="Elenco dei turni sgraditi (es. 'notte', 'festivo', 'fine_settimana')")
    giorni_indisponibilita: List[str] = Field(default=[], description="Giorni specifici di indisponibilità assoluta in formato stringa (es. '2026-12-25')")
    max_emergenze: Optional[int] = Field(default=None, description="Numero massimo di turni di emergenza accettati")

class VincoliStrutturati(BaseModel):
    preferenze_dipendenti: List[PreferenzeDipendente] = Field(
        description="Lista delle preferenze strutturate per tutti i dipendenti menzionati nell'input"
    )


def extract_preferences_node(state: SchedulerState) -> SchedulerState:
    """
    Agente LLM responsabile della Fase 1: raccolta e traduzione delle preferenze.
    Converte le frasi in linguaggio naturale in vincoli strutturati (soft/hard).
    """
    
    testo_preferenze = "\n".join(state.get("preferenze_nl", []))
    
    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL, 
        google_api_key=GEMINI_API, 
        temperature=0.5
    )
    llm_strutturato = llm.with_structured_output(VincoliStrutturati)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", """
         Il calendario a cui fai riferimento è il seguente: \n{calendario}\n
         Ecco le preferenze espresse dai dipendenti:\n{preferenze_testuali}""")
    ])
    
    chain = prompt | llm_strutturato
    risultato_estrazione = chain.invoke({
        "calendario": CALENDARIO,
        "preferenze_testuali": testo_preferenze
    })
    vincoli_dict = risultato_estrazione.model_dump()
    
    return {"vincoli_soft": vincoli_dict}