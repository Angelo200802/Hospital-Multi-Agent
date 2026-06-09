from input_type import SchedulerForm, GiornoSettimana
from csp import solve_hard_constraints

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
            
            # --- GERARCHIA: Le richieste specifiche battono le preferenze generali ---
            # Verifichiamo se in questo giorno (d) c'era una richiesta specifica (es. voleva fare la mattina)
            # Nota: qui dovresti mappare 'd' (0-30) alla stringa data 'YYYY-MM-DD' per fare il match esatto.
            richiesta_match = False 
            # Esempio logico (assumendo che tu abbia una funzione get_data_string(d)):
            # data_str = get_data_string(d)
            # for req in dipendente.richieste_specifiche:
            #     if req.data == data_str and req.desiderato == True and cat_map[turno] in req.turno:
            #         richiesta_match = True 
            
            # Se è una richiesta specifica esaudita, non calcoliamo penalità per questo giorno
            if richiesta_match:
                penalita -= 2
                continue
            
            if turni_map[turni] in turni_no:
                penalita += 10
                
            # Aggiunta penalità per giorno della settimana sgradito (es. odia il venerdì)
            if giorno_settimana in giorni_no:
                penalita += 10
                
            # Aggiunta penalità per weekend (se esplicitamente sgradito nella CategoriaTurno)
            if is_weekend and "weekend" in turni_no:
                penalita += 15
                
            # 3. CONTROLLO TURNI CONSECUTIVI SGRADITI (es. non vuole fare turni di notte consecutivi) [7, 9]
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