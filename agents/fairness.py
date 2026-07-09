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

def calcola_fairness(piano, preferenze_dipendenti):
    # Gestione difensiva iniziale per input nulli o vuoti
    if not piano or not preferenze_dipendenti:
        return {}

    # Data di inizio del piano: 7 Dicembre 2026
    start_date = datetime.date(2026, 12, 7)
    giorni_settimana = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
    festivi_date = {"2026-12-08", "2026-12-25", "2026-12-26", "2027-01-01", "2027-01-06"}

    # Pre-calcolo delle informazioni sui 31 giorni per ottimizzare e semplificare i confronti
    days_info = []
    for d in range(31):
        curr_date = start_date + datetime.timedelta(days=d)
        date_str = curr_date.isoformat()
        weekday_idx = curr_date.weekday()
        weekday_name = giorni_settimana[weekday_idx]
        is_weekend = weekday_idx in (5, 6)
        is_holiday = date_str in festivi_date
        days_info.append({
            "date": date_str,
            "weekday": weekday_name,
            "is_weekend": is_weekend,
            "is_holiday": is_holiday
        })

    # Helper per estrarre il valore numerico del peso in modo sicuro e difensivo
    def get_peso_valore(peso_str):
        if not peso_str:
            return MAPPA_PESI["MODERATA"]
        peso_upper = str(peso_str).upper()
        for key in MAPPA_PESI:
            if key in peso_upper:
                return MAPPA_PESI[key]
        return MAPPA_PESI["MODERATA"]

    # Helper per normalizzare i codici dei turni e gestire formati stringa complessi
    def normalize_shift(s):
        if not s:
            return ""
        s_upper = str(s).upper()
        if "MATTINA" in s_upper or s_upper == "M":
            return "M"
        if "POMERIGGIO" in s_upper or s_upper == "P":
            return "P"
        if "NOTTE" in s_upper or s_upper == "N":
            return "N"
        if "RIPOSO" in s_upper or s_upper == "R":
            return "R"
        if "WEEKEND" in s_upper:
            return "WEEKEND"
        if "FESTIVO" in s_upper:
            return "FESTIVO"
        if "TUTTI" in s_upper:
            return "TUTTI"
        return s_upper

    # Helper universale per fare il parsing di preferenze espresse sia come dict che come stringhe grezze
    def parse_preference_item(item):
        if isinstance(item, str):
            val = item
            peso = "MODERATA"
            if "Peso" in item:
                parts = item.split("Peso")
                val = parts[0].strip()
                peso_part = parts[1]
                for k in MAPPA_PESI:
                    if k in peso_part.upper():
                        peso = k
                        break
            if "." in val:
                val = val.split(".")[-1]
            val = val.replace("(", "").replace(")", "").strip()
            return {"val": val, "peso": peso}
        elif isinstance(item, dict):
            val = item.get("turno") or item.get("giorno") or item.get("val")
            peso = item.get("peso", "MODERATA")
            if val and "." in str(val):
                val = str(val).split(".")[-1]
            return {"val": val, "peso": peso}
        return {"val": None, "peso": "MODERATA"}

    risultati_fairness = {}

    # Ciclo esterno su ciascun dipendente presente nelle preferenze strutturate
    for pref in preferenze_dipendenti:
        id_dip = pref.get("id_dipendente")
        if not id_dip:
            continue

        # Se il dipendente non è presente nel piano, il suo punteggio viene inizializzato a 0 e saltato
        if id_dip not in piano:
            risultati_fairness[id_dip] = 0
            continue

        piano_dip = piano[id_dip]
        num_giorni = min(31, len(piano_dip))
        penalty = 0.0

        turni_da_evitare = pref.get("turni_da_evitare", [])
        if turni_da_evitare:
            for item in turni_da_evitare:
                parsed = parse_preference_item(item)
                t_norm = normalize_shift(parsed["val"])
                peso_val = get_peso_valore(parsed["peso"])

                for d in range(num_giorni):
                    assigned = piano_dip[d]
                    is_match = False
                    if t_norm == "WEEKEND":
                        is_match = days_info[d]["is_weekend"] and assigned != "R"
                    elif t_norm == "FESTIVO":
                        is_match = days_info[d]["is_holiday"] and assigned != "R"
                    else:
                        is_match = (assigned == t_norm)

                    if is_match:
                        penalty += peso_val

        turni_desiderati = pref.get("turni_desiderati", [])
        if turni_desiderati:
            for item in turni_desiderati:
                parsed = parse_preference_item(item)
                t_norm = normalize_shift(parsed["val"])
                peso_val = get_peso_valore(parsed["peso"])

                for d in range(num_giorni):
                    assigned = piano_dip[d]
                    is_match = False
                    if t_norm == "WEEKEND":
                        is_match = days_info[d]["is_weekend"] and assigned != "R"
                    elif t_norm == "FESTIVO":
                        is_match = days_info[d]["is_holiday"] and assigned != "R"
                    else:
                        is_match = (assigned == t_norm)

                    if is_match:
                        penalty -= peso_val // 2


        richieste_specifiche = pref.get("richieste_specifiche", [])
        if richieste_specifiche:
            for req in richieste_specifiche:
                if not isinstance(req, dict):
                    continue
                data_str = req.get("data")
                if not data_str:
                    continue
                try:
                    req_date = datetime.date.fromisoformat(data_str)
                    d = (req_date - start_date).days
                except Exception:
                    continue

                if 0 <= d < num_giorni:
                    assigned = piano_dip[d]
                    turni_req = req.get("turno", [])
                    if isinstance(turni_req, str):
                        turni_req = [turni_req]
                    turni_req_norm = [normalize_shift(t) for t in turni_req]
                    desiderato = req.get("desiderato", True)
                    peso_str = req.get("peso", "MODERATA")
                    peso_val = get_peso_valore(peso_str)

                    has_tutti = any(t == "TUTTI" for t in turni_req_norm)

                    if desiderato:
                        is_match = (assigned != "R") if has_tutti else (assigned in turni_req_norm)
                        if is_match:
                            penalty -= peso_val // 2
                        else:
                            penalty += peso_val
                    else:
                        is_match = (assigned != "R") if has_tutti else (assigned in turni_req_norm)
                        if is_match:
                            penalty += peso_val

        giorni_settimana_sgraditi = pref.get("giorni_settimana_sgraditi", [])
        if giorni_settimana_sgraditi:
            for item in giorni_settimana_sgraditi:
                parsed = parse_preference_item(item)
                g_norm = str(parsed["val"]).lower() if parsed["val"] else ""
                peso_val = get_peso_valore(parsed["peso"])

                for d in range(num_giorni):
                    assigned = piano_dip[d]
                    if assigned != "R" and days_info[d]["weekday"] == g_norm:
                        penalty += peso_val
    
        giorni_settimana_graditi = pref.get("giorni_settimana_graditi", [])
        if giorni_settimana_graditi:
            for item in giorni_settimana_graditi:
                parsed = parse_preference_item(item)
                g_norm = str(parsed["val"]).lower() if parsed["val"] else ""
                peso_val = get_peso_valore(parsed["peso"])

                for d in range(num_giorni):
                    assigned = piano_dip[d]
                    if assigned != "R" and days_info[d]["weekday"] == g_norm:
                        penalty -= peso_val // 2

        giorno_riposo_preferito = pref.get("giorno_riposo_preferito")
        peso_riposo_str = pref.get("peso_riposo", "MODERATA")
        peso_riposo_val = get_peso_valore(peso_riposo_str)

        if giorno_riposo_preferito:
            riposo_pref = str(giorno_riposo_preferito)
            if "." in riposo_pref:
                riposo_pref = riposo_pref.split(".")[-1]
            riposo_pref_norm = riposo_pref.lower()

            is_date = "-" in riposo_pref_norm
            rest_respected = False

            if is_date:
                try:
                    req_date = datetime.date.fromisoformat(riposo_pref_norm)
                    d = (req_date - start_date).days
                    if 0 <= d < num_giorni:
                        if piano_dip[d] == "R":
                            rest_respected = True
                except Exception:
                    pass
            else:
                for d in range(num_giorni):
                    if days_info[d]["weekday"] == riposo_pref_norm and piano_dip[d] == "R":
                        rest_respected = True
                        break

            if not rest_respected:
                penalty += peso_riposo_val
        
        tolleranza_turni_consecutivi = pref.get("tolleranza_turni_consecutivi", [])
        if tolleranza_turni_consecutivi:
            for item in tolleranza_turni_consecutivi:
                parsed = parse_preference_item(item)
                t_norm = normalize_shift(parsed["val"])
                peso_val = get_peso_valore(parsed["peso"])

                for d in range(1, num_giorni):
                    assigned_curr = piano_dip[d]
                    assigned_prev = piano_dip[d-1]

                    if assigned_curr != "R" and assigned_prev != "R":
                        is_match = False
                        if t_norm == "FESTIVO":
                            is_match = days_info[d]["is_holiday"] and days_info[d-1]["is_holiday"]
                        elif t_norm == "WEEKEND":
                            is_match = days_info[d]["is_weekend"] and days_info[d-1]["is_weekend"]
                        else:
                            is_match = (assigned_curr == t_norm and assigned_prev == t_norm)

                        if is_match:
                            penalty += peso_val

        risultati_fairness[id_dip] = round(penalty, 2)

    return risultati_fairness