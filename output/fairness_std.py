# # File generato automaticamente dallo Stage 2 (Coding Fairness Agent)

# # Contiene la specifica della funzione di valutazione della fairness


import datetime
import re

# Costante per la conversione dei pesi dichiarati in punteggi numerici di penalità
MAPPA_PESI = {
    "LIEVE": 2,
    "MODERATA": 5,
    "ALTA": 8,
    "VITALE": 10
}

def calcola_fairness(piano, preferenze_dipendenti):
    """
    Calcola il punteggio di insoddisfazione (fairness) per ciascun dipendente
    confrontando i turni assegnati nel piano con le sue preferenze dichiarate.
    
    :param piano: Dizionario {"id_dipendente": ["M", "R", "N", ...]} con 31 turni.
    :param preferenze_dipendenti: Lista di dizionari contenenti le preferenze di ciascun dipendente.
    :return: Dizionario {"id_dipendente": punteggio_insoddisfazione}
    """
    
    # Data di inizio del piano: 7 Dicembre 2026
    START_DATE = datetime.date(2026, 12, 7)
    
    # --- FUNZIONI UTILI DI SUPPORTO (HELPERS) ---
    
    def get_date_of_index(idx):
        """Restituisce l'oggetto date corrispondente all'indice del giorno (0-30)."""
        return START_DATE + datetime.timedelta(days=idx)
        
    def parse_day_of_week(day_str):
        """Converte una stringa giorno della settimana nel corrispondente intero (0=Lunedì, 6=Domenica)."""
        if not day_str:
            return None
        day_str = day_str.lower()
        if "luned" in day_str or "monday" in day_str:
            return 0
        if "marted" in day_str or "tuesday" in day_str:
            return 1
        if "mercoled" in day_str or "wednesday" in day_str:
            return 2
        if "gioved" in day_str or "thursday" in day_str:
            return 3
        if "venerd" in day_str or "friday" in day_str:
            return 4
        if "sabato" in day_str or "saturday" in day_str:
            return 5
        if "domenica" in day_str or "sunday" in day_str:
            return 6
        return None

    def is_festive_date(date_obj):
        """Verifica se una data è un giorno festivo (Domenica o festività nazionale italiana)."""
        if date_obj.weekday() == 6:
            return True
        festive_strs = ["2026-12-08", "2026-12-25", "2026-12-26", "2027-01-01", "2027-01-06"]
        return date_obj.strftime("%Y-%m-%d") in festive_strs

    def match_shift(piano_shift, pref_shift_str, date_obj):
        """Verifica se il turno assegnato nel piano corrisponde alla preferenza espressa."""
        if not pref_shift_str or not piano_shift:
            return False
        
        # Se il turno assegnato è Riposo ("R"), non corrisponde a nessuna richiesta di lavoro attivo
        if piano_shift == "R":
            return False
            
        pref_shift_str = pref_shift_str.lower()
        
        if "mattina" in pref_shift_str and piano_shift == "M":
            return True
        if "pomeriggio" in pref_shift_str and piano_shift == "P":
            return True
        if "notte" in pref_shift_str and piano_shift == "N":
            return True
        if "weekend" in pref_shift_str:
            return date_obj.weekday() in [5, 6]
        if "festivo" in pref_shift_str:
            return is_festive_date(date_obj)
        if pref_shift_str in ["tutti", "all"]:
            return True
        return False

    def get_weight_value(weight_str):
        """Estrae il valore numerico del peso usando la mappa globale MAPPA_PESI."""
        if not weight_str:
            return MAPPA_PESI["MODERATA"]
        weight_str = weight_str.upper()
        for key in MAPPA_PESI:
            if key in weight_str:
                return MAPPA_PESI[key]
        return MAPPA_PESI["MODERATA"]

    def parse_pref_item(item):
        """Estrae il tipo di turno/giorno e il peso associato, gestendo sia dict che stringhe."""
        if isinstance(item, dict):
            return item.get("turno", ""), item.get("peso", "MODERATA")
        elif isinstance(item, str):
            shift = item
            weight = "MODERATA"
            if "Peso" in item:
                match = re.search(r'ImportanzaPreferenza\.([A-Z]+)', item)
                if match:
                    weight = match.group(1)
                shift = item.split(" (")[0]
            return shift, weight
        return "", "MODERATA"

    def parse_day_pref_item(item):
        """Estrae il giorno della settimana e il peso associato, gestendo sia dict che stringhe."""
        if isinstance(item, dict):
            return item.get("giorno", ""), item.get("peso", "MODERATA")
        elif isinstance(item, str):
            day = item
            weight = "MODERATA"
            if "Peso" in item:
                match = re.search(r'ImportanzaPreferenza\.([A-Z]+)', item)
                if match:
                    weight = match.group(1)
                day = item.split(" (")[0]
            return day, weight
        return "", "MODERATA"

    def matches_specific_request(assigned, req_shifts, date_obj):
        """Verifica se il turno assegnato soddisfa una richiesta specifica su data singola."""
        if not assigned or not req_shifts:
            return False
        if isinstance(req_shifts, str):
            req_shifts = [req_shifts]
        for req_s in req_shifts:
            if not isinstance(req_s, str):
                continue
            if req_s.lower() in ["tutti", "all"]:
                if assigned != "R":
                    return True
            elif match_shift(assigned, req_s, date_obj):
                return True
        return False

    # --- CALCOLO DELLA FAIRNESS ---
    
    risultati = {}
    
    for pref_dip in preferenze_dipendenti:
        id_dip = pref_dip.get("id_dipendente")
        if not id_dip:
            continue
            
        # Se il dipendente non è presente nel piano, lo saltiamo difensivamente
        if id_dip not in piano:
            risultati[id_dip] = 0.0
            continue
            
        piano_dip = piano[id_dip]
        penalita = 0.0
        
        # 1. Turno indesiderato assegnato
        # CoT:
        # 1. Verifico la preferenza "turni_da_evitare" del dipendente.
        # 2. Ricavo i dati leggendo la chiave "turni_da_evitare" (lista di dict o stringhe). Per ciascun elemento, estraggo il turno sgradito e il peso associato.
        # 3. Se il dipendente lavora in un giorno d in un turno che corrisponde a quello da evitare, sommo il valore numerico del peso (da MAPPA_PESI) alla penalità per ogni occorrenza.
        for item in pref_dip.get("turni_da_evitare", []):
            shift_str, weight_str = parse_pref_item(item)
            weight_val = get_weight_value(weight_str)
            for d in range(len(piano_dip)):
                assigned = piano_dip[d]
                date_obj = get_date_of_index(d)
                if match_shift(assigned, shift_str, date_obj):
                    penalita += weight_val

        # 2. Turno desiderato NON assegnato (Bonus)
        # CoT:
        # 1. Verifico la preferenza "turni_desiderati" del dipendente.
        # 2. Ricavo i dati leggendo la chiave "turni_desiderati". Per ciascun elemento, estraggo il turno desiderato e il peso associato.
        # 3. Se il dipendente viene assegnato a quel turno desiderato in un giorno d, applico un bonus sottraendo la metà del valore del peso (peso / 2) dalla penalità. Non applico alcuna penalità se il turno non viene assegnato.
        for item in pref_dip.get("turni_desiderati", []):
            shift_str, weight_str = parse_pref_item(item)
            weight_val = get_weight_value(weight_str)
            for d in range(len(piano_dip)):
                assigned = piano_dip[d]
                date_obj = get_date_of_index(d)
                if match_shift(assigned, shift_str, date_obj):
                    penalita -= weight_val / 2.0

        # 3. Richiesta specifica su una data
        # CoT:
        # 1. Verifico la preferenza "richieste_specifiche" del dipendente.
        # 2. Ricavo i dati leggendo la chiave "richieste_specifiche", che contiene una lista di richieste con "data", "turno", "desiderato" e "peso".
        # 3. Converto la data in un indice di giorno (0 per il 7 Dicembre 2026). Se l'indice è valido (tra 0 e 30):
        #    - Se "desiderato" è True e il turno assegnato NON corrisponde a quello richiesto, sommo il peso alla penalità.
        #    - Se "desiderato" è True e il turno assegnato corrisponde, sottraggo la metà del peso (bonus).
        #    - Se "desiderato" è False e il turno assegnato corrisponde a uno di quelli non voluti, sommo il peso alla penalità.
        for req in pref_dip.get("richieste_specifiche", []):
            if not req:
                continue
            data_str = req.get("data")
            if not data_str:
                continue
            try:
                req_date = datetime.datetime.strptime(data_str.strip(), "%Y-%m-%d").date()
                d = (req_date - START_DATE).days
            except Exception:
                continue
            
            if 0 <= d < len(piano_dip):
                assigned = piano_dip[d]
                req_shifts = req.get("turno", [])
                desiderato = req.get("desiderato", False)
                weight_str = req.get("peso", "MODERATA")
                weight_val = get_weight_value(weight_str)
                
                matched = matches_specific_request(assigned, req_shifts, get_date_of_index(d))
                
                if desiderato:
                    if not matched:
                        penalita += weight_val
                    else:
                        penalita -= weight_val / 2.0
                else:
                    if matched:
                        penalita += weight_val

        # 4. Giorno della settimana sgradito
        # CoT:
        # 1. Verifico la preferenza "giorni_settimana_sgraditi" del dipendente.
        # 2. Ricavo i dati leggendo la chiave "giorni_settimana_sgraditi" (lista di dict o stringhe con giorno e peso).
        # 3. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana corrisponde a quello sgradito, sommo il peso alla penalità per ogni occorrenza.
        for item in pref_dip.get("giorni_settimana_sgraditi", []):
            day_str, weight_str = parse_day_pref_item(item)
            target_dow = parse_day_of_week(day_str)
            if target_dow is not None:
                weight_val = get_weight_value(weight_str)
                for d in range(len(piano_dip)):
                    assigned = piano_dip[d]
                    if assigned != "R":
                        date_obj = get_date_of_index(d)
                        if date_obj.weekday() == target_dow:
                            penalita += weight_val

        # 5. Riposo preferito non rispettato
        # CoT:
        # 1. Verifico la preferenza "giorno_riposo_preferito" del dipendente.
        # 2. Ricavo i dati leggendo "giorno_riposo_preferito" e il relativo "peso_riposo".
        # 3. Se il valore è una data specifica (formato YYYY-MM-DD) e il dipendente lavora in quel giorno, sommo il peso alla penalità. Se è un giorno della settimana (es. "domenica") e il dipendente non ha ALMENO un giorno di riposo ("R") in quel giorno della settimana in tutto il mese, sommo il peso alla penalità (una sola volta).
        giorno_riposo = pref_dip.get("giorno_riposo_preferito")
        if giorno_riposo:
            weight_str = pref_dip.get("peso_riposo", "MODERATA")
            weight_val = get_weight_value(weight_str)
            
            if "-" in str(giorno_riposo):
                try:
                    req_date = datetime.datetime.strptime(str(giorno_riposo).strip(), "%Y-%m-%d").date()
                    d = (req_date - START_DATE).days
                    if 0 <= d < len(piano_dip):
                        if piano_dip[d] != "R":
                            penalita += weight_val
                except Exception:
                    pass
            else:
                target_dow = parse_day_of_week(str(giorno_riposo))
                if target_dow is not None:
                    has_riposo = False
                    for d in range(len(piano_dip)):
                        date_obj = get_date_of_index(d)
                        if date_obj.weekday() == target_dow and piano_dip[d] == "R":
                            has_riposo = True
                            break
                    if not has_riposo:
                        penalita += weight_val

        # 6. Turni consecutivi dello stesso tipo non tollerati
        # CoT:
        # 1. Verifico la preferenza "tolleranza_turni_consecutivi" del dipendente.
        # 2. Ricavo i dati leggendo la chiave "tolleranza_turni_consecutivi" (lista di dict o stringhe con il tipo di turno non tollerato consecutivamente e il peso).
        # 3. Per ogni giorno d (da 1 a 30), se sia il giorno d che il giorno d-1 hanno un turno assegnato (diverso da "R") dello stesso tipo "t", sommo il peso alla penalità per ogni occorrenza.
        for item in pref_dip.get("tolleranza_turni_consecutivi", []):
            shift_str, weight_str = parse_pref_item(item)
            weight_val = get_weight_value(weight_str)
            for d in range(1, len(piano_dip)):
                shift_curr = piano_dip[d]
                shift_prev = piano_dip[d-1]
                if shift_curr != "R" and shift_prev != "R":
                    if shift_curr == shift_prev:
                        date_curr = get_date_of_index(d)
                        if match_shift(shift_curr, shift_str, date_curr):
                            penalita += weight_val

        # Bonus: Giorni della settimana graditi
        # CoT:
        # 1. Verifico la preferenza "giorni_settimana_graditi" del dipendente.
        # 2. Ricavo i dati leggendo la chiave "giorni_settimana_graditi" (lista di dict o stringhe con giorno e peso).
        # 3. Se il dipendente lavora (turno != "R") in un giorno d il cui giorno della settimana corrisponde a quello gradito, applico un bonus sottraendo la metà del peso (peso / 2) dalla penalità. Non applico alcuna penalità se non lavora in quel giorno.
        for item in pref_dip.get("giorni_settimana_graditi", []):
            day_str, weight_str = parse_day_pref_item(item)
            target_dow = parse_day_of_week(day_str)
            if target_dow is not None:
                weight_val = get_weight_value(weight_str)
                for d in range(len(piano_dip)):
                    assigned = piano_dip[d]
                    if assigned != "R":
                        date_obj = get_date_of_index(d)
                        if date_obj.weekday() == target_dow:
                            penalita -= weight_val / 2.0

        # Il punteggio di insoddisfazione finale non può essere negativo
        risultati[id_dip] = max(0.0, penalita)
        
    return risultati