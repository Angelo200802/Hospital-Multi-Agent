# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    
    # Normalizzazione del piano di assegnamenti in un unico dizionario
    piano = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                piano.update(item)
    elif isinstance(piano_assegnamenti, dict):
        piano = piano_assegnamenti

    all_nurses = std_nurses + spec_nurses
    turno_nomi = {0: "Mattina", 1: "Pomeriggio", 2: "Notte"}

    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift_val(nurse, day, shift_idx):
        if nurse not in piano:
            return 0
        if day >= len(piano[nurse]):
            return 0
        val = piano[nurse][day]
        if val == 'M' and shift_idx == 0:
            return 1
        if val == 'P' and shift_idx == 1:
            return 1
        if val == 'N' and shift_idx == 2:
            return 1
        return 0

    # 1. Controllo turni consecutivi (Notte -> Mattina del giorno dopo)
    for n in all_nurses:
        for d in range(30):
            if get_shift_val(n, d, 2) == 1 and get_shift_val(n, d + 1, 0) == 1:
                errori.append(
                    f"Lavoratore {n}: violato vincolo turno consecutivo. Assegnata Mattina al giorno {d+1} dopo la Notte al giorno {d}."
                )

    # 2. Controllo 2 giorni di riposo consecutivi dopo un turno di Notte
    for n in all_nurses:
        for d in range(31):
            if get_shift_val(n, d, 2) == 1:
                if d + 1 < 31:
                    for s in range(3):
                        if get_shift_val(n, d + 1, s) == 1:
                            errori.append(
                                f"Lavoratore {n}: violato vincolo riposo post-notte. Assegnato turno {turno_nomi[s]} al giorno {d+1} dopo la Notte al giorno {d}."
                            )
                if d + 2 < 31:
                    for s in range(3):
                        if get_shift_val(n, d + 2, s) == 1:
                            errori.append(
                                f"Lavoratore {n}: violato vincolo riposo post-notte. Assegnato turno {turno_nomi[s]} al giorno {d+2} dopo la Notte al giorno {d}."
                            )

    # 3. Controllo carico di lavoro mensile (esattamente 25 turni equivalenti)
    for n in all_nurses:
        tot_equivalenti = sum(
            get_shift_val(n, d, 0) + get_shift_val(n, d, 1) + 2 * get_shift_val(n, d, 2)
            for d in range(31)
        )
        if tot_equivalenti != 25:
            errori.append(
                f"Lavoratore {n}: violato carico di lavoro mensile. Turni equivalenti assegnati: {tot_equivalenti} (richiesti: 25)."
            )

    # 4. Controllo limite ore settimanali (massimo 36 ore)
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31)
    ]
    for n in all_nurses:
        for idx, w in enumerate(weeks):
            ore_settimanali = sum(
                6 * get_shift_val(n, d, 0) + 6 * get_shift_val(n, d, 1) + 12 * get_shift_val(n, d, 2)
                for d in w
            )
            if ore_settimanali > 36:
                errori.append(
                    f"Lavoratore {n}: superate ore settimanali nella settimana {idx+1} (giorni {w[0]}-{w[-1]}). Ore assegnate: {ore_settimanali} (massimo consentito: 36)."
                )

    # 5. Controllo almeno un giorno di riposo assoluto nel mese
    for n in all_nurses:
        giorni_lavorati = sum(
            1 for d in range(31) if any(get_shift_val(n, d, s) == 1 for s in range(3))
        )
        if giorni_lavorati > 30:
            errori.append(
                f"Lavoratore {n}: violato riposo minimo mensile. Giorni lavorati: {giorni_lavorati} su 31 (richiesto almeno 1 giorno di riposo assoluto)."
            )

    # 6. Controllo requisiti di copertura del personale
    if len(spec_nurses) == 0:
        # Caso A: Lavoratori Omogenei (almeno 2 standard per turno)
        for d in range(31):
            for s in range(3):
                copertura = sum(get_shift_val(n, d, s) for n in std_nurses)
                if copertura < 2:
                    errori.append(
                        f"Giorno {d}, Turno {turno_nomi[s]}: copertura insufficiente. Lavoratori standard assegnati: {copertura} (richiesti: 2)."
                    )
    else:
        # Caso B: Lavoratori Misti (almeno 3 totali di cui almeno 1 specializzato)
        for d in range(31):
            for s in range(3):
                tot_copertura = sum(get_shift_val(n, d, s) for n in all_nurses)
                spec_copertura = sum(get_shift_val(n, d, s) for n in spec_nurses)
                if tot_copertura < 3:
                    errori.append(
                        f"Giorno {d}, Turno {turno_nomi[s]}: copertura totale insufficiente. Assegnati: {tot_copertura} (richiesti: 3)."
                    )
                if spec_copertura < 1:
                    errori.append(
                        f"Giorno {d}, Turno {turno_nomi[s]}: copertura specializzata insufficiente. Assegnati: {spec_copertura} (richiesti: 1)."
                    )

    return errori