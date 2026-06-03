from input_type import SchedulerState
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from dotenv import load_dotenv
from enum import Enum
import os


load_dotenv()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2b")
GEMINI_API = os.getenv("GEMINI_API")

SYSTEM_PROMPT = """
## Il tuo ruolo:
Sei un assistente intelligente incaricato di estrarre e strutturare le preferenze dei dipendenti di una struttura ospedaliera per la pianificazione dei turni. 

## Input Ricevuto:
Riceverai in input un testo in cui sono espresse le preferenze degli impiegati in linguaggio naturale, ad esempio:
   - "Il dipendente A preferisce i turni di mattina ed evitare i notturni"
   - "Il dipendente B è disponibile in emergenza max 2 volte"

## Cosa Devi Fare:   
Dovrai analizzare queste frasi e tradurle in un formato strutturato (JSON/Dict) che rappresenti chiaramente:
   - Quali turni sono preferiti o da evitare per ciascun dipendente
   - Eventuali richieste specifiche per date particolari (es. "non lavorare il venerdì")
   - Eventuali giorni di indisponibilità assoluta
   - Limiti specifici come il numero massimo di turni di emergenza accettati

## Esempio di output atteso:

Il dipendente C è un infermiere standard, preferisce lavorare la mattina, mentre odia i turni di notte e vorrebbe evitare il più possibile di lavorare di venerdì. 
Vorrebbe che il suo riposo mensile cadesse di domenica. 
Per le vacanze, il 24 e 25 dicembre 2026 è fuori città quindi non ci sarà per l'intera giornata. 
Invece il 31 dicembre vorrebbe fare il turno di mattina. 
Non vuole fare turni festivi consecutivi e può coprire al massimo 1 emergenza.
Il dipendente D è operatore specializzato, vuole evitare di lavorare nei fine settimana e durante i festivi, 
mentre preferisce concentrare i turni il lunedì e il martedì. 
Come giorno di riposo obbligatorio richiede esplicitamente la data del 26 dicembre 2026. 
A livello di indisponibilità non ha giorni interi di ferie, ma il 15 dicembre non può assolutamente fare né il pomeriggio né la notte. 
Non ha alcun limite per le emergenze, ma non tollera fare turni di notte consecutivi.

[

{{
  "id_dipendente": "C",
  "is_specialised": false,
  "turni_desiderati": ["mattina"],
  "turni_da_evitare": ["notte"],
  "giorni_settimana_graditi": [],
  "giorni_settimana_sgraditi": ["venerdì"],
  "richieste_specifiche": [
    {{
      "data": "2026-12-24",
      "turno": ["tutti"],
      "desiderato": false
    }},
    {{
      "data": "2026-12-25",
      "turno": ["tutti"],
      "desiderato": false
    }},
    {{
      "data": "2026-12-31",
      "turno": ["mattina"],
      "desiderato": true
    }}
  ],
  "max_emergenze": 1,
  "tolleranza_turni_consecutivi": ["festivo"],
  "giorno_riposo_preferito": "domenica"
}},

{{
  "id_dipendente": "D",
  "is_specialised": true,
  "turni_desiderati": [],
  "turni_da_evitare": ["weekend", "festivo"],
  "giorni_settimana_graditi": ["lunedì", "martedì"],
  "giorni_settimana_sgraditi": [],
  "richieste_specifiche": [
    {{
      "data": "2026-12-15",
      "turno": ["pomeriggio", "notte"],
      "desiderato": false
    }}
  ],
  "max_emergenze": null,
  "tolleranza_turni_consecutivi": ["notte"],
  "giorno_riposo_preferito": "2026-12-26"
}}

]

"""

class CategoriaTurno(Enum):
    MATTINA = "mattina"
    POMERIGGIO = "pomeriggio"
    NOTTE = "notte"
    FESTIVO = "festivo"
    WEEKEND = "weekend"

class TurnoReale(Enum):
    MATTINA = "mattina"
    POMERIGGIO = "pomeriggio"
    NOTTE = "notte"
    TUTTI = "tutti" 

class GiornoSettimana(Enum):
    LUNEDI = "lunedì"
    MARTEDI = "martedì"
    MERCOLEDI = "mercoledì"
    GIOVEDI = "giovedì"
    VENERDI = "venerdì"
    SABATO = "sabato"
    DOMENICA = "domenica"

class RichiestaSpecifica(BaseModel):
    data: str = Field(..., description="La data specifica (formato YYYY-MM-DD)")
    turno: List[TurnoReale] = Field(..., description="Il turno interessato (mattina, pomeriggio, notte, o tutti se indisponibile l'intero giorno)")
    desiderato: bool = Field(..., description="True se il dipendente VUOLE lavorare, False se NON PUO'/NON VUOLE lavorare in quel turno")

class PreferenzeDipendente(BaseModel):
    id_dipendente: str = Field(..., description="L'identificativo del dipendente (es. 'A')")
    is_specialised: bool = Field(default=False, description="Indica se il dipendente è specializzato")
    
    turni_desiderati: List[CategoriaTurno] = Field(default=[], description="Elenco dei turni preferiti")
    turni_da_evitare: List[CategoriaTurno] = Field(default=[], description="Elenco dei turni sgraditi")
    giorni_settimana_graditi: List[GiornoSettimana] = Field(
        default=[], 
        description="Giorni della settimana ricorrenti in cui il dipendente PREFERISCE lavorare (es. 'lunedì', 'martedì')"
    )
    
    giorni_settimana_sgraditi: List[GiornoSettimana] = Field(
        default=[], 
        description="Giorni della settimana ricorrenti in cui il dipendente preferisce NON lavorare (es. 'venerdì', 'domenica')"
    )
    richieste_specifiche: List[RichiestaSpecifica] = Field(
        default=[], 
        description="Richieste esatte per date specifiche. Se il dipendente non vuole lavorare in un giorno ricorrente (es. 'venerdì'), l'LLM deve calcolare le date esatte tra il 07-12-2026 e il 06-01-2027 e inserirle qui."
    )
    
    max_emergenze: Optional[int] = Field(default=None, description="Max turni di emergenza accettati")

    giorno_riposo_preferito: Optional[Union[GiornoSettimana, str]] = Field(
        default=None, 
        description="Il riposo desiderato. Può essere un giorno della settimana (es. 'domenica') OPPURE una data specifica in formato YYYY-MM-DD (es. '2026-12-24')."
    )
    tolleranza_turni_consecutivi: List[CategoriaTurno] = Field(default=[], description="Combinazioni di turni consecutivi sgraditi (es. festivi)")

class VincoliStrutturati(BaseModel):
    preferenze_dipendenti: List[PreferenzeDipendente] = Field(
        description="Lista delle preferenze strutturate per tutti i dipendenti menzionati nell'input"
    )


def extract_preferences_node(state: SchedulerState) -> SchedulerState:
    """
    Agente LLM responsabile della Fase 1: raccolta e traduzione delle preferenze.
    Converte le frasi in linguaggio naturale in vincoli strutturati (soft/hard).
    """
    
    input_path = state.get("input_path", None)
    if not input_path:
        raise ValueError("Il percorso al file di input non è specificato")
    
    with open(input_path, "r") as f:
        testo_preferenze = f.read()

    llm = ChatGoogleGenerativeAI(
        model=GEMINI_MODEL, 
        google_api_key=GEMINI_API, 
        temperature=0.5
    )
    llm_strutturato = llm.with_structured_output(VincoliStrutturati)
    
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco le preferenze espresse dai dipendenti:\n{preferenze_testuali}""")
    ])
    

    chain = prompt | llm_strutturato
    risultato_estrazione = chain.invoke({
        "preferenze_testuali": testo_preferenze
    })
    vincoli_dict = risultato_estrazione.model_dump()
    
    return {"vincoli_soft": vincoli_dict}