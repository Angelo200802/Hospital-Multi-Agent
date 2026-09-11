# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3

    # Normalizzazione del piano_assegnamenti in un unico dizionario
    assegnamenti = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                assegnamenti.update(item)
    elif isinstance(piano_assegnamenti, dict):
        assegnamenti = piano_assegnamenti

    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift_val(n, d, s):
        if n not in assegnamenti:
            return 0
        turni = assegnamenti[n]
        if d >= len(turni):
            return 0
        turno = turni[d]
        if turno == 'M' and s == 0:
            return 1
        elif turno == 'P' and s == 1:
            return 1
        elif turno == 'N' and s == 2:
            return 1
        return 0

    shift_names = {0: "Mattina (M)", 1: "Pomeriggio (P)", 2: "Notte (N)"}

    # 1. Vincolo di Copertura Giornaliera per ogni turno
    if len(spec_nurses) == 0:
        # Caso A: Almeno 2 lavoratori per turno
        for d in range(num_days):
            for s in range(num_shifts):
                tot_workers = sum(get_shift_val(n, d, s) for n in all_nurses)
                if tot_workers < 2:
                    errori.append(
                        f"Giorno {d}: Copertura insufficiente nel turno {shift_names[s]}. "
                        f"Assegnati {tot_workers} lavoratori, richiesti almeno 2."
                    )
    else:
        # Caso B: Almeno 3 lavoratori totali e almeno 1 specializzato per turno
        for d in range(num_days):
            for s in range(num_shifts):
                tot_workers = sum(get_shift_val(n, d, s) for n in all_nurses)
                spec_workers = sum(get_shift_val(n, d, s) for n in spec_nurses)
                if tot_workers < 3:
                    errori.append(
                        f"Giorno {d}: Copertura totale insufficiente nel turno {shift_names[s]}. "
                        f"Assegnati {tot_workers} lavoratori, richiesti almeno 3."
                    )
                if spec_workers < 1:
                    errori.append(
                        f"Giorno {d}: Mancanza di personale specializzato nel turno {shift_names[s]}. "
                        f"Assegnati {spec_workers} specializzati, richiesto almeno 1."
                    )

    # 2. Impedire turni consecutivi (Notte -> Mattina del giorno dopo)
    for n in all_nurses:
        for d in range(num_days - 1):
            if get_shift_val(n, d, 2) == 1 and get_shift_val(n, d + 1, 0) == 1:
                errori.append(
                    f"Dipendente {n}: Violazione turno consecutivo vietato. "
                    f"Assegnato turno di Notte al giorno {d} e Mattina al giorno {d+1}."
                )

    # 3. Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte
    for n in all_nurses:
        for d in range(num_days):
            if get_shift_val(n, d, 2) == 1:
                if d + 1 < num_days:
                    worked_d1 = sum(get_shift_val(n, d + 1, s) for s in range(num_shifts))
                    if worked_d1 > 0:
                        errori.append(
                            f"Dipendente {n}: Violazione riposo post-notte. "
                            f"Lavora al giorno {d+1} dopo aver fatto la Notte al giorno {d}."
                        )
                if d + 2 < num_days:
                    worked_d2 = sum(get_shift_val(n, d + 2, s) for s in range(num_shifts))
                    if worked_d2 > 0:
                        errori.append(
                            f"Dipendente {n}: Violazione riposo post-notte. "
                            f"Lavora al giorno {d+2} dopo aver fatto la Notte al giorno {d}."
                        )

    # 4. Esattamente 25 turni di carico nel mese
    for n in all_nurses:
        workload = sum(
            get_shift_val(n, d, 0) * 1 + 
            get_shift_val(n, d, 1) * 1 + 
            get_shift_val(n, d, 2) * 2 
            for d in range(num_days)
        )
        if workload != 25:
            errori.append(
                f"Dipendente {n}: Violazione carico di lavoro mensile. "
                f"Assegnati {workload} punti carico, richiesti esattamente 25."
            )

    # 5. Massimo 36 ore settimanali complessive su finestre fisse
    weeks = [
        range(0, 7),    # Settimana 1: giorni 0-6
        range(7, 14),   # Settimana 2: giorni 7-13
        range(14, 21),  # Settimana 3: giorni 14-20
        range(21, 28),  # Settimana 4: giorni 21-27
        range(28, 31)   # Settimana 5: giorni 28-30
    ]
    for n in all_nurses:
        for w_idx, w_range in enumerate(weeks):
            hours = sum(
                get_shift_val(n, d, 0) * 6 + 
                get_shift_val(n, d, 1) * 6 + 
                get_shift_val(n, d, 2) * 12 
                for d in w_range
            )
            if hours > 36:
                errori.append(
                    f"Dipendente {n}: Violazione ore settimanali nella settimana {w_idx+1} "
                    f"(giorni {w_range.start}-{w_range.stop-1}). Assegnate {hours} ore, limite massimo 36."
                )

    # 6. Almeno un giorno di riposo assoluto nel mese
    for n in all_nurses:
        days_worked = sum(
            1 for d in range(num_days) 
            if sum(get_shift_val(n, d, s) for s in range(num_shifts)) > 0
        )
        if days_worked > 30:
            errori.append(
                f"Dipendente {n}: Violazione riposo assoluto mensile. "
                f"Lavorati {days_worked} giorni su 31, richiesto almeno 1 giorno di riposo."
            )

    return errori