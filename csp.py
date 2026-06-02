from ortools.sat.python import cp_model
from typing import Dict, Any

def verify_hard_constraints_ortools(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Agente simbolico OR-Tools. Riceve il piano generato dall'LLM e 
    verifica rigorosamente i 4 vincoli hard sui dipendenti.
    """
    piano_llm = state.get("piano_attuale", {})
    
    num_nurses = 10
    num_days = 31       # 7 Dicembre - 7 Gennaio
    num_shifts = 3      # 0=Mattina, 1=Pomeriggio, 2=Notte
    shift_map = {'M': 0, 'P': 1, 'N': 2}
    
    model = cp_model.CpModel()
    
    # 1. Inizializzazione Variabili Booleane
    shifts = {}
    for n in range(num_nurses):
        for d in range(num_days):
            for s in range(num_shifts):
                shifts[(n, d, s)] = model.NewBoolVar(f'shift_n{n}_d{d}_s{s}')
                
    # ==============================================================
    # 2. DEFINIZIONE DEI 4 VINCOLI HARD SUI DIPENDENTI
    # ==============================================================
    
    for n in range(num_nurses):
        
        # Vincolo 1: Massimo 1 turno al giorno [3, 4]
        for d in range(num_days):
            model.AddAtMostOne(shifts[(n, d, s)] for s in range(num_shifts))
            
        # Vincolo 2: Turni non consecutivi [3, 5, 6]
        # Evita che il dipendente faccia un turno il giorno prima e il turno mattutino il giorno dopo.
        # (Nota: La Notte seguita dalla Mattina è già severamente vietata dal Vincolo 4,
        # quindi qui copriamo il caso del Pomeriggio seguito dalla Mattina).
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 1)], shifts[(n, d+1, 0)].Not())
            
        # Vincolo 3: Deve essere garantito almeno 1 giorno di riposo nel mese [3, 7]
        giorni_lavorati = []
        for d in range(num_days):
            lavora_oggi = model.NewBoolVar(f'lavora_n{n}_d{d}')
            # lavora_oggi vale 1 se l'infermiere fa almeno un turno, 0 altrimenti
            model.Add(lavora_oggi == sum(shifts[(n, d, s)] for s in range(num_shifts)))
            giorni_lavorati.append(lavora_oggi)
            
        # Affinché ci sia almeno 1 giorno libero su 31, la somma dei giorni presenziati deve essere <= 30
        model.Add(sum(giorni_lavorati) <= num_days - 1)
        
        # Vincolo 4: Dopo la Notte, 2 giorni interi di riposo [2, 8, 9]
        for d in range(num_days):
            if d + 1 < num_days:
                for s in range(num_shifts):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, s)].Not())
            if d + 2 < num_days:
                for s in range(num_shifts):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+2, s)].Not())

    # ==============================================================
    # 3. VINCOLI STRUTTURALI (Necessari per il funzionamento del reparto)
    # ==============================================================
    # Tutti i turni devono essere coperti da almeno 2 persone [2]
    for d in range(num_days):
        for s in range(num_shifts):
            model.Add(sum(shifts[(n, d, s)] for n in range(num_nurses)) >= 2)
            
    # Esattamente 25 turni mensili da smaltire per ciascun dipendente [1, 2]
    for n in range(num_nurses):
        model.Add(sum(shifts[(n, d, s)] for d in range(num_days) for s in range(num_shifts)) == 25)

    # ==============================================================
    # 4. INIEZIONE DEL PIANO DELL'LLM E VERIFICA LOGICA
    # ==============================================================
    if piano_llm:
        for n in range(num_nurses):
            # Ottiene la lista di 31 turni per il dipendente 'n' (es. ['M', 'R', 'N', ...])
            # Se un dipendente manca, riempie i suoi turni con Riposi ('R')
            turni_assegnati = piano_llm.get(str(n), ['R'] * num_days)
            for d in range(num_days):
                turno_llm = turni_assegnati[d]
                if turno_llm in shift_map:
                    s_assegnato = shift_map[turno_llm]
                    for s in range(num_shifts):
                        if s == s_assegnato:
                            model.Add(shifts[(n, d, s)] == 1)
                        else:
                            model.Add(shifts[(n, d, s)] == 0)
                else:
                    # Se ha il giorno di riposo ('R'), tutte le variabili di quel giorno valgono 0
                    for s in range(num_shifts):
                        model.Add(shifts[(n, d, s)] == 0)

    # Esecuzione del Risolutore
    solver = cp_model.CpSolver()
    status = solver.Solve(model)
    
    # Valutazione finale
    if status in [cp_model.FEASIBLE, cp_model.OPTIMAL]:
        return {
            "hard_constraints_valid": True,
            "feedback_errori_hard": "Validazione superata. L'LLM ha rispettato tutti i vincoli."
        }
    else:
        return {
            "hard_constraints_valid": False,
            "feedback_errori_hard": "Piano rigettato. L'LLM ha violato uno o più vincoli hard."
        }