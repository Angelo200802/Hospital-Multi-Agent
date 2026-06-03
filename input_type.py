from typing import TypedDict, Dict, Optional
from pathlib import Path

class SchedulerForm(TypedDict):
    # Input iniziale
    input_path: Path
    
    #Preferenze strutturate
    vincoli_soft: Dict           
    
    # Fase 2/4: Bozza del piano
    piano_attuale: Optional[Dict]     
    
    # Fase 3a: Verifica vincoli Hard
    hard_constraints_valid: bool      
    feedback_errori_hard: str         
    
    # Fase 3b: Valutazione Fairness
    dipendente_piu_sfortunato: str    
    fairness_score: float             
    
    # Criteri di terminazione
    terminazione_raggiunta: bool      