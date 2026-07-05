from input_type import SchedulerForm, GiornoSettimana, Piano, TurnoAssegnato
from typing import Dict, List
from datetime import date, timedelta
from ortools.sat.python import cp_model
from dotenv import load_dotenv
import numpy as np, sys, os, importlib

CSP_PATH = os.getenv("OUTPUT_CSP_PATH")
FEEDBACK_PATH = os.getenv("OUTPUT_FEEDBACK_PATH")
FAIRNESS_PATH = os.getenv("OUTPUT_FAIRNESS_PATH")

NUM_DAYS = 31       # 7 Dicembre - 7 Gennaio
NUM_SHIFTS = 3      # 0=Mattina, 1=Pomeriggio, 2=Notte


def get_data_string(d: int) -> str:
    """
    Converte l'indice del giorno (0-30) nella stringa data corrispondente,
    basandosi sull'orizzonte temporale del progetto (7 Dic 2026 - 6 Gen 2027).
    """
    data_inizio = date(2026, 12, 7)
    data_corrente = data_inizio + timedelta(days=d)
    return data_corrente.strftime("%Y-%m-%d")

def importa_funzione_da_file(file_path: str, nome_metodo: str):
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Errore: Il file '{file_path}' non è stato trovato.")
        
    
    nome_modulo = os.path.splitext(os.path.basename(file_path))[0]
    spec = importlib.util.spec_from_file_location(nome_modulo, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Errore: Impossibile creare le specifiche per '{file_path}'.")
        
    modulo = importlib.util.module_from_spec(spec)
    
    sys.modules[nome_modulo] = modulo
    
    try:
        spec.loader.exec_module(modulo)
    except Exception as e:
        raise RuntimeError(f"Errore durante l'esecuzione del codice nel file '{file_path}': {e}")
        
    try:
        funzione = getattr(modulo, nome_metodo)
        return funzione
    except AttributeError:
        raise AttributeError(f"Errore: Il metodo '{nome_metodo}' non è presente nel file '{file_path}'. Controlla che l'LLM lo abbia generato correttamente.")

def assign_shifts_from_llm(
        model: cp_model.CpModel, 
        shifts: Dict, 
        piano_llm: Piano,
        nurses: list[str]
) -> cp_model.CpModel:
    
    piano_llm : dict[str, List[str]] = piano_llm.to_dict()

    shift_map = {
        "M": 0,  # Mattina
        "P": 1,  # Pomeriggio
        "N": 2,  # Notte
    }

    if piano_llm:
        for n in nurses:
            turni_assegnati = piano_llm.get(n, [])
            
            for d in range(NUM_DAYS):
                turno_llm = turni_assegnati[d]
                
                if turno_llm in shift_map:
                    s_assegnato = shift_map[turno_llm]
                    for s in range(NUM_SHIFTS):
                        if s == s_assegnato:
                            model.Add(shifts[(n, d, s)] == 1)
                        else:
                            model.Add(shifts[(n, d, s)] == 0)
    
    return model

def verify_hard_constraints_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 3a: Agente simbolico (OR-Tools) che verifica la validità del piano [3, 7].
    Controlla che nessuno faccia 2 turni consecutivi, limiti di ore, riposi, ecc.
    """
    
    print('Verifica dei vincoli hard in corso')
    
    model = cp_model.CpModel()

    vincoli_soft = state.vincoli_soft
    piano_llm = state.piano_attuale

    std_nurses = [dip.id_dipendente for dip in vincoli_soft.preferenze_dipendenti if not dip.is_specialised]
    spec_nurses = [dip.id_dipendente for dip in vincoli_soft.preferenze_dipendenti if dip.is_specialised]
    nurses = std_nurses + spec_nurses
    
    crea_modello_csp = importa_funzione_da_file(
        file_path=CSP_PATH, 
        nome_metodo="crea_modello_vincoli_hard"
    )

    genera_feedback_violazioni = importa_funzione_da_file(
        file_path=FEEDBACK_PATH, 
        nome_metodo="estrai_feedback_errori_hard"
    )

    # Esegui il setup del modello
    model, shifts = crea_modello_csp(model, {}, std_nurses, spec_nurses)
    
    assigned_model = assign_shifts_from_llm(model, shifts, piano_llm,nurses)
    solver = cp_model.CpSolver()
    status = solver.Solve(assigned_model)

    print(f"Status: {status}")

    if status == cp_model.INFEASIBLE:
        vincoli_non_soddisfatti = genera_feedback_violazioni(piano_llm.to_dict(), std_nurses, spec_nurses)
        print("Numero di Errori: ",len(vincoli_non_soddisfatti))
        return {
            "condizione_di_stop": "None" if state.best_plan is None else "Vincoli Hard Violati nel Raffinamento",
            "hard_constraints_valid" : False, 
            "feedback_errori_hard" : "\n".join(vincoli_non_soddisfatti)}

    elif status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
        print("Il piano generato rispetta perfettamente tutti i vincoli hard.")
        return {
            "hard_constraints_valid" : True
        }
        
    else:
        print("Stato del risolvitore sconosciuto o tempo scaduto.")
        return {
            "hard_constraints_valid" : False,
            "feedback_errori_hard" : "Impossibile determinare la validità del piano (Errore generico del risolvitore)."
        }


def evaluate_fairness_node(state: SchedulerForm) -> SchedulerForm:
    
    print('Valutazione della fairness in corso')
    
    valuta_fairness = importa_funzione_da_file(
        file_path=FAIRNESS_PATH, 
        nome_metodo="calcola_fairness"
    )
    
    punteggi : Dict = valuta_fairness(state.piano_attuale.to_dict(), [p.model_dump(mode="json") for p in state.vincoli_soft.preferenze_dipendenti])

    
    lavoratore_piu_sfortunato = max(punteggi, key=punteggi.get)
    peggior_punteggio = punteggi[lavoratore_piu_sfortunato]

    print("Fine valutazione della fairness.")
    print(f"Lavoratore più sfortunato è {lavoratore_piu_sfortunato} con un punteggio di {peggior_punteggio}.")
    
    if not state.fairness_score:
        state.fairness_score = punteggi
        return {
            "fairness_score": punteggi,
            "best_plan": state.piano_attuale,
            "dipendente_piu_sfortunato": [lavoratore_piu_sfortunato],
            "terminazione_raggiunta": False    
        }

    if peggior_punteggio > max(state.fairness_score.values()):
        return {
            "condizione_di_stop": "Fairness Score Peggiorato",
            "terminazione_raggiunta": True
        }
    if peggior_punteggio < max(state.fairness_score.values()):
        state.dipendente_piu_sfortunato.append(lavoratore_piu_sfortunato)
        return {
                "fairness_score": punteggi,
                "best_plan": state.piano_attuale,  
                "dipendente_piu_sfortunato": state.dipendente_piu_sfortunato,
                "terminazione_raggiunta": False    
            }
    
    media_nuovi_punteggi = np.mean(list(punteggi.values()))
    media_vecchi_punteggi = np.mean(list(state.fairness_score.values()))

    if media_nuovi_punteggi >= media_vecchi_punteggi:
        return {
            "condizione_di_stop": "Fairness Score Non Migliorato",
            "terminazione_raggiunta": True
        }
    if media_nuovi_punteggi < media_vecchi_punteggi:
        state.dipendente_piu_sfortunato.append(lavoratore_piu_sfortunato)
        return {
                "fairness_score": punteggi,
                "best_plan": state.piano_attuale,  
                "dipendente_piu_sfortunato": state.dipendente_piu_sfortunato,
                "terminazione_raggiunta": False    
            }
    