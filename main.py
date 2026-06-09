from langgraph.graph import StateGraph, END
from input_type import SchedulerForm
from agents.extract_preferences_agent import extract_preferences_node
from agents.verify_extracted_preferences_agent import verify_extracted_preferences_node
from agents.correct_preferences_agent import correct_preferences_node
from agents.generate_or_refine_plan_agent import generate_or_refine_plan_node
from agents.verify_evaluate_agent import verify_hard_constraints_node, evaluate_fairness_node
from agents.return_output_agent import return_output_node
from dotenv import load_dotenv
from halo import Halo
import os, langchain

langchain.debug = True

load_dotenv()
INPUT_FILE_NAME = os.getenv("INPUT_FILE_NAME")

def route_after_hard_check(state: SchedulerForm) -> str:
    """
    Decide dove andare dopo il controllo dei vincoli di legge.
    Se violati -> Torna all'LLM per rifare il piano.
    Se rispettati -> Passa al calcolo della fairness.
    """
    if not state.hard_constraints_valid and not state.best_plan:
        return "generate_or_refine_plan_node"
    if not state.hard_constraints_valid and state.best_plan:
        return "output_finale_node"
    
    if not state.best_plan:
        state.best_plan = state.piano_attuale
    return "evaluate_fairness_node"

def route_after_fairness_check(state: SchedulerForm) -> str:
    """
    Decide se terminare o raffinare iterativamente.
    Se terminazione raggiunta -> Fine
    Altrimenti -> Callback all'LLM per raffinare il piano per il dipendente sfortunato [4].
    """
    if state.terminazione_raggiunta:
        return "output_finale_node"
    return "generate_or_refine_plan_node"

def route_after_preferences_check(state: SchedulerForm) -> str:
    """
    Decide se procedere o terminare dopo la verifica delle preferenze estratte.
    Se preferenze non valide -> Il prossimo agente corregge le preferenze.
    Se preferenze valide -> Procedi alla generazione del piano.
    """
    preferenze = state.preferenze_valide
    
    if preferenze and preferenze.valide:
        return "generate_or_refine_plan_node"
    else:
        return "correct_preferences_node"

def build_workflow():
    workflow = StateGraph(SchedulerForm)

    # Aggiunta dei nodi al grafo
    workflow.add_node("extract_preferences_node", extract_preferences_node)
    workflow.add_node("verify_extracted_preferences_node", verify_extracted_preferences_node)
    workflow.add_node("correct_preferences_node", correct_preferences_node) 
    workflow.add_node("generate_or_refine_plan_node", generate_or_refine_plan_node)
    workflow.add_node("verify_hard_constraints_node", verify_hard_constraints_node)
    workflow.add_node("evaluate_fairness_node", evaluate_fairness_node)
    workflow.add_node("output_finale_node", return_output_node)
    
    # Definizione del flusso base (Edges)
    workflow.set_entry_point("extract_preferences_node")
    workflow.add_edge("extract_preferences_node", "verify_extracted_preferences_node")
    workflow.add_edge("correct_preferences_node", "verify_extracted_preferences_node" )
    workflow.add_edge("verify_extracted_preferences_node", "generate_or_refine_plan_node")
    workflow.add_edge("generate_or_refine_plan_node", "verify_hard_constraints_node")
    # Aggiunta degli archi condizionali (Conditional Edges)
    
    workflow.add_conditional_edges(
        "verify_extracted_preferences_node",
        route_after_preferences_check,
        {
            "generate_or_refine_plan_node": "generate_or_refine_plan_node",
            "correct_preferences_node": "correct_preferences_node"
        }
    )
    workflow.add_conditional_edges(
        "verify_hard_constraints_node",
        route_after_hard_check,
        {
            "generate_or_refine_plan_node": "generate_or_refine_plan_node",
            "evaluate_fairness_node": "evaluate_fairness_node",
            "output_finale_node": "output_finale_node"
        }
    )

    workflow.add_conditional_edges(
        "evaluate_fairness_node",
        route_after_fairness_check,
        {
            "generate_or_refine_plan_node": "generate_or_refine_plan_node",
            "output_finale_node": "output_finale_node"
        }
    )

    workflow.add_edge("output_finale_node", END)
    # Compilazione del grafo
    return workflow.compile()

if __name__ == "__main__":
    app = build_workflow()
    
    if INPUT_FILE_NAME:
        path = f"{os.getcwd()}/input/{INPUT_FILE_NAME}"
        
        spinner = Halo(
            text='Caricamento del file di input',
            spinner='line',
            color='cyan'
        )
        spinner.start()
        with open(path, "r") as f:
            input_iniziale = f.read()
        spinner.succeed("File di input caricato correttamente.")

        print("Inizio del processo di generazione del piano...")
        piano = app.invoke({"input":input_iniziale})
        print("Piano finale generato:\n", piano.get("piano_attuale"))
    else:
        raise ValueError("Il nome del file di input non è specificato nelle variabili d'ambiente")