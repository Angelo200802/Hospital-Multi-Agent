from typing import TypedDict, Dict, Optional
from pathlib import Path
class SchedulerState(TypedDict):
    # Input iniziale
    input_path: Path          # percorso al file di testo con le preferenze in linguaggio naturale (es. "preferenze.txt")
    
    # Fase 1: Preferenze strutturate
    vincoli_soft: Dict                # Preferenze tradotte in formato strutturato per OR-Tools
    
    # Fase 2/4: Bozza del piano
    piano_attuale: Optional[Dict]     # L'assegnamento corrente dei turni generato dall'LLM
    
    # Fase 3a: Verifica vincoli Hard
    hard_constraints_valid: bool      # Esito della verifica logica di OR-Tools
    feedback_errori_hard: str         # Messaggio da passare all'LLM in caso di violazione vincoli di legge
    
    # Fase 3b: Valutazione Fairness
    dipendente_piu_sfortunato: str    # ID del dipendente più scontento calcolato dalla funzione obiettivo
    fairness_score: float             # Punteggio generale di equità del piano attuale
    
    # Criteri di terminazione
    terminazione_raggiunta: bool      # Flag che indica se il ciclo iterativo deve interrompersi
