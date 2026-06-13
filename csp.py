from ortools.sat.python import cp_model
from typing import Dict, Any, Tuple
from input_type import SchedulerForm, Piano, TurnoAssegnato

NUM_DAYS = 31       # 7 Dicembre - 7 Gennaio
NUM_SHIFTS = 3      # 0=Mattina, 1=Pomeriggio, 2=Notte

def genera_feedback_violazioni(piano_llm: Piano, spec_nurses: list = None, num_days: int = 31) -> list:
    """
    Analizza il piano dell'LLM ed estrae i feedback in linguaggio naturale 
    sui vincoli hard violati.
    """
    errori = []
    if spec_nurses is None:
        spec_nurses = []
        
    # Struttura per contare le presenze per ogni giorno e per ogni turno
    # Formato: copertura[giorno][turno] = lista_id_dipendenti
    copertura = {d: {'M': [], 'P': [], 'N': []} for d in range(num_days)}
    
    for assegnamento in piano_llm.assegnamenti:
        n = assegnamento.id_dipendente
        turni = [t.value for t in assegnamento.turni_assegnati] # es. ['M', 'P', 'R', 'N', ...]
        
        # Popoliamo il dizionario della copertura per il CONTROLLO 5
        for d in range(num_days):
            t = turni[d]
            if t in ['M', 'P', 'N']:
                copertura[d][t].append(n)
        
        # CONTROLLO 1: Esattamente 25 turni mensili (Notte vale 2)
        carico_totale = 0
        for t in turni:
            if t in ['M', 'P']: carico_totale += 1
            elif t == 'N': carico_totale += 2
            
        if carico_totale != 25:
            errori.append(f"Il dipendente {n} ha un carico mensile di {carico_totale} turni invece dei 25 richiesti.")
            
        # CONTROLLO 2: Turni consecutivi a cavallo di 2 giorni (Notte -> Mattina)
        for d in range(num_days - 1):
            if turni[d] == 'N' and turni[d+1] == 'M':
                errori.append(f"Turni consecutivi non permessi: il dipendente {n} fa la Notte il giorno {d} e la Mattina il giorno {d+1}.")
                
        # CONTROLLO 3: Riposi post-notte (N -> R -> R)
        for d in range(num_days - 2):
            if turni[d] == 'N':
                if turni[d+1] != 'R' or turni[d+2] != 'R':
                    errori.append(f"Riposo obbligatorio mancato: il dipendente {n} non ha 2 giorni liberi dopo la Notte del giorno {d}.")
                    
        # CONTROLLO 4: Max 36 ore settimanali (Settimane FISSE, NO finestra mobile)
        # La funzione range(0, num_days, 7) crea blocchi rigidi: 0-6, 7-13, 14-20, 21-27, 28-30
        for start_d in range(0, num_days, 7):
            ore_settimanali = 0
            
            # Calcoliamo la fine della settimana fissa (bloccandola a 31 per l'ultima)
            end_d = min(start_d + 7, num_days)
            
            for d in range(start_d, end_d):
                t = turni[d]
                if t in ['M', 'P']: 
                    ore_settimanali += 6   # Turno diurno: 6 ore
                elif t == 'N': 
                    ore_settimanali += 12  # Turno notturno: 12 ore (doppio)
                    
            # Il limite massimo è di 36 ore nella settimana fissa
            if ore_settimanali > 36:
                errori.append(f"Il dipendente {n} supera le 36 ore settimanali nella settimana fissa dal giorno {start_d} al giorno {end_d - 1} (Totale: {ore_settimanali} ore).")
                

    # CONTROLLO 5: Verifica della soglia minima di persone nei turni (Copertura)
    for d in range(num_days):
        for t in ['M', 'P', 'N']:
            lavoratori_turno = copertura[d][t]
            totale_lavoratori = len(lavoratori_turno)
            
            if len(spec_nurses) > 0:
                # Caso d'uso B: Almeno 1 specializzato e almeno 3 persone in totale per turno
                spec_presenti = sum(1 for dip in lavoratori_turno if dip in spec_nurses)
                
                if totale_lavoratori < 3:
                    errori.append(f"Copertura insufficiente: il Giorno {d} nel turno di '{t}' ci sono solo {totale_lavoratori} lavoratori (minimo richiesto: 3).")
                if spec_presenti < 1:
                    errori.append(f"Mancanza specializzati: il Giorno {d} nel turno di '{t}' non ci sono lavoratori specializzati (minimo richiesto: 1).")
            else:
                # Caso d'uso A: Almeno 2 lavoratori qualsiasi per turno
                if totale_lavoratori < 2:
                    errori.append(f"Copertura insufficiente: il Giorno {d} nel turno di '{t}' ci sono solo {totale_lavoratori} lavoratori (minimo richiesto: 2).")

    return errori

def create_hard_constraints(
        std_nurses: list, 
        spec_nurses: list
) -> Tuple[cp_model.CpModel, Dict]:
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
        for start_d in range(0, NUM_DAYS, 7):
            workload_settimanale = []
            
            # end_d serve a gestire correttamente gli ultimi 3 giorni del mese (dal 28 al 30),
            # evitando che il range vada fuori dall'indice (Out of Bounds).
            end_d = min(start_d + 7, NUM_DAYS)
            
            for d in range(start_d, end_d):
                workload_settimanale.append(6 * shifts[(n, d, 0)])        # Mattina = 6 ore
                workload_settimanale.append(6 * shifts[(n, d, 1)])        # Pomeriggio = 6 ore
                workload_settimanale.append(12 * shifts[(n, d, 2)])       # Notte = 12 ore (doppio carico)
            
            # La somma delle ore nella singola settimana (o nei giorni rimanenti) 
            # non deve superare le 36 ore
            model.Add(sum(workload_settimanale) <= 36)

        giorni_liberi = []
        # VINCOLO 7: Almeno un giorno di riposo assoluto
        for d in range(NUM_DAYS):
            giorno_libero = model.NewBoolVar(f'giorno_libero_n{n}_d{d}')
            model.Add(sum(shifts[(n, d, s)] for s in range(NUM_SHIFTS)) == 0).OnlyEnforceIf(giorno_libero)
            giorni_liberi.append(giorno_libero)
        
        model.Add(sum(giorni_liberi) >= 1)

    return model,shifts

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
            # AGGIUNGI .value QUI SOTTO
                turno_llm = turni_assegnati[d].value 
                
                if turno_llm in shift_map:
                    s_assegnato = shift_map[turno_llm]
                    for s in range(NUM_SHIFTS):
                        if s == s_assegnato:
                            model.Add(shifts[(n, d, s)] == 1)
                        else:
                            model.Add(shifts[(n, d, s)] == 0)
    
    return model

def solve_hard_constraints(state: SchedulerForm) -> Dict[str, Any]:
    """
    Risolve il modello di OR-Tools e restituisce True se esiste una soluzione che soddisfa tutti i vincoli hard, altrimenti False.
    """

    vincoli_soft = state.vincoli_soft
    piano_llm = state.piano_attuale

    std_nurses = [dip.id_dipendente for dip in vincoli_soft.preferenze_dipendenti if not dip.is_specialised]
    spec_nurses = [dip.id_dipendente for dip in vincoli_soft.preferenze_dipendenti if dip.is_specialised]
    nurses = std_nurses + spec_nurses
    
    model, shifts = create_hard_constraints(std_nurses, spec_nurses)
    
    assigned_model = assign_shifts_from_llm(model, shifts, piano_llm,nurses)

    solver = cp_model.CpSolver()
    status = solver.Solve(assigned_model)

    print(f"Status: {status}")

    if status == cp_model.INFEASIBLE:
        vincoli_non_soddisfatti = genera_feedback_violazioni(piano_llm, spec_nurses = spec_nurses)
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
    