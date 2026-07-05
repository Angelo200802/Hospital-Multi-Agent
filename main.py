from langgraph.graph import StateGraph, END
from input_type import SchedulerForm
from agents.generate_csp_agent import generate_csp_node
from agents.generate_evaluation_fun_agent import generate_fairness_node
from agents.verify_csp_code_agent import verify_csp_code
from agents.extract_preferences_agent import extract_preferences_node
from agents.verify_extracted_preferences_agent import verify_extracted_preferences_node
from agents.correct_preferences_agent import correct_preferences_node
from agents.generate_plan_agent import generate_plan_node
from agents.refine_plan_agent import refine_plan_node
from agents.evaluate_agent import verify_hard_constraints_node, evaluate_fairness_node
from agents.return_output_agent import return_output_node
from dotenv import load_dotenv
import os, langchain

langchain.debug = True

load_dotenv()
PREFERENCES_FILE = os.getenv("PREFERENCES_FILE")
HARD_CONSTRAINTS_FILE = os.getenv("HARD_CONSTRAINTS_FILE")

def route_after_code_check(state: SchedulerForm) -> str:
    if state.errori_codice:
        print(f"Numero di Errori nel codice csp: {len(state.errori_codice.errori)}")
        
    if state.errori_codice and len(state.errori_codice.errori) > 0:
        return "generate_csp_node"
    else:
        return "prosegui"

def route_after_hard_check(state: SchedulerForm) -> str:
    """
    Decide dove andare dopo il controllo dei vincoli di legge.
    Se violati -> Torna all'LLM per rifare il piano.
    Se rispettati -> Passa al calcolo della fairness.
    """
    if not state.hard_constraints_valid and not state.best_plan:
        return "generate_plan_node"
    if not state.hard_constraints_valid and state.best_plan:
        return "output_finale_node"

    return "evaluate_fairness_node"

def route_after_fairness_check(state: SchedulerForm) -> str:
    """
    Decide se terminare o raffinare iterativamente.
    Se terminazione raggiunta -> Fine
    Altrimenti -> Callback all'LLM per raffinare il piano per il dipendente sfortunato [4].
    """
    if state.terminazione_raggiunta:
        return "output_finale_node"
    return "refine_plan_node"

def route_after_preferences_check(state: SchedulerForm) -> str:
    """
    Decide se procedere o terminare dopo la verifica delle preferenze estratte.
    Se preferenze non valide -> Il prossimo agente corregge le preferenze.
    Se preferenze valide -> Procedi alla generazione del piano.
    """
    preferenze = state.preferenze_valide
    
    if preferenze and preferenze.valide:
        return ["generate_fairness_node","generate_csp_node","generate_plan_node"]
    else:
        return "correct_preferences_node"

def route_after_sync(state: SchedulerForm) -> str:
    if state.piano_attuale and state.errori_codice and len(state.errori_codice.errori) == 0:
        return "verify_hard_constraints_node"
    else:
        return "sync_node"

def build_workflow():
    workflow = StateGraph(SchedulerForm)

    # Aggiunta dei nodi al grafo
    workflow.add_node("generate_csp_node", generate_csp_node)
    workflow.add_node("verify_code_node", verify_csp_code)
    workflow.add_node("generate_fairness_node", generate_fairness_node)
    workflow.add_node("extract_preferences_node", extract_preferences_node)
    workflow.add_node("verify_extracted_preferences_node", verify_extracted_preferences_node)
    workflow.add_node("correct_preferences_node", correct_preferences_node) 
    workflow.add_node("generate_plan_node", generate_plan_node)
    #workflow.add_node("sync_node", lambda state: state) 
    workflow.add_node("refine_plan_node", refine_plan_node)
    workflow.add_node("verify_hard_constraints_node", verify_hard_constraints_node,defer = True)
    workflow.add_node("evaluate_fairness_node", evaluate_fairness_node)
    workflow.add_node("output_finale_node", return_output_node)
    
    # Definizione del flusso base (Edges)
    workflow.set_entry_point("extract_preferences_node")
    workflow.add_edge("generate_csp_node", "verify_code_node")
    workflow.add_edge("extract_preferences_node", "verify_extracted_preferences_node")
    workflow.add_edge("correct_preferences_node", "verify_extracted_preferences_node" )
    workflow.add_edge("generate_plan_node", "verify_hard_constraints_node")
    workflow.add_edge("generate_fairness_node", "verify_hard_constraints_node")
    #workflow.add_edge("sync_node", "verify_hard_constraints_node")
    workflow.add_edge("refine_plan_node", "verify_hard_constraints_node")
    # Aggiunta degli archi condizionali (Conditional Edges)
    

    workflow.add_conditional_edges(
        "verify_extracted_preferences_node",
        route_after_preferences_check,
        {
            "correct_preferences_node": "correct_preferences_node",
            "generate_plan_node": "generate_plan_node",
            "generate_csp_node": "generate_csp_node",
            "generate_fairness_node": "generate_fairness_node"
        }
    )

    workflow.add_conditional_edges(
        "verify_code_node",
        route_after_code_check,
        {
            "prosegui": "verify_hard_constraints_node",
            "generate_csp_node": "generate_csp_node"
        }
    )

    #workflow.add_conditional_edges(
    #    "sync_node",
    #    route_after_sync,
    #    {
    #        "verify_hard_constraints_node": "verify_hard_constraints_node",
    #        "sync_node": "sync_node"
    #    }
    #)
   
    workflow.add_conditional_edges(
        "verify_hard_constraints_node",
        route_after_hard_check,
        {
            "generate_plan_node": "generate_plan_node",
            "evaluate_fairness_node": "evaluate_fairness_node",
            "output_finale_node": "output_finale_node"
        }
    )

    workflow.add_conditional_edges(
        "evaluate_fairness_node",
        route_after_fairness_check,
        {
            "refine_plan_node": "refine_plan_node",
            "output_finale_node": "output_finale_node"
        }
    )

    workflow.add_edge("output_finale_node", END)
    # Compilazione del grafo
    return workflow.compile()

def get_graph(app):
    try:
        png_bytes = app.get_graph().draw_mermaid_png()
        with open("output/workflow_graph.png", "wb") as f:
            f.write(png_bytes)
    except Exception as e:
        print(f"Errore durante la generazione del grafo: {e}")
        return None


if __name__ == "c__main__":
    def leggi_piano_da_excel(percorso_file: str, lista_tutti_dipendenti = None):
        """
        Legge il piano turni da un file Excel strutturato con 3 righe (Mattina, Pomeriggio, Notte)
        e N colonne rappresentanti i giorni. Le celle contengono ID separati da virgole.
        """
        # Leggiamo il DataFrame
        import pandas as pd
        from input_type import TurniDipendente, TurnoAssegnato, Piano
        df = pd.read_excel(percorso_file)
        
        # Assumiamo che se la prima colonna contiene stringhe come "Mattina", "Pomeriggio", "Notte", 
        # i giorni veri e propri partano dalla seconda colonna (indice 1). 
        # Se il tuo file non ha l'etichetta del turno, metti semplicemente colonne_giorni = df.columns
        colonne_giorni = df.columns[1:] if len(df.columns) > 31 else df.columns
        num_giorni = len(colonne_giorni)

        # Inizializziamo un dizionario per tenere traccia dei turni: { 'A': ['R', 'R', ...], 'B': [...] }
        assegnamenti_dict = {}
        
        # Mappatura della riga dell'Excel al tipo di turno
        # Riga 0 = Mattina, Riga 1 = Pomeriggio, Riga 2 = Notte
        mappa_turni = {0: 'M', 1: 'P', 2: 'N'}
        
        # Iteriamo solo sulle prime 3 righe per sicurezza
        for indice_riga in range(3):
            turno_corrente = mappa_turni[indice_riga]
            
            # Iteriamo su tutte le colonne che rappresentano le date
            for indice_giorno, nome_colonna in enumerate(colonne_giorni):
                # Otteniamo il valore della cella
                cella = df.iloc[indice_riga, df.columns.get_loc(nome_colonna)]
                
                # Se la cella non è vuota (NaN)
                if pd.notna(cella):
                    # Dividiamo la stringa per virgola e togliamo eventuali spazi (es. "A, B, C" -> ['A', 'B', 'C'])
                    dipendenti_assegnati = [d.strip() for d in str(cella).split(',')]
                    
                    for dipendente in dipendenti_assegnati:
                        if dipendente: # Controlla che non sia una stringa vuota
                            # Se è la prima volta che incontriamo questo dipendente, inizializziamo i suoi 31 giorni a 'R'
                            if dipendente not in assegnamenti_dict:
                                assegnamenti_dict[dipendente] = ['R'] * num_giorni
                            
                            # Assegniamo il turno in quel giorno specifico
                            assegnamenti_dict[dipendente][indice_giorno] = turno_corrente

        # Se hai passato una lista con tutti i dipendenti noti (es. da 'A' a 'S'), 
        # garantiamo che anche chi non ha MAI lavorato nel mese (solo 'R') venga aggiunto al Piano
        if lista_tutti_dipendenti:
            for dipendente in lista_tutti_dipendenti:
                if dipendente not in assegnamenti_dict:
                    assegnamenti_dict[dipendente] = ['R'] * num_giorni

        # Convertiamo il dizionario negli oggetti Pydantic richiesti
        lista_turni_dipendente = []
        
        # Ordiniamo alfabeticamente gli ID dei dipendenti per avere un output pulito
        for dipendente in sorted(assegnamenti_dict.keys()):
            # Trasformiamo la lista di stringhe ['M', 'R', 'N'...] nella lista di Enum
            turni_enum = [TurnoAssegnato(t) for t in assegnamenti_dict[dipendente]]
            
            # Creiamo l'oggetto TurniDipendente
            obj_dipendente = TurniDipendente(
                id_dipendente=dipendente, 
                turni_assegnati=turni_enum
            )
            lista_turni_dipendente.append(obj_dipendente)

        # Restituiamo l'oggetto Piano finale
        return Piano(assegnamenti=lista_turni_dipendente)
    piano = leggi_piano_da_excel("/home/angelo/Project/uni/AI/progetto/output/piano_di_turni_1781509446.534241.xlsx")
    print("Piano letto da Excel e convertito in oggetto Pydantic:", piano)
    from output.csp_std import crea_modello_vincoli_hard
    from agents.evaluate_agent import assign_shifts_from_llm
    from ortools.sat.python import cp_model
    std_nurses = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M"]
    spec_nurses = ["N", "O", "P", "Q", "R", "S"]
    model = cp_model.CpModel()
    model, shifts = crea_modello_vincoli_hard(
        model=model, 
        shifts={}, 
        std_nurses=std_nurses, 
        spec_nurses=spec_nurses
    )
    nurses = std_nurses + spec_nurses
    assigned_model = assign_shifts_from_llm(model, shifts, piano, nurses)

    solver = cp_model.CpSolver()
    status = solver.Solve(assigned_model)

    print(f"Status: {status}")


if __name__ == "__main__":
    app = build_workflow()
    get_graph(app)
    
    if PREFERENCES_FILE:
        path = f"{os.getcwd()}/input/{PREFERENCES_FILE}"
        
        print("Caricamento del file di input...")
        with open(path, "r") as f:
            input_iniziale = f.read()
        print("File di input caricato correttamente.")
    if HARD_CONSTRAINTS_FILE:
        path = f"{os.getcwd()}/input/{HARD_CONSTRAINTS_FILE}"
        print("Caricamento del file dei vincoli hard...")
        with open(path, "r") as f:
            hard_constraints = f.read()
        print("File dei vincoli hard caricato correttamente.")
    if PREFERENCES_FILE and HARD_CONSTRAINTS_FILE:   
        print("Inizio del processo di generazione del piano...")
        #print(generate_strategy(hard_constraints_dal_file=hard_constraints))
        piano = app.invoke({"input":{ "preferences": input_iniziale, "hard_constraints": hard_constraints }})
        print("Piano finale generato:\n", piano.get("piano_attuale"))
    else:
        raise ValueError("Il nome del file di input non è specificato nelle variabili d'ambiente")