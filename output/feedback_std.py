# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    
    # Normalizzazione del piano di assegnamenti (gestisce sia dizionari che liste di dizionari)
    piano = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                piano.update(item)
    elif isinstance(piano_assegnamenti, dict):
        piano = piano_assegnamenti
        
    all_nurses = std_nurses + spec_nurses
    
    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift_val(nurse, day, s):
        if nurse not in piano:
            return 0
        lista_turni = piano[nurse]
        if day >= len(lista_turni):
            return 0
        turno = lista_turni[day]
        if turno == 'M' and s == 0:
            return 1
        elif turno == 'P' and s == 1:
            return 1
        elif turno == 'N' and s == 2:
            return 1
        return 0

    # 1. Copertura minima per ogni turno di ogni giorno
    for d in range(31):
        for s in range(3):
            shift_name = {0: "Mattina", 1: "Pomeriggio", 2: "Notte"}[s]
            tot_assigned = sum(get_shift_val(n, d, s) for n in all_nurses)
            
            if len(spec_nurses) > 0:
                # Caso B: Lavoratori Misti
                if tot_assigned < 3:
                    errori.append(f"Giorno {d+1}, turno {shift_name}: violata copertura minima totale. Assegnati {tot_assigned} infermieri (minimo richiesto: 3).")
                spec_assigned = sum(get_shift_val(n, d, s) for n in spec_nurses)
                if spec_assigned < 1:
                    errori.append(f"Giorno {d+1}, turno {shift_name}: violata copertura minima specializzati. Assegnati {spec_assigned} (minimo richiesto: 1).")
            else:
                # Caso A: Lavoratori Omogenei
                if tot_assigned < 2:
                    errori.append(f"Giorno {d+1}, turno {shift_name}: violata copertura minima totale. Assegnati {tot_assigned} infermieri (minimo richiesto: 2).")

    # 2. Massimo un turno al giorno per dipendente
    for n in all_nurses:
        for d in range(31):
            tot_shifts = sum(get_shift_val(n, d, s) for s in range(3))
            if tot_shifts > 1:
                errori.append(f"Dipendente {n}: violato limite turni giornalieri il Giorno {d+1}. Assegnati {tot_shifts} turni (massimo consentito: 1).")

    # 3. No Mattina (s=0) dopo Notte (s=2)
    for n in all_nurses:
        for d in range(30):
            if get_shift_val(n, d, 2) == 1 and get_shift_val(n, d+1, 0) == 1:
                errori.append(f"Dipendente {n}: violato riposo post-notte. Assegnato turno di Mattina il Giorno {d+2} dopo il turno di Notte del Giorno {d+1}.")

    # 4. 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2)
    for n in all_nurses:
        for d in range(31):
            if get_shift_val(n, d, 2) == 1:
                # Giorno d+1 (smonto)
                if d + 1 < 31:
                    for s in range(3):
                        if get_shift_val(n, d+1, s) == 1:
                            shift_name = {0: "Mattina", 1: "Pomeriggio", 2: "Notte"}[s]
                            errori.append(f"Dipendente {n}: violato riposo di 2 giorni post-notte. Assegnato turno di {shift_name} il Giorno {d+2} dopo la Notte del Giorno {d+1}.")
                # Giorno d+2 (recupero)
                if d + 2 < 31:
                    for s in range(3):
                        if get_shift_val(n, d+2, s) == 1:
                            shift_name = {0: "Mattina", 1: "Pomeriggio", 2: "Notte"}[s]
                            errori.append(f"Dipendente {n}: violato riposo di 2 giorni post-notte. Assegnato turno di {shift_name} il Giorno {d+3} dopo la Notte del Giorno {d+1}.")

    # 5. Esattamente 25 turni di carico nel mese
    for n in all_nurses:
        carico = sum(get_shift_val(n, d, 0) + get_shift_val(n, d, 1) + 2 * get_shift_val(n, d, 2) for d in range(31))
        if carico != 25:
            errori.append(f"Dipendente {n}: violato carico mensile. Totale carico assegnato: {carico} (richiesto: 25).")

    # 6. Massimo 36 ore settimanali su finestre fisse
    weeks = [
        range(0, 7),    # Settimana 1
        range(7, 14),   # Settimana 2
        range(14, 21),  # Settimana 3
        range(21, 28),  # Settimana 4
        range(28, 31)   # Settimana 5
    ]
    for n in all_nurses:
        for idx, week_days in enumerate(weeks):
            ore_sett = sum(6 * get_shift_val(n, d, 0) + 6 * get_shift_val(n, d, 1) + 12 * get_shift_val(n, d, 2) for d in week_days)
            if ore_sett > 36:
                errori.append(f"Dipendente {n}: superate ore settimanali nella Settimana {idx+1} (giorni {week_days.start+1}-{week_days.stop}). Ore assegnate: {ore_sett} (massimo consentito: 36).")

    # 7. Almeno un giorno di riposo assoluto nel mese
    for n in all_nurses:
        tot_giorni_lavorati = sum(1 for d in range(31) if any(get_shift_val(n, d, s) == 1 for s in range(3)))
        if tot_giorni_lavorati > 30:
            errori.append(f"Dipendente {n}: violato riposo mensile assoluto. Giorni lavorati: {tot_giorni_lavorati} su 31 (richiesto almeno 1 giorno di riposo assoluto).")

    return errori