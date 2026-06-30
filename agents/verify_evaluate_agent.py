from input_type import SchedulerForm, GiornoSettimana, Piano
from typing import Dict
from datetime import date, timedelta
from ortools.sat.python import cp_model
from dotenv import load_dotenv
import numpy as np, sys, os, importlib

CSP_PATH = os.getenv("OUTPUT_CSP_PATH")
FEEDBACK_PATH = os.getenv("OUTPUT_FEEDBACK_PATH")

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
    """
    Importa dinamicamente un metodo specifico da un file Python generato dall'LLM.
    
    Args:
        file_path (str): Il percorso completo o relativo al file .py (es. 'output/feedback.py')
        nome_metodo (str): Il nome esatto della funzione da importare
        
    Returns:
        function: L'oggetto funzione pronto per essere eseguito.
    """
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
    
    shift_map = {
        "M": 0,  # Mattina
        "P": 1,  # Pomeriggio
        "N": 2,  # Notte
    }

    if piano_llm:
        for n in nurses:
            turni_assegnati = [piano_n for piano_n in piano_llm.assegnamenti if piano_n.id_dipendente == str(n)][0].turni_assegnati
            
            for d in range(NUM_DAYS):
                turno_llm = turni_assegnati[d].value 
                
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
        vincoli_non_soddisfatti = genera_feedback_violazioni(piano_llm, std_nurses, spec_nurses)
        print("Numero di Errori: ",len(vincoli_non_soddisfatti))
        return {
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
    
    punteggi = {}
    giorni = [giorno.value for giorno in GiornoSettimana]
    turni_map = {'M': 'mattina', 'P': 'pomeriggio', 'N': 'notte', "R": 'riposo'}

    for dipendente in state.vincoli_soft.preferenze_dipendenti:
        n = dipendente.id_dipendente
        turni_assegnati = [piano_n for piano_n in state.piano_attuale.assegnamenti if piano_n.id_dipendente == str(n)][0].turni_assegnati
        penalita = 0
        
        giorni_no = [g.value for g in dipendente.giorni_settimana_sgraditi]
        turni_no = [t.value for t in dipendente.turni_da_evitare]
        
        if dipendente.giorno_riposo_preferito:
            riposo_ottenuto = False
            pref_riposo = dipendente.giorno_riposo_preferito
            
            for d in range(31):
                if turni_assegnati[d] == 'R':
                    giorno_settimana = giorni[d % 7]
                    if pref_riposo.lower() == giorno_settimana.lower():
                        riposo_ottenuto = True
                        penalita -= 10 
                        break
            
            if not riposo_ottenuto:
                penalita += 20 

        for d in range(31):
            turni = turni_assegnati[d]
            if turni.value == 'R':
                continue 
                
            giorno_settimana = giorni[d % 7]
            is_weekend = giorno_settimana in ["sabato", "domenica"]
            
            data_str = get_data_string(d)
            richiesta_match = False 
            
            for req in dipendente.richieste_specifiche:
                if req.data != data_str:
                    continue

                turni_richiesti = [t.value if hasattr(t, 'value') else t for t in req.turno]
                turno_assegnato_match = (turni_map[turni.value] in turni_richiesti) or ("tutti" in turni_richiesti)

                if req.desiderato == False and turno_assegnato_match:
                    penalita += 15

                elif req.desiderato == True:
                    if turno_assegnato_match:
                        penalita -= 2
                        richiesta_match = True
                    else:
                        penalita += 5 
            
            if richiesta_match:
                continue
            
            if turni_map[turni.value] in turni_no:
                penalita += 10
                
            if giorno_settimana in giorni_no:
                penalita += 10
                
            if is_weekend and "weekend" in turni_no:
                penalita += 10
                
            if d > 0 and turni_assegnati[d-1] != 'R':
                turno_ieri = turni_assegnati[d-1]
                if turni_map[turni.value] in [t.value for t in dipendente.tolleranza_turni_consecutivi] and turni_map[turni.value] == turni_map[turno_ieri.value]:
                    penalita += 20

        punteggi[n] = penalita

    
    lavoratore_piu_sfortunato = max(punteggi, key=punteggi.get)
    peggior_punteggio = punteggi[lavoratore_piu_sfortunato]

    print("Fine valutazione della fairness.")
    print(f"Lavoratore più sfortunato è {lavoratore_piu_sfortunato} con un punteggio di {peggior_punteggio}.")
    
    if not state.fairness_score:
        state.fairness_score = punteggi
        return {
            "fairness_score": punteggi,
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
    