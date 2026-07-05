# # File generato automaticamente dallo Stage 2 (Coding Fairness Agent)

# # Contiene la specifica della funzione di valutazione della fairness


import datetime

# Costante globale per la mappatura dei pesi dichiarati in punteggi numerici
MAPPA_PESI = {
    "LIEVE": 2,
    "MODERATA": 5,
    "ALTA": 8,
    "VITALE": 10
}

def _get_peso_val(peso_str):
    """
    Helper per convertire una stringa di peso nel corrispondente valore numerico.
    Gestisce in modo difensivo stringhe complesse o parziali.
    """
    if not peso_str:
        return MAPPA_PESI["MODERATA"]
    p_clean = str(peso_str).upper()
    for k in MAPPA_PESI:
        if k in p_clean:
            return MAPPA_PESI[k]
    return MAPPA_PESI["MODERATA"]

def _extract_peso(pref_dict, default_weight="MODERATA"):
    """
    Estrae il peso da un dizionario di preferenza. Se la chiave 'peso' non è presente,
    tenta di ricavarla analizzando il testo degli altri campi principali.
    """
    p = pref_dict.get("peso")
    if p:
        return _get_peso_val(str(p))
    for key in ["turno", "giorno", "giorno_riposo_preferito"]:
        val = pref_dict.get(key)
        if val:
            for k in MAPPA_PESI:
                if k in str(val).upper():
                    return MAPPA_PESI[k]
    return MAPPA_PESI[default_weight]

def _normalize_pref(pref, key_name):
    """
    Normalizza la preferenza: se è una stringa la converte in un dizionario
    con la chiave specificata, altrimenti la restituisce come dizionario.
    """
    if isinstance(pref, str):
        return {key_name: pref}
    if isinstance(pref, dict):
        return pref
    return {}

def _matches_turno(turno_pref, assigned_shift, is_weekend, is_holiday):
    """
    Verifica se il turno assegnato corrisponde alla preferenza espressa.
    Gestisce categorie speciali come WEEKEND e FESTIVO.
    """
    tp = str(turno_pref).upper()
    if "MATTINA" in tp and assigned_shift == "M":
        return True
    if "POMERIGGIO" in tp and assigned_shift == "P":
        return True
    if "NOTTE" in tp and assigned_shift == "N":
        return True
    if "RIPOSO" in tp and assigned_shift == "R":
        return True
    if "WEEKEND" in tp and is_weekend and assigned_shift != "R":
        return True
    if "FESTIVO" in tp and is_holiday and assigned_shift != "R":
        return True
    return False

def _matches_spec_shift(assigned, req_shifts):
    """
    Verifica se il turno assegnato corrisponde a una lista di turni richiesti
    nelle richieste specifiche (es. 'tutti', 'mattina', 'notte').
    """
    req_shifts_lower = [str(s).lower() for s in req_shifts]
    for rs in req_shifts_lower:
        if "tutti" in rs:
            return assigned != "R"
        if "mattina" in rs and assigned == "M":
            return True
        if "pomeriggio" in rs and assigned == "P":
            return True
        if "notte" in rs and assigned == "N":
            return True
        if "riposo" in rs and assigned == "R":
            return True
    return False

def _day_matches(pref_giorno, weekday_idx):
    """
    Verifica se l'indice del giorno della settimana corrisponde al giorno preferito/sgradito.
    """
    pg = str(pref_giorno).upper()
    days_map = {
        0: ["LUNEDI", "LUNEDÌ"],
        1: ["MARTEDI", "MARTEDÌ"],
        2: ["MERCOLEDI", "MERCOLEDÌ"],
        3: ["GIOVEDI", "GIOVEDÌ"],
        4: ["VENERDI", "VENERDÌ"],
        5: ["SABATO"],
        6: ["DOMENICA"]
    }
    for term in days_map[weekday_idx]:
        if term in pg:
            return True
    return False

def calcola_fairness(piano, preferenze_dipendenti):
    """
    Calcola il punteggio di insoddisfazione per ciascun dipendente confrontando
    i turni assegnati con le sue preferenze dichiarate.
    """
    # Definizione dell'intervallo temporale: dal 7 Dicembre 2026 al 6 Gennaio 2027 (31 giorni)
    start_date = datetime.date(2026, 12, 7)
    days_info = []
    for d in range(31):
        curr_date = start_date + datetime.timedelta(days=d)
        date_str = curr_date.strftime("%Y-%m-%d")
        weekday_idx = curr_date.weekday()
        is_weekend = weekday_idx in (5, 6)
        is_national_holiday = date_str in [
            "2026-12-08",
            "2026-12-25",
            "2026-12-26",
            "2027-01-01",
            "2027-01-06"
        ]
        is_holiday = (weekday_idx == 6) or is_national_holiday
        days_info.append({
            "date_str": date_str,
            "weekday_idx": weekday_idx,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday
        })

    risultati = {}

    # Ciclo esterno su ogni dipendente presente in preferenze_dipendenti
    for preferenze in preferenze_dipendenti:
        id_dip = preferenze.get("id_dipendente")
        if not id_dip:
            continue
        
        # Gestione difensiva: se il dipendente non è presente nel piano, il suo punteggio è 0
        if id_dip not in piano:
            risultati[id_dip] = 0.0
            continue
            
        piano_dip = piano[id_dip]
        if len(piano_dip) != 31:
            risultati[id_dip] = 0.0
            continue

        # Accumulatore di penalità inizializzato a 0
        penalita = 0.0

        # 1. Turno indesiderato assegnato
        # CoT:
        # 1. Per ogni elemento {"turno": t, "peso": p} in "turni_da_evitare" del dipendente.
        # 2. Verifico se il turno assegnato al dipendente nel giorno d corrisponde a "t" (converto il
        #    codice turno "M"/"P"/"N" nel nome esteso per confrontarlo, o verifico se è weekend/festivo).
        # 3. Se corrisponde, sommo MAPPA_PESI[p] alla penalità del dipendente per ogni giorno in cui accade.
        for raw_pref in preferenze.get("turni_da_evitare", []):
            pref = _normalize_pref(raw_pref, "turno")
            if not pref:
                continue
            turno_pref = pref.get("turno", "")
            peso_val = _extract_peso(pref, "MODERATA")
            for d in range(31):
                assigned = piano_dip[d]
                day_meta = days_info[d]
                if _matches_turno(turno_pref, assigned, day_meta["is_weekend"], day_meta["is_holiday"]):
                    penalita += peso_val

        # 2. Turno desiderato NON assegnato quando avrebbe potuto esserlo (Bonus)
        # CoT:
        # 1. Per ogni elemento {"turno": t, "peso": p} in "turni_desiderati" del dipendente.
        # 2. Verifico se il turno assegnato al dipendente nel giorno d corrisponde a "t".
        # 3. Se corrisponde, sottraggo MAPPA_PESI[p] / 2 (bonus) dalla penalità del dipendente per ogni giorno in cui accade.
        for raw_pref in preferenze.get("turni_desiderati", []):
            pref = _normalize_pref(raw_pref, "turno")
            if not pref:
                continue
            turno_pref = pref.get("turno", "")
            peso_val = _extract_peso(pref, "MODERATA")
            for d in range(31):
                assigned = piano_dip[d]
                day_meta = days_info[d]
                if _matches_turno(turno_pref, assigned, day_meta["is_weekend"], day_meta["is_holiday"]):
                    penalita -= peso_val / 2.0

        # 3. Richiesta specifica su una data
        # CoT:
        # 1. Per ogni elemento {"data": d_str, "turno": [...], "desiderato": bool, "peso": p} in
        #    "richieste_specifiche", converto "data" nell'indice di giorno d (0 = 7 dicembre 2026).
        # 2. Se "desiderato" è True e il turno assegnato in quel giorno NON è tra quelli richiesti,
        #    sommo MAPPA_PESI[p] alla penalità.
        # 3. Se "desiderato" è True e il turno assegnato corrisponde, sottraggo MAPPA_PESI[p] / 2
        #    (bonus, penalità negativa).
        # 4. Se "desiderato" è False e il turno assegnato corrisponde a uno di quelli non voluti,
        #    sommo MAPPA_PESI[p] alla penalità.
        for req in preferenze.get("richieste_specifiche", []):
            if not req:
                continue
            req_date_str = req.get("data")
            if not req_date_str:
                continue
            try:
                req_date = datetime.datetime.strptime(str(req_date_str).strip(), "%Y-%m-%d").date()
                d = (req_date - start_date).days
            except Exception:
                continue
            if 0 <= d < 31:
                assigned = piano_dip[d]
                req_shifts = req.get("turno", [])
                desiderato = req.get("desiderato", False)
                peso_val = _extract_peso(req, "MODERATA")
                
                matches = _matches_spec_shift(assigned, req_shifts)
                
                if desiderato:
                    if not matches:
                        penalita += peso_val
                    else:
                        penalita -= peso_val / 2.0
                else:
                    if matches:
                        penalita += peso_val

        # 4. Giorno della settimana sgradito
        # CoT:
        # 1. Per ogni elemento {"giorno": g, "peso": p} in "giorni_settimana_sgraditi".
        # 2. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
        #    corrisponde a "g", sommo MAPPA_PESI[p] alla penalità.
        for raw_pref in preferenze.get("giorni_settimana_sgraditi", []):
            pref = _normalize_pref(raw_pref, "giorno")
            if not pref:
                continue
            giorno_pref = pref.get("giorno", "")
            peso_val = _extract_peso(pref, "MODERATA")
            for d in range(31):
                assigned = piano_dip[d]
                if assigned != "R":
                    day_meta = days_info[d]
                    if _day_matches(giorno_pref, day_meta["weekday_idx"]):
                        penalita += peso_val

        # 5. Riposo preferito non rispettato
        # CoT:
        # 1. Se "giorno_riposo_preferito" non è None, verifico se ESISTE almeno un giorno di riposo
        #    ("R" nel piano) che cade in quel giorno della settimana (o in quella data esatta, se il
        #    campo è una data invece di un nome di giorno).
        # 2. Se non esiste alcun riposo in quel giorno/data lungo tutto il mese, sommo MAPPA_PESI[peso_riposo]
        #    alla penalità (una sola volta per il mese, non per ogni occorrenza mancata).
        giorno_riposo = preferenze.get("giorno_riposo_preferito")
        if giorno_riposo:
            peso_riposo_str = preferenze.get("peso_riposo")
            if peso_riposo_str:
                peso_val = _get_peso_val(str(peso_riposo_str))
            else:
                peso_val = _extract_peso({"giorno_riposo_preferito": giorno_riposo}, "MODERATA")
            
            is_date = "-" in str(giorno_riposo)
            riposo_rispettato = False
            
            if is_date:
                try:
                    target_date = datetime.datetime.strptime(str(giorno_riposo).strip(), "%Y-%m-%d").date()
                    d = (target_date - start_date).days
                    if 0 <= d < 31:
                        if piano_dip[d] == "R":
                            riposo_rispettato = True
                except Exception:
                    pass
            else:
                for d in range(31):
                    if piano_dip[d] == "R":
                        day_meta = days_info[d]
                        if _day_matches(str(giorno_riposo), day_meta["weekday_idx"]):
                            riposo_rispettato = True
                            break
            
            if not riposo_rispettato:
                penalita += peso_val

        # 6. Turni consecutivi dello stesso tipo non tollerati
        # CoT:
        # 1. Per ogni elemento {"turno": t, "peso": p} in "tolleranza_turni_consecutivi".
        # 2. Confronto il turno del giorno d con quello del giorno d-1 (se d-1 esiste ed è != "R").
        # 3. Se i due turni coincidono ed entrambi corrispondono al tipo "t", sommo MAPPA_PESI[p]
        #    alla penalità per ogni occorrenza.
        for raw_pref in preferenze.get("tolleranza_turni_consecutivi", []):
            pref = _normalize_pref(raw_pref, "turno")
            if not pref:
                continue
            turno_pref = pref.get("turno", "")
            peso_val = _extract_peso(pref, "MODERATA")
            for d in range(1, 31):
                s_prev = piano_dip[d-1]
                s_curr = piano_dip[d]
                if s_prev != "R" and s_curr != "R" and s_prev == s_curr:
                    day_meta_prev = days_info[d-1]
                    day_meta_curr = days_info[d]
                    match_prev = _matches_turno(turno_pref, s_prev, day_meta_prev["is_weekend"], day_meta_prev["is_holiday"])
                    match_curr = _matches_turno(turno_pref, s_curr, day_meta_curr["is_weekend"], day_meta_curr["is_holiday"])
                    if match_prev and match_curr:
                        penalita += peso_val

        # 7. Giorno della settimana gradito (Bonus)
        # CoT:
        # 1. Per ogni elemento {"giorno": g, "peso": p} in "giorni_settimana_graditi".
        # 2. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
        #    corrisponde a "g", sottraggo MAPPA_PESI[p] / 2 (bonus) dalla penalità.
        for raw_pref in preferenze.get("giorni_settimana_graditi", []):
            pref = _normalize_pref(raw_pref, "giorno")
            if not pref:
                continue
            giorno_pref = pref.get("giorno", "")
            peso_val = _extract_peso(pref, "MODERATA")
            for d in range(31):
                assigned = piano_dip[d]
                if assigned != "R":
                    day_meta = days_info[d]
                    if _day_matches(giorno_pref, day_meta["weekday_idx"]):
                        penalita -= peso_val / 2.0

        # Memorizza il punteggio finale per il dipendente corrente
        risultati[id_dip] = float(penalita)

    return risultati