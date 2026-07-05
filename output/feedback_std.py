# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    
    # Uniamo tutti i dipendenti in un'unica lista
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    
    # Normalizzazione del piano_assegnamenti in un dizionario unico
    assignments = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                assignments.update(item)
    elif isinstance(piano_assegnamenti, dict):
        assignments = piano_assegnamenti

    # Funzione di utilità per mappare in modo sicuro i turni testuali
    def get_shift(nurse, day):
        sh_list = assignments.get(nurse, [])
        if day < len(sh_list):
            return sh_list[day]
        return 'R'  # Default a Riposo se l'indice è fuori intervallo o mancante

    # 1. Controllo sequenza Notte (s=2) seguita da Mattina (s=0) il giorno successivo
    for n in all_nurses:
        for d in range(num_days - 1):
            if get_shift(n, d) == 'N' and get_shift(n, d + 1) == 'M':
                errori.append(
                    f"Infermiere {n}: Rilevato turno di Notte al giorno {d} seguito da Mattina al giorno {d+1}, violando il riposo minimo."
                )

    # 2. Controllo riposo di 2 giorni consecutivi dopo un turno di Notte (s=2)
    for n in all_nurses:
        # Impediamo i turni di Notte negli ultimi due giorni del mese (giorni 29 e 30)
        if get_shift(n, num_days - 2) == 'N':
            errori.append(
                f"Infermiere {n}: Rilevato turno di Notte al giorno {num_days - 2}, vietato negli ultimi due giorni del mese."
            )
        if get_shift(n, num_days - 1) == 'N':
            errori.append(
                f"Infermiere {n}: Rilevato turno di Notte al giorno {num_days - 1}, vietato negli ultimi due giorni del mese."
            )

        # Controllo riposo nei giorni d+1 e d+2 per i turni di Notte nei giorni precedenti
        for d in range(num_days - 2):
            if get_shift(n, d) == 'N':
                if get_shift(n, d + 1) != 'R':
                    errori.append(
                        f"Infermiere {n}: Mancato riposo al giorno {d+1} dopo il turno di Notte al giorno {d}."
                    )
                if get_shift(n, d + 2) != 'R':
                    errori.append(
                        f"Infermiere {n}: Mancato riposo al giorno {d+2} after il turno di Notte al giorno {d}."
                    )

    # 3. Controllo carico di lavoro mensile (esattamente 25 unità di carico)
    for n in all_nurses:
        workload = 0
        for d in range(num_days):
            val = get_shift(n, d)
            if val in ['M', 'P']:
                workload += 1
            elif val == 'N':
                workload += 2
        if workload != 25:
            errori.append(
                f"Infermiere {n}: Rilevato carico di lavoro di {workload} unità nel mese, ma il vincolo impone esattamente 25."
            )

    # 4. Controllo ore di lavoro settimanali (massimo 36 ore)
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31)
    ]
    for n in all_nurses:
        for w_idx, week in enumerate(weeks):
            hours = 0
            for d in week:
                val = get_shift(n, d)
                if val in ['M', 'P']:
                    hours += 6
                elif val == 'N':
                    hours += 12
            if hours > 36:
                errori.append(
                    f"Infermiere {n}: Rilevate {hours} ore di lavoro nella settimana {w_idx} (giorni {week.start}-{week.stop-1}), superando il limite massimo di 36 ore."
                )

    # 5. Controllo almeno un giorno di riposo assoluto nel mese
    for n in all_nurses:
        worked_days = sum(1 for d in range(num_days) if get_shift(n, d) in ['M', 'P', 'N'])
        if worked_days > 30:
            errori.append(
                f"Infermiere {n}: Rilevati {worked_days} giorni lavorati, violando l'obbligo di almeno 1 giorno di riposo assoluto (max 30 giorni lavorati)."
            )

    # 6. Controllo copertura minima dei turni
    shift_map = {0: 'M', 1: 'P', 2: 'N'}
    if len(spec_nurses) == 0:
        # Caso A: Lavoratori Omogenei (almeno 2 per turno)
        for d in range(num_days):
            for s in range(3):
                shift_char = shift_map[s]
                total_working = sum(1 for n in all_nurses if get_shift(n, d) == shift_char)
                if total_working < 2:
                    errori.append(
                        f"Giorno {d}, Turno {shift_char}: Rilevati {total_working} lavoratori assegnati, ma il minimo richiesto è 2."
                    )
    else:
        # Caso B: Lavoratori Misti (almeno 3 totali, di cui almeno 1 specializzato)
        for d in range(num_days):
            for s in range(3):
                shift_char = shift_map[s]
                total_working = sum(1 for n in all_nurses if get_shift(n, d) == shift_char)
                if total_working < 3:
                    errori.append(
                        f"Giorno {d}, Turno {shift_char}: Rilevati {total_working} lavoratori totali assegnati, ma il minimo richiesto è 3."
                    )
                
                spec_working = sum(1 for n in spec_nurses if get_shift(n, d) == shift_char)
                if spec_working < 1:
                    errori.append(
                        f"Giorno {d}, Turno {shift_char}: Rilevati {spec_working} lavoratori specializzati assegnati, ma il minimo richiesto è 1."
                    )

    return errori