from input_type import SchedulerForm, GiornoSettimana
from csp import solve_hard_constraints
from datetime import date, timedelta

def get_data_string(d: int) -> str:
    """
    Converte l'indice del giorno (0-30) nella stringa data corrispondente,
    basandosi sull'orizzonte temporale del progetto (7 Dic 2026 - 6 Gen 2027).
    """
    data_inizio = date(2026, 12, 7)
    data_corrente = data_inizio + timedelta(days=d)
    return data_corrente.strftime("%Y-%m-%d")


def verify_hard_constraints_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 3a: Agente simbolico (OR-Tools) che verifica la validità del piano [3, 7].
    Controlla che nessuno faccia 2 turni consecutivi, limiti di ore, riposi, ecc.
    """
    
    return solve_hard_constraints(state)


def evaluate_fairness_node(state: SchedulerForm) -> SchedulerForm:
    
    punteggi = {}
    giorni = [giorno.value for giorno in GiornoSettimana]
    turni_map = {'M': 'mattina', 'P': 'pomeriggio', 'N': 'notte'}

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
            if turni == 'R':
                continue 
                
            giorno_settimana = giorni[d % 7]
            is_weekend = giorno_settimana in ["sabato", "domenica"]
            
            data_str = get_data_string(d)
            richiesta_match = False 
            
            for req in dipendente.richieste_specifiche:
                if req.data != data_str:
                    continue

                turni_richiesti = [t.value if hasattr(t, 'value') else t for t in req.turno]
                turno_assegnato_match = (turni_map[turni] in turni_richiesti) or ("tutti" in turni_richiesti)

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
            
            if turni_map[turni] in turni_no:
                penalita += 10
                
            if giorno_settimana in giorni_no:
                penalita += 10
                
            if is_weekend and "weekend" in turni_no:
                penalita += 15
                
            if d > 0 and turni_assegnati[d-1] != 'R':
                turno_ieri = turni_assegnati[d-1]
                if turni_map[turni] in [t.value for t in dipendente.tolleranza_turni_consecutivi] and turni_map[turni] == turni_map[turno_ieri]:
                    penalita += 20

        punteggi[n] = penalita

    
    lavoratore_piu_sfortunato = max(punteggi, key=punteggi.get)
    peggior_punteggio = punteggi[lavoratore_piu_sfortunato]

    print(f"\n--- VALUTAZIONE FAIRNESS ---")
    for lavoratore, score in punteggi.items():
        print(f"Dipendente {lavoratore}: Scontentezza = {score}")
    
    print(f"\nIl dipendente più sfortunato è il '{lavoratore_piu_sfortunato}' con penalità {peggior_punteggio}.")