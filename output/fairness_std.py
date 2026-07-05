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
    """
    Calcola il punteggio di insoddisfazione (fairness) per ciascun dipendente
    confrontando i turni assegnati nel piano con le sue preferenze.
    
    :param piano: Dizionario {"id_dipendente": ["M", "R", "N", ...]} con 31 turni.
    :param preferenze_dipendenti: Lista di dizionari contenenti le preferenze di ciascun dipendente.
    :return: Dizionario {"id_dipendente": punteggio_totale}
    """
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

        # ==========================================
        # REGOLA 1: Turno indesiderato assegnato
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "turni_da_evitare" del dipendente (lista di turni sgraditi).
        # 2. Ricavo ciascun turno da evitare e il relativo peso associato tramite la chiave "turni_da_evitare".
        # 3. Se il turno assegnato in un giorno d corrisponde al turno sgradito (o se è WEEKEND/FESTIVO
        #    e il dipendente lavora in quel giorno speciale), sommo MAPPA_PESI[peso] alla penalità.
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

        # ==========================================
        # REGOLA 2: Turno desiderato assegnato (Bonus)
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "turni_desiderati" del dipendente.
        # 2. Ricavo ciascun turno desiderato e il relativo peso associato tramite la chiave "turni_desiderati".
        # 3. Se il turno assegnato in un giorno d corrisponde al turno desiderato,
        #    sottraggo la metà del peso (MAPPA_PESI[peso] // 2) come bonus dalla penalità.
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

        # ==========================================
        # REGOLA 3: Richiesta specifica su una data
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "richieste_specifiche" del dipendente.
        # 2. Ricavo la data, la lista di turni coinvolti, il flag "desiderato" e il peso associato.
        # 3. Converto la data nell'indice del giorno d (0 = 7 Dicembre 2026).
        # 4. Se "desiderato" è True: se il turno assegnato corrisponde a uno di quelli richiesti (o se è "tutti"
        #    e il turno non è "R"), applico un bonus (sottraggo MAPPA_PESI[peso] // 2). Altrimenti, applico una penalità (sommo MAPPA_PESI[peso]).
        # 5. Se "desiderato" è False: se il turno assegnato corrisponde a uno di quelli sgraditi (o se è "tutti"
        #    e il turno non è "R"), applico una penalità (sommo MAPPA_PESI[peso]).
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

        # ==========================================
        # REGOLA 4: Giorno della settimana sgradito
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "giorni_settimana_sgraditi" del dipendente.
        # 2. Ricavo il giorno della settimana sgradito e il relativo peso associato.
        # 3. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
        #    corrisponde a quello sgradito, sommo MAPPA_PESI[peso] alla penalità.
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

        # ==========================================
        # REGOLA 4b: Giorno della settimana gradito (Bonus)
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "giorni_settimana_graditi" del dipendente.
        # 2. Ricavo il giorno della settimana gradito e il relativo peso associato.
        # 3. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana
        #    corrisponde a quello gradito, sottraggo MAPPA_PESI[peso] // 2 dalla penalità.
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

        # ==========================================
        # REGOLA 5: Riposo preferito non rispettato
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "giorno_riposo_preferito" e il relativo "peso_riposo".
        # 2. Se è una data specifica (contiene "-"), verifico se in quel giorno esatto il turno assegnato è "R".
        # 3. Se è un giorno della settimana (es. "domenica"), verifico se esiste almeno un giorno di riposo ("R")
        #    in quel giorno della settimana lungo tutto il mese.
        # 4. Se la preferenza non è rispettata, sommo MAPPA_PESI[peso_riposo] alla penalità (una sola volta).
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

        # ==========================================
        # REGOLA 6: Turni consecutivi dello stesso tipo non tollerati
        # ==========================================
        # CoT:
        # 1. Verifico la preferenza "tolleranza_turni_consecutivi" del dipendente.
        # 2. Per ciascun turno non tollerato consecutivamente, confronto il turno del giorno d con il giorno d-1.
        # 3. Se entrambi i giorni sono lavorati (diversi da "R") e coincidono con il tipo sgradito "t"
        #    (o se "t" è "festivo"/"weekend" ed entrambi i giorni consecutivi sono festivi/weekend lavorati),
        #    sommo MAPPA_PESI[peso] alla penalità per ogni occorrenza.
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

        # Memorizzazione del punteggio finale (arrotondato a 2 cifre decimali per pulizia)
        risultati_fairness[id_dip] = round(penalty, 2)

    return risultati_fairness