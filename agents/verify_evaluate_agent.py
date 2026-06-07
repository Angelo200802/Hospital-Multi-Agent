from input_type import SchedulerForm
from csp import solve_hard_constraints

def verify_hard_constraints_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 3a: Agente simbolico (OR-Tools) che verifica la validità del piano [3, 7].
    Controlla che nessuno faccia 2 turni consecutivi, limiti di ore, riposi, ecc.
    """
    
    return solve_hard_constraints(state)

 


def evaluate_fairness_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 3b: Valutazione della funzione obiettivo basata sulle preferenze [8, 9].
    Individua il dipendente più scontento.
    Verifica anche i criteri di terminazione: impossibilità di migliorare senza 
    violare i vincoli hard o peggiorare il livello minimo generale [5].
    """
    # ... Logica matematica/simbolica per calcolare lo scontento ...
    # Se il piano è perfetto o non più migliorabile, imposta terminazione_raggiunta = True
    return {
        "dipendente_piu_sfortunato": "dipendente_C",
        "fairness_score": 85.5,
        "terminazione_raggiunta": False # O True se si raggiunge lo stallo
    }