from input_type import SchedulerState

def extract_preferences_node(state: SchedulerState) -> SchedulerState:
    """
    Fase 1: Agente LLM che traduce il linguaggio naturale in vincoli strutturati [1, 6].
    Implementazione futura: Prompt LangChain per estrarre JSON/Dict compatibile con OR-Tools.
    """
    # ... Logica dell'agente LangChain ...
    return {"vincoli_soft": {"dipendente_A": "no_notte", "dipendente_B": "max_2_emergenze"}} # Esempio dummy
