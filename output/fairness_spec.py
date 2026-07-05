# # File generato automaticamente dallo Stage 2 (Coding Fairness Agent)

# # Contiene la specifica della funzione di valutazione della fairness


from datetime import datetime, timedelta
import re

# Costante globale per la conversione dei pesi in punteggi numerici di insoddisfazione
MAPPA_PESI = {
    "LIEVE": 2,
    "MODERATA": 5,
    "ALTA": 8,
    "VITALE": 10
}

def get_weight(weight_str):
    """
    Estrae il valore numerico del peso a partire dalla stringa descrittiva.
    Se non specificato o non trovato, restituisce il valore di default MODERATA (5).
    """
    if not weight_str:
        return MAPPA_PESI["MODERATA"]
    weight_str = str(weight_str).upper()
    for key in MAPPA_PESI:
        if key in weight_str:
            return MAPPA_PESI[key]
    return MAPPA_PESI["MODERATA"]

def normalize_day(day_str):
    """
    Normalizza i nomi dei giorni della settimana in italiano per facilitare il confronto.
    Rimuove accenti e converte in minuscolo.
    """
    if not day_str:
        return ""
    day_str = str(day_str).upper()
    if "LUNEDI" in day_str or "LUNEDÌ" in day_str: return "lunedi"
    if "MARTEDI" in day_str or "MARTEDÌ" in day_str: return "martedi"
    if "MERCOLEDI" in day_str or "MERCOLEDÌ" in day_str: return "mercoledi"
    if "GIOVEDI" in day_str or "GIOVEDÌ" in day_str: return "giovedi"
    if "VENERDI" in day_str or "VENERDÌ" in day_str: return "venerdi"
    if "SABATO" in day_str: return "sabato"
    if "DOMENICA" in day_str: return "domenica"
    return day_str.lower()

def parse_preference_item(item):
    """
    Parsifica un elemento di preferenza che può essere un dizionario strutturato
    oppure una stringa contenente il peso (es. 'CategoriaTurno.MATTINA (Peso ImportanzaPreferenza.MODERATA)').
    Ritorna una tupla (valore, peso_str).
    """
    if isinstance(item, dict):
        val = item.get("turno") or item.get("giorno")
        peso = item.get("peso", "MODERATA")
        return val, peso
    elif isinstance(item, str):
        match = re.search(r'(.*?)\s*\(Peso\s+ImportanzaPreferenza\.(\w+)\)', item)
        if match:
            val = match.group(1).strip()
            peso = match.group(2).strip()
            return val, peso
        else:
            return item, "MODERATA"
    return None, "MODERATA"

def matches_shift(shift_code, pref_shift_str, date_str, day_of_week):
    """
    Verifica se il codice turno assegnato ("M", "P", "N", "R") corrisponde
    alla preferenza espressa (es. "MATTINA", "WEEKEND", "FESTIVO", "TUTTI").
    """
    if not pref_shift_str:
        return False
    pref = str(pref_shift_str).upper()
    code_map = {"M": "MATTINA", "P": "POMERIGGIO", "N": "NOTTE", "R": "RIPOSO"}
    normalized_code = code_map.get(shift_code, "")
    
    if "MATTINA" in pref and normalized_code == "MATTINA":
        return True
    if "POMERIGGIO" in pref and normalized_code == "POMERIGGIO":
        return True
    if "NOTTE" in pref and normalized_code == "NOTTE":
        return True
    if "RIPOSO" in pref and normalized_code == "RIPOSO":
        return True
    if "WEEKEND" in pref:
        if day_of_week in ["sabato", "domenica"]:
            return True
    if "FESTIVO" in pref:
        holidays = ["2026-12-08", "2026-12-25", "2026-12-26", "2027-01-01", "2027-01-06"]
        if date_str in holidays or day_of_week == "domenica":
            return True
    if "TUTTI" in pref:
        # "TUTTI" si riferisce a qualsiasi turno lavorativo (esclude il riposo)
        return normalized_code != "RIPOSO"
    
    # Fallback per confronto diretto
    if pref.lower() == shift_code.lower() or pref.lower() == normalized_code.lower():
        return True
    return False

def calcola_fairness(piano, preferenze_dipendenti):
    """
    Calcola il punteggio di insoddisfazione per ciascun dipendente confrontando
    i turni assegnati con le sue preferenze dichiarate.
    """
    if not piano or not preferenze_dipendenti:
        return {}

    punteggi = {}
    start_date = datetime(2026, 12, 7)
    
    # Precalcolo delle date e dei giorni della settimana per i 31 giorni del piano
    days_info = []
    dow_map = {0: "lunedi", 1: "martedi", 2: "mercoledi", 3: "giovedi", 4: "venerdi", 5: "sabato", 6: "domenica"}
    for d in range(31):
        current_date = start_date + timedelta(days=d)
        date_str = current_date.strftime("%Y-%m-%d")
        day_of_week = dow_map[current_date.weekday()]
        days_info.append((date_str, day_of_week))

    for emp_pref in preferenze_dipendenti:
        if not isinstance(emp_pref, dict):
            continue
        emp_id = emp_pref.get("id_dipendente")
        if not emp_id:
            continue
        
        # Gestione difensiva: se il dipendente non è presente nel piano o ha turni incompleti, assegna 0
        assigned_shifts = piano.get(emp_id)
        if not assigned_shifts or len(assigned_shifts) < 31:
            punteggi[emp_id] = 0
            continue
        
        penalty = 0

        # ---------------------------------------------------------------------
        # REGOLA 1: Turno indesiderato assegnato
        # CoT:
        # 1. Per ogni elemento {"turno": t, "peso": p} in "turni_da_evitare" del dipendente.
        # 2. Verifico se il turno assegnato al dipendente nel giorno d corrisponde a "t" (converto il
        #    codice turno "M"/"P"/"N" nel nome esteso per confrontarlo).
        # 3. Se corrisponde, sommo MAPPA_PESI[p] alla penalità del dipendente per ogni giorno in cui accade.
        # ---------------------------------------------------------------------
        for d in range(31):
            shift_code = assigned_shifts[d]
            date_str, day_of_week = days_info[d]
            for avoid_item in emp_pref.get("turni_da_evitare", []):
                t, p = parse_preference_item(avoid_item)
                if t and matches_shift(shift_code, t, date_str, day_of_week):
                    penalty += get_weight(p)

        # ---------------------------------------------------------------------
        # REGOLA 2: Turno desiderato NON assegnato quando avrebbe potuto esserlo (Bonus)
        # CoT:
        # 1. Questa regola contribuisce SOLO come bonus quando il turno desiderato viene effettivamente
        #    assegnato (sottraendo una frazione di MAPPA_PESI[p], es. metà), mai come penalità per la sua assenza.
        # 2. Per ogni elemento {"turno": t, "peso": p} in "turni_desiderati" del dipendente.
        # 3. Se il turno assegnato nel giorno d corrisponde a "t", sottraggo MAPPA_PESI[p] // 2 dalla penalità.
        # ---------------------------------------------------------------------
        for d in range(31):
            shift_code = assigned_shifts[d]
            date_str, day_of_week = days_info[d]
            for des_item in emp_pref.get("turni_desiderati", []):
                t, p = parse_preference_item(des_item)
                if t and matches_shift(shift_code, t, date_str, day_of_week):
                    penalty -= get_weight(p) // 2

        # ---------------------------------------------------------------------
        # REGOLA 3: Richiesta specifica su una data
        # CoT:
        # 1. Per ogni elemento {"data": d_str, "turno": [...], "desiderato": bool, "peso": p} in
        #    "richieste_specifiche", converto "data" nell'indice di giorno d (0 = 7 dicembre 2026).
        # 2. Se "desiderato" è True e il turno assegnato in quel giorno NON è tra quelli richiesti,
        #    sommo MAPPA_PESI[p] alla penalità.
        # 3. Se "desiderato" è True e il turno assegnato corrisponde, sottraggo MAPPA_PESI[p] // 2
        #    (bonus, penalità negativa).
        # 4. Se "desiderato" è False e il turno assegnato corrisponde a uno di quelli non voluti,
        #    sommo MAPPA_PESI[p] alla penalità.
        # ---------------------------------------------------------------------
        for req in emp_pref.get("richieste_specifiche", []):
            if not req:
                continue
            req_date = req.get("data")
            if not req_date:
                continue
            try:
                req_dt = datetime.strptime(req_date, "%Y-%m-%d")
                d = (req_dt - start_date).days
            except Exception:
                continue
            
            if 0 <= d <= 30:
                shift_code = assigned_shifts[d]
                date_str, day_of_week = days_info[d]
                req_shifts = req.get("turno", [])
                if isinstance(req_shifts, str):
                    req_shifts = [req_shifts]
                desiderato = req.get("desiderato", False)
                p = req.get("peso", "MODERATA")
                
                matches = any(matches_shift(shift_code, rs, date_str, day_of_week) for rs in req_shifts)
                
                if desiderato:
                    if not matches:
                        penalty += get_weight(p)
                    else:
                        penalty -= get_weight(p) // 2
                else:
                    if matches:
                        penalty += get_weight(p)

        # ---------------------------------------------------------------------
        # REGOLA 4: Giorno della settimana sgradito
        # CoT:
        # 1. Per ogni elemento {"giorno": g, "peso": p} in "giorni_settimana_sgraditi".
        # 2. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
        #    corrisponde a "g", sommo MAPPA_PESI[p] alla penalità.
        # ---------------------------------------------------------------------
        for d in range(31):
            shift_code = assigned_shifts[d]
            if shift_code != "R":
                date_str, day_of_week = days_info[d]
                for sgradito in emp_pref.get("giorni_settimana_sgraditi", []):
                    g, p = parse_preference_item(sgradito)
                    if g and normalize_day(g) == day_of_week:
                        penalty += get_weight(p)

        # ---------------------------------------------------------------------
        # REGOLA 5: Riposo preferito non rispettato
        # CoT:
        # 1. Se "giorno_riposo_preferito" non è None, verifico se ESISTE almeno un giorno di riposo
        #    ("R" nel piano) che cade in quel giorno della settimana (o in quella data esatta, se il
        #    campo è una data invece di un nome di giorno).
        # 2. Se non esiste alcun riposo in quel giorno/data lungo tutto il mese, sommo MAPPA_PESI[peso_riposo]
        #    alla penalità (una sola volta per il mese, non per ogni occorrenza mancata).
        # ---------------------------------------------------------------------
        pref_riposo = emp_pref.get("giorno_riposo_preferito")
        peso_riposo = emp_pref.get("peso_riposo", "MODERATA")
        
        if pref_riposo:
            # Estrazione difensiva del peso se incorporato nella stringa del giorno di riposo
            if isinstance(pref_riposo, str):
                match = re.search(r'(.*?),\s*\(Peso\s+ImportanzaPreferenza\.(\w+)\)', pref_riposo)
                if match:
                    pref_riposo = match.group(1).strip()
                    peso_riposo = match.group(2).strip()
            
            found_riposo = False
            for d in range(31):
                shift_code = assigned_shifts[d]
                if shift_code == "R":
                    date_str, day_of_week = days_info[d]
                    if "-" in str(pref_riposo):  # È una data specifica (YYYY-MM-DD)
                        if str(pref_riposo).strip() == date_str:
                            found_riposo = True
                            break
                    else:  # È un giorno della settimana ricorrente
                        if normalize_day(pref_riposo) == day_of_week:
                            found_riposo = True
                            break
            if not found_riposo:
                penalty += get_weight(peso_riposo)

        # ---------------------------------------------------------------------
        # REGOLA 6: Turni consecutivi dello stesso tipo non tollerati
        # CoT:
        # 1. Per ogni elemento {"turno": t, "peso": p} in "tolleranza_turni_consecutivi".
        # 2. Confronto il turno del giorno d con quello del giorno d-1 (se d-1 esiste ed è != "R").
        # 3. Se i due turni coincidono ed entrambi corrispondono al tipo "t", sommo MAPPA_PESI[p]
        #    alla penalità per ogni occorrenza.
        # ---------------------------------------------------------------------
        for d in range(1, 31):
            shift_curr = assigned_shifts[d]
            shift_prev = assigned_shifts[d-1]
            if shift_prev != "R" and shift_curr == shift_prev:
                date_str, day_of_week = days_info[d]
                for tol in emp_pref.get("tolleranza_turni_consecutivi", []):
                    t, p = parse_preference_item(tol)
                    if t and matches_shift(shift_curr, t, date_str, day_of_week):
                        penalty += get_weight(p)

        # ---------------------------------------------------------------------
        # REGOLA 7: Giorno della settimana gradito (Bonus)
        # CoT:
        # 1. Questa regola contribuisce SOLO come bonus quando il giorno della settimana gradito viene
        #    effettivamente assegnato come giorno lavorativo (turno != "R"), sottraendo una frazione di
        #    MAPPA_PESI[p] (es. metà), mai come penalità per la sua assenza.
        # 2. Per ogni elemento {"giorno": g, "peso": p} in "giorni_settimana_graditi".
        # 3. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
        #    corrisponde a "g", sottraggo MAPPA_PESI[p] // 2 dalla penalità.
        # ---------------------------------------------------------------------
        for d in range(31):
            shift_code = assigned_shifts[d]
            if shift_code != "R":
                date_str, day_of_week = days_info[d]
                for gradito in emp_pref.get("giorni_settimana_graditi", []):
                    g, p = parse_preference_item(gradito)
                    if g and normalize_day(g) == day_of_week:
                        penalty -= get_weight(p) // 2

        # Salvataggio del punteggio finale (garantendo che non sia negativo)
        punteggi[emp_id] = max(0, penalty)

    return punteggi