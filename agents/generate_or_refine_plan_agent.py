from input_type import SchedulerState

PROMPT = """

"""

def generate_or_refine_plan_node(state: SchedulerState) -> SchedulerState:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback [2, 4].
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    return {"piano_attuale": {"assegnamenti": "dummy_data"}}