# File generato automaticamente dallo Stage 1 (Workers Agent)
# Contieneil codice per l'estrazione di feedback da un modello OR-Tools

def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    
    # Normalizzazione di piano_assegnamenti in un dizionario standard
    piano_dict = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                piano_dict.update(item)
            elif isinstance(item, tuple) and len(item) == 2:
                piano_dict[item[0]] = item[1]
    elif isinstance(piano_assegnamenti, dict):
        piano_dict = piano_assegnamenti

    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3

    # =========================================================================
    # 2. VINCOLO: MASSIMO UN TURNO GIORNALIERO
    # =========================================================================
    for n in all_nurses:
        if n not in piano_dict:
            continue
        for d in range(num_days):
            somma = sum(piano_dict[n][d][s] for s in range(num_shifts))
            if somma > 1:
                errori.append(
                    f"Violazione Massimo Un Turno Giornaliero: L'infermiere {n} ha lavorato in {somma} turni il giorno {d}. Il limite massimo consentito è 1."
                )

    # =========================================================================
    # 3. VINCOLO: NESSUN TURNO CONSECUTIVO (NOTTE -> MATTINA)
    # =========================================================================
    for n in all_nurses:
        if n not in piano_dict:
            continue
        for d in range(num_days - 1):
            if piano_dict[n][d][2] == 1:  # Notte al giorno d
                if piano_dict[n][d + 1][0] == 1:  # Mattina al giorno d+1
                    errori.append(
                        f"Violazione Turno Consecutivo: L'infermiere {n} ha lavorato nel turno di Mattina il giorno {d + 1} dopo aver lavorato nel turno di Notte il giorno {d}."
                    )

    # =========================================================================
    # 4. VINCOLO: RIPOSO POST-NOTTE (2 GIORNI INTERI DI RIPOSO)
    # =========================================================================
    for n in all_nurses:
        if n not in piano_dict:
            continue
        for d in range(num_days):
            if piano_dict[n][d][2] == 1:  # Notte al giorno d
                if d + 1 < num_days:
                    somma_d1 = sum(piano_dict[n][d + 1][s] for s in range(num_shifts))
                    if somma_d1 != 0:
                        errori.append(
                            f"Violazione Riposo Post-Notte: L'infermiere {n} ha lavorato in {somma_d1} turni il giorno {d + 1} (giorno successivo a un turno di Notte al giorno {d}). Erano richiesti 0 turni."
                        )
                if d + 2 < num_days:
                    somma_d2 = sum(piano_dict[n][d + 2][s] for s in range(num_shifts))
                    if somma_d2 != 0:
                        errori.append(
                            f"Violazione Riposo Post-Notte: L'infermiere {n} ha lavorato in {somma_d2} turni il giorno {d + 2} (secondo giorno successivo a un turno di Notte al giorno {d}). Erano richiesti 0 turni."
                        )

    # =========================================================================
    # 5. VINCOLO: CARICO DI LAVORO MENSILE (ESATTAMENTE 25 TURNI EQUIVALENTI)
    # =========================================================================
    for n in all_nurses:
        if n not in piano_dict:
            continue
        carico_mensile = sum(
            piano_dict[n][d][0] + piano_dict[n][d][1] + 2 * piano_dict[n][d][2]
            for d in range(num_days)
        )
        if carico_mensile != 25:
            errori.append(
                f"Violazione Carico Mensile: L'infermiere {n} ha accumulato un carico di lavoro di {carico_mensile} turni equivalenti nel mese, ma il vincolo impone esattamente 25."
            )

    # =========================================================================
    # 6. VINCOLO: LIMITE ORARIO SETTIMANALE (MASSIMO 36 ORE)
    # =========================================================================
    settimane = [
        range(0, 7),    # Settimana 1: giorni 0-6
        range(7, 14),   # Settimana 2: giorni 7-13
        range(14, 21),  # Settimana 3: giorni 14-20
        range(21, 28),  # Settimana 4: giorni 21-27
        range(28, 31)   # Settimana 5: giorni 28-30
    ]
    for n in all_nurses:
        if n not in piano_dict:
            continue
        for idx, settimana in enumerate(settimane):
            ore_settimanali = sum(
                6 * piano_dict[n][d][0] + 6 * piano_dict[n][d][1] + 12 * piano_dict[n][d][2]
                for d in settimana
            )
            if ore_settimanali > 36:
                giorni_settimana = f"{settimana[0]}-{settimana[-1]}"
                errori.append(
                    f"Violazione Limite Orario Settimanale: L'infermiere {n} ha lavorato {ore_settimanali} ore nella settimana {idx + 1} (giorni {giorni_settimana}), superando il limite massimo di 36 ore."
                )

    # =========================================================================
    # 7. VINCOLO: RIPOSO MENSILE MINIMO (ALMENO 1 GIORNO DI RIPOSO ASSOLUTO)
    # =========================================================================
    for n in all_nurses:
        if n not in piano_dict:
            continue
        giorni_lavorati = sum(piano_dict[n][d][s] for d in range(num_days) for s in range(num_shifts))
        if giorni_lavorati > 30:
            errori.append(
                f"Violazione Riposo Mensile Minimo: L'infermiere {n} ha lavorato per {giorni_lavorati} giorni nel mese. Deve avere almeno 1 giorno di riposo assoluto (massimo 30 giorni lavorati)."
            )

    # =========================================================================
    # 8. VINCOLO: REQUISITI DI COPERTURA (CASO A VS CASO B)
    # =========================================================================
    specializzati_presenti = len(spec_nurses) > 0

    for d in range(num_days):
        for s in range(num_shifts):
            if not specializzati_presenti:
                # Caso A: Almeno 2 lavoratori omogenei per turno
                tot_std = sum(piano_dict[n][d][s] for n in std_nurses if n in piano_dict)
                if tot_std < 2:
                    errori.append(
                        f"Violazione Copertura (Caso A): Il giorno {d}, turno {s} ha una copertura di {tot_std} infermieri standard. Richiesti almeno 2."
                    )
            else:
                # Caso B: Almeno 3 lavoratori totali per turno
                tot_all = sum(piano_dict[n][d][s] for n in all_nurses if n in piano_dict)
                if tot_all < 3:
                    errori.append(
                        f"Violazione Copertura Totale (Caso B): Il giorno {d}, turno {s} ha una copertura totale di {tot_all} infermieri. Richiesti almeno 3."
                    )
                # Caso B: Almeno 1 dei lavoratori deve essere specializzato
                tot_spec = sum(piano_dict[n][d][s] for n in spec_nurses if n in piano_dict)
                if tot_spec < 1:
                    errori.append(
                        f"Violazione Copertura Specializzata (Caso B): Il giorno {d}, turno {s} ha {tot_spec} infermieri specializzati assegnati. Richiesto almeno 1."
                    )

    return errori