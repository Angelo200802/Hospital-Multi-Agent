import datetime

MAPPA_PESI = {
    "LIEVE": 2,
    "MODERATA": 5,
    "ALTA": 8,
    "VITALE": 10,
}

GIORNI_SETTIMANA = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
FESTIVI = {"2026-12-08", "2026-12-25", "2026-12-26", "2027-01-01", "2027-01-06"}
DATA_INIZIO = datetime.date(2026, 12, 7)
NUM_GIORNI = 31
SHIFT_MAP = {"mattina": "M", "pomeriggio": "P", "notte": "N"}


def _info_giorni() -> list[dict]:
    """Precalcola weekday/weekend/festivo per ciascuno dei 31 giorni del piano."""
    info = []
    for d in range(NUM_GIORNI):
        data = DATA_INIZIO + datetime.timedelta(days=d)
        data_str = data.isoformat()
        info.append({
            "weekday": GIORNI_SETTIMANA[data.weekday()],
            "is_weekend": data.weekday() in (5, 6),
            "is_festivo": data_str in FESTIVI,
        })
    return info


def _turno_corrisponde(categoria: str, turno_assegnato: str, giorno_info: dict) -> bool:
    if not categoria or turno_assegnato == "R":
        return False
    if categoria == "weekend":
        return giorno_info["is_weekend"]
    if categoria == "festivo":
        return giorno_info["is_festivo"]
    return SHIFT_MAP.get(categoria) == turno_assegnato


def calcola_fairness(piano: dict, preferenze_dipendenti: list) -> dict:
    if not piano or not preferenze_dipendenti:
        return {}

    giorni_info = _info_giorni()
    risultati = {}

    for pref in preferenze_dipendenti:
        emp_id = pref.get("id_dipendente")
        if not emp_id:
            continue

        turni = piano.get(emp_id)
        if not turni or len(turni) < NUM_GIORNI:
            risultati[emp_id] = 0.0
            continue

        penalita = 0.0

        # Regola 1: turno indesiderato assegnato
        for item in pref.get("turni_da_evitare") or []:
            peso_val = MAPPA_PESI.get(item.get("peso"), MAPPA_PESI["MODERATA"])
            for d in range(NUM_GIORNI):
                if _turno_corrisponde(item.get("turno"), turni[d], giorni_info[d]):
                    penalita += peso_val

        # Regola 2: turno desiderato assegnato (bonus)
        for item in pref.get("turni_desiderati") or []:
            peso_val = MAPPA_PESI.get(item.get("peso"), MAPPA_PESI["MODERATA"])
            for d in range(NUM_GIORNI):
                if _turno_corrisponde(item.get("turno"), turni[d], giorni_info[d]):
                    penalita -= peso_val / 2

        # Regola 3: giorno della settimana sgradito
        for item in pref.get("giorni_settimana_sgraditi") or []:
            peso_val = MAPPA_PESI.get(item.get("peso"), MAPPA_PESI["MODERATA"])
            for d in range(NUM_GIORNI):
                if turni[d] != "R" and giorni_info[d]["weekday"] == item.get("giorno"):
                    penalita += peso_val

        # Regola 4: giorno della settimana gradito (bonus)
        for item in pref.get("giorni_settimana_graditi") or []:
            peso_val = MAPPA_PESI.get(item.get("peso"), MAPPA_PESI["MODERATA"])
            for d in range(NUM_GIORNI):
                if turni[d] != "R" and giorni_info[d]["weekday"] == item.get("giorno"):
                    penalita -= peso_val / 2

        # Regola 5: richiesta specifica su una data
        for req in pref.get("richieste_specifiche") or []:
            data_str = req.get("data")
            if not data_str:
                continue
            try:
                d = (datetime.date.fromisoformat(data_str) - DATA_INIZIO).days
            except ValueError:
                continue
            if not (0 <= d < NUM_GIORNI):
                continue

            assegnato = turni[d]
            desiderato = req.get("desiderato", False)
            peso_val = MAPPA_PESI.get(req.get("peso"), MAPPA_PESI["MODERATA"])
            turni_richiesti = req.get("turno") or []

            match = (assegnato != "R") if "tutti" in turni_richiesti else \
                    any(SHIFT_MAP.get(t) == assegnato for t in turni_richiesti)

            if desiderato:
                penalita += (-peso_val / 2) if match else peso_val
            elif match:
                penalita += peso_val

        # Regola 6: riposo preferito non rispettato
        giorno_riposo = pref.get("giorno_riposo_preferito")
        if giorno_riposo:
            peso_riposo_val = MAPPA_PESI.get(pref.get("peso_riposo"), MAPPA_PESI["MODERATA"])
            rispettato = False
            if "-" in giorno_riposo:  # è una data specifica YYYY-MM-DD
                try:
                    d = (datetime.date.fromisoformat(giorno_riposo) - DATA_INIZIO).days
                    rispettato = 0 <= d < NUM_GIORNI and turni[d] == "R"
                except ValueError:
                    pass
            else:  # è un giorno della settimana ricorrente
                rispettato = any(
                    giorni_info[d]["weekday"] == giorno_riposo and turni[d] == "R"
                    for d in range(NUM_GIORNI)
                )
            if not rispettato:
                penalita += peso_riposo_val
            else:
                penalita -= peso_riposo_val / 2  # bonus se rispettato

        # Regola 7: turni consecutivi dello stesso tipo non tollerati
        for item in pref.get("tolleranza_turni_consecutivi") or []:
            categoria = item.get("categoria_turno")
            peso_val = MAPPA_PESI.get(item.get("peso"), MAPPA_PESI["MODERATA"])
            for d in range(1, NUM_GIORNI):
                if _turno_corrisponde(categoria, turni[d], giorni_info[d]) and \
                   _turno_corrisponde(categoria, turni[d - 1], giorni_info[d - 1]):
                    penalita += peso_val
                else : penalita -= peso_val / 2  

        risultati[emp_id] = round(penalita, 2)

    return risultati