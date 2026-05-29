from langgraph.graph import StateGraph, END
from input_type import SchedulerState
from agents.extract_preferences_agent import extract_preferences_node
from agents.generate_or_refine_plan_agent import generate_or_refine_plan_node
from agents.verify_evaluate_agent import verify_hard_constraints_node, evaluate_fairness_node

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

if __name__ == "__main__":
    app = build_workflow()
    
    input_iniziale = {
        "preferenze_nl": [
            "Il dipendente A preferisce i turni di mattina ed evitare i notturni",
            "Il dipendente B è disponibile in emergenza max 2 volte"
        ]
    }
    risultato_finale = app.invoke(input_iniziale)
    print("Piano finale generato:", risultato_finale.get("piano_attuale"))