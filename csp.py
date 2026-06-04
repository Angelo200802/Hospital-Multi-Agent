from ortools.sat.python import cp_model
from typing import Dict, Any
from input_type import SchedulerForm

NUM_DAYS = 31       # 7 Dicembre - 7 Gennaio
NUM_SHIFTS = 3      # 0=Mattina, 1=Pomeriggio, 2=Notte

def create_hard_constraints(std_nurses: list, spec_nurses: list) -> SchedulerForm:
    """
    Agente simbolico OR-Tools. Riceve il piano generato dall'LLM e 
    verifica rigorosamente i vincoli hard sui dipendenti.
    """
    nurses = std_nurses + spec_nurses
    
    model = cp_model.CpModel()
    shifts = {}
    
    # 1. Inizializzazione Variabili Booleane
    for n in nurses:
        for d in range(NUM_DAYS):
            for s in range(NUM_SHIFTS):
                shifts[(n, d, s)] = model.NewBoolVar(f'shift_n{n}_d{d}_s{s}')
                
   
    for n in nurses:
        for d in range(NUM_DAYS):
            # VINCOLO 1: Massimo 1 turno al giorno per dipendente
            model.AddAtMostOne([shifts[(n, d, s)] for s in range(NUM_SHIFTS)])
            
            # VINCOLO 2: Niente turni consecutivi a cavallo di due giorni (Notte -> Mattina)
            if d < NUM_DAYS - 1:
                model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not())

            # VINCOLO 3: 2 giorni di riposo garantiti dopo il turno di notte
            if d < NUM_DAYS - 2:
                model.Add(sum(shifts[(n, d+1, s)] for s in range(NUM_SHIFTS)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])
                model.Add(sum(shifts[(n, d+2, s)] for s in range(NUM_SHIFTS)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])
            elif d == NUM_DAYS - 2:
                # Bordo del mese (ultimo e penultimo giorno)
                model.Add(sum(shifts[(n, d+1, s)] for s in range(NUM_SHIFTS)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])
    
    # VINCOLO 4: Requisiti di copertura per ogni turno
    for d in range(NUM_DAYS):
        for s in range(NUM_SHIFTS):
            if len(spec_nurses) > 0:
                # Caso d'uso B: Almeno 1 specializzato e almeno 3 persone in totale per turno
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)
                model.Add(sum(shifts[(n, d, s)] for n in nurses) >= 3)
            else:
                # Caso d'uso A: Almeno 2 lavoratori qualsiasi per turno
                model.Add(sum(shifts[(n, d, s)] for n in nurses) >= 2)

    
    for n in nurses:
        workload_mensile = []
        # VINCOLO 5: 25 turni mensili (considerando la notte come carico di lavoro doppio)
        for d in range(NUM_DAYS):
            workload_mensile.append(shifts[(n, d, 0)])           # Mattina = peso 1
            workload_mensile.append(shifts[(n, d, 1)])           # Pomeriggio = peso 1
            workload_mensile.append(2 * shifts[(n, d, 2)])       # Notte = peso 2
        model.Add(sum(workload_mensile) == 25)

        # VINCOLO 6: Massimo 36 ore settimanali (Finestra mobile di 7 giorni)
        for start_d in range(NUM_DAYS - 6):
            workload_settimanale = []
            for d in range(start_d, start_d + 7):
                workload_settimanale.append(6 * shifts[(n, d, 0)]) 
                workload_settimanale.append(6 * shifts[(n, d, 1)]) 
                workload_settimanale.append(6 * 2 * shifts[(n, d, 2)]) 
            
            model.Add(sum(workload_settimanale) <= 36)

        giorni_liberi = []
        # VINCOLO 7: Almeno un giorno di riposo assoluto
        for d in range(NUM_DAYS):
            giorno_libero = model.NewBoolVar(f'giorno_libero_n{n}_d{d}')
            model.Add(sum(shifts[(n, d, s)] for s in range(NUM_SHIFTS)) == 0).OnlyEnforceIf(giorno_libero)
            giorni_liberi.append(giorno_libero)
        
        model.Add(sum(giorni_liberi) >= 1)

    return model,shifts

def assign_shifts_from_llm(model: cp_model.CpModel, shifts: Dict, piano_llm: Dict[str, Any],nurses: list[str]):
    
    shift_map = {
        "M": 0,  # Mattina
        "P": 1,  # Pomeriggio
        "N": 2,  # Notte
    }

    if piano_llm:
        for n in nurses:
            # Ottiene la lista di 31 turni per il dipendente 'n' (es. ['M', 'R', 'N', ...])
            # Se un dipendente manca, riempie i suoi turni con Riposi ('R')
            turni_assegnati = piano_llm.get(str(n), ['R'] * NUM_DAYS)
            
            for d in range(NUM_DAYS):
                turno_llm = turni_assegnati[d]
                if turno_llm in shift_map:
                    s_assegnato = shift_map[turno_llm]
                    for s in range(NUM_SHIFTS):
                        if s == s_assegnato:
                            model.Add(shifts[(n, d, s)] == 1)
                        else:
                            model.Add(shifts[(n, d, s)] == 0)
                else:
                    # Se ha il giorno di riposo ('R'), tutte le variabili di quel giorno valgono 0
                    for s in range(NUM_SHIFTS):
                        model.Add(shifts[(n, d, s)] == 0)
    
    return model

def solve_hard_constraints(state: SchedulerForm) -> bool:
    """
    Risolve il modello di OR-Tools e restituisce True se esiste una soluzione che soddisfa tutti i vincoli hard, altrimenti False.
    """

    vincoli_soft = state.get("vincoli_soft", {})
    piano_llm = state.get("piano_attuale", {})

    std_nurses = [dip.id for dip in vincoli_soft.preferenze_dipendenti if not dip.is_specialised]
    spec_nurses = [dip.id for dip in vincoli_soft.preferenze_dipendenti if dip.is_specialised]
    nurses = std_nurses + spec_nurses
    
    model, shifts = create_hard_constraints(std_nurses, spec_nurses)
    
    assigned_model = assign_shifts_from_llm(model, shifts, piano_llm,nurses)

    solver = cp_model.CpSolver()
    status = solver.Solve(assigned_model)

    print(f"Status: {status}")