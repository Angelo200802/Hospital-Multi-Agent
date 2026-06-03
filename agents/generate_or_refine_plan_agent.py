from input_type import SchedulerState

CALENDARIO = """
Dicembre 2026
 L|  M|  M|  G|  V|  S|  D
 7|  8|  9| 10| 11| 12| 13
14| 15| 16| 17| 18| 19| 20
21| 22| 23| 24| 25| 26| 27
28| 29| 30| 31|  -|  -|  -

Gennaio 2027
 L| M| M| G| V| S| D|
 -| -| -| -| 1| 2| 3
 4| 5| 6 

Giorni festivi: 8 Dicembre, 25 Dicembre, 26 Dicembre, 1 Gennaio, 6 Gennaio
"""

PROMPT = """

"""

def generate_or_refine_plan_node(state: SchedulerState) -> SchedulerState:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback [2, 4].
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    return {"piano_attuale": {"assegnamenti": "dummy_data"}}