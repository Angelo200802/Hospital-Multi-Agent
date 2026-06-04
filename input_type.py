from typing import TypedDict, Dict, Optional
from pathlib import Path
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

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

class PreferenzeValidate(BaseModel):
    valide : bool = Field(..., description="Indica se le preferenze estratte sono valide e coerenti con l'input originale")
    suggerimenti: Optional[Dict[str, str]] = Field(default=None, description="Se valide è None, altrimenti contiene coppie chiave-valore dove la chiave è l'ID del dipendente e il valore è un suggerimento su cosa correggere nelle preferenze estratte per renderle valide")

class SchedulerForm(TypedDict):
    # Input iniziale
    input_path: Path
    
    # Fase 1a/4: Estrazione preferenze
    vincoli_soft: VincoliStrutturati           
    # Fase 1b/4: Verifica preferenze estratte
    preferenze_valide: PreferenzeValidate 

    # Fase 2/4: Bozza del piano
    piano_attuale: Optional[Dict]     
    
    # Fase 3a/4: Verifica vincoli Hard
    hard_constraints_valid: bool      
    feedback_errori_hard: str         
    
    # Fase 3b/4: Valutazione Fairness
    dipendente_piu_sfortunato: str    
    fairness_score: float             
    
    # Criteri di terminazione
    terminazione_raggiunta: bool      