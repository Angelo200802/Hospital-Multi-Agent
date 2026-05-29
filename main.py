from typing import TypedDict, List, Dict, Optional
from langgraph.graph import StateGraph, END

# ==========================================
# 1. DEFINIZIONE DELLO STATO DEL GRAFO
# ==========================================
class SchedulerState(TypedDict):
    # Input iniziale
    preferenze_nl: List[str]          # Preferenze in linguaggio naturale espresse dai dipendenti
    
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

# ==========================================
# 2. DEFINIZIONE DEI NODI (AGENTI)
# ==========================================

def extract_preferences_node(state: SchedulerState) -> SchedulerState:
    """
    Fase 1: Agente LLM che traduce il linguaggio naturale in vincoli strutturati [1, 6].
    Implementazione futura: Prompt LangChain per estrarre JSON/Dict compatibile con OR-Tools.
    """
    # ... Logica dell'agente LangChain ...
    return {"vincoli_soft": {"dipendente_A": "no_notte", "dipendente_B": "max_2_emergenze"}} # Esempio dummy


def generate_or_refine_plan_node(state: SchedulerState) -> SchedulerState:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback [2, 4].
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    # ... Logica dell'agente LangChain che forza gli assegnamenti ...
    return {"piano_attuale": {"assegnamenti": "dummy_data"}}


def verify_hard_constraints_node(state: SchedulerState) -> SchedulerState:
    """
    Fase 3a: Agente simbolico (OR-Tools) che verifica la validità del piano [3, 7].
    Controlla che nessuno faccia 2 turni consecutivi, limiti di ore, riposi, ecc.
    """
    # ... Logica OR-Tools per validare la matrice degli assegnamenti ...
    # Se fallisce, restituisce hard_constraints_valid=False e il feedback_errori_hard
    return {"hard_constraints_valid": True, "feedback_errori_hard": ""}


def evaluate_fairness_node(state: SchedulerState) -> SchedulerState:
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


# ==========================================
# 3. FUNZIONI DI ROUTING (ARCHI CONDIZIONALI)
# ==========================================

def route_after_hard_check(state: SchedulerState) -> str:
    """
    Decide dove andare dopo il controllo dei vincoli di legge.
    Se violati -> Torna all'LLM per rifare il piano [3].
    Se rispettati -> Passa al calcolo della fairness [3].
    """
    if not state.get("hard_constraints_valid"):
        return "generate_or_refine_plan_node"
    return "evaluate_fairness_node"

def route_after_fairness_check(state: SchedulerState) -> str:
    """
    Decide se terminare o raffinare iterativamente.
    Se terminazione raggiunta -> Fine [5].
    Altrimenti -> Callback all'LLM per raffinare il piano per il dipendente sfortunato [4].
    """
    if state.get("terminazione_raggiunta"):
        return END
    return "generate_or_refine_plan_node"


# ==========================================
# 4. COSTRUZIONE DEL GRAFO LANGGRAPH
# ==========================================

def build_workflow():
    workflow = StateGraph(SchedulerState)

    # Aggiunta dei nodi al grafo
    workflow.add_node("extract_preferences_node", extract_preferences_node)
    workflow.add_node("generate_or_refine_plan_node", generate_or_refine_plan_node)
    workflow.add_node("verify_hard_constraints_node", verify_hard_constraints_node)
    workflow.add_node("evaluate_fairness_node", evaluate_fairness_node)

    # Definizione del flusso base (Edges)
    workflow.set_entry_point("extract_preferences_node")
    workflow.add_edge("extract_preferences_node", "generate_or_refine_plan_node")
    workflow.add_edge("generate_or_refine_plan_node", "verify_hard_constraints_node")

    # Aggiunta degli archi condizionali (Conditional Edges)
    workflow.add_conditional_edges(
        "verify_hard_constraints_node",
        route_after_hard_check,
        {
            "generate_or_refine_plan_node": "generate_or_refine_plan_node",
            "evaluate_fairness_node": "evaluate_fairness_node"
        }
    )

    workflow.add_conditional_edges(
        "evaluate_fairness_node",
        route_after_fairness_check,
        {
            "generate_or_refine_plan_node": "generate_or_refine_plan_node",
            END: END
        }
    )

    # Compilazione del grafo
    return workflow.compile()

# ==========================================
# 5. ESECUZIONE (ESEMPIO)
# ==========================================
if __name__ == "__main__":
    app = build_workflow()
    
    input_iniziale = {
        "preferenze_nl": [
            "Il dipendente A preferisce i turni di mattina ed evitare i notturni",
            "Il dipendente B è disponibile in emergenza max 2 volte"
        ]
    }
    
    # Esegue il grafo fino alla terminazione
    # (nella realtà itererà attraverso il ciclo di validazione/fairness)
    risultato_finale = app.invoke(input_iniziale)
    print("Piano finale generato:", risultato_finale.get("piano_attuale"))