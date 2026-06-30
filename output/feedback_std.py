# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []

    # Appiattiamo il piano_assegnamenti in un unico dizionario per facilitare l'accesso
    piano = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            for k, v in item.items():
                piano[k] = v
    else:
        piano = piano_assegnamenti

    all_nurses = std_nurses + spec_nurses
    num_days = 31
    shift_mapping = {0: 'M', 1: 'P', 2: 'N'}

    # Controllo preliminare di validità dei caratteri inseriti
    for n in all_nurses:
        turni = piano.get(n, [])
        for d in range(min(len(turni), num_days)):
            if turni[d] not in ['M', 'P', 'N', 'R']:
                errori.append(
                    f"Infermiere {n}: Turno non valido '{turni[d]}' al giorno {d}. "
                    f"I valori ammessi sono M, P, N, R."
                )

    # 1. Vincolo: Massimo un turno al giorno per dipendente
    # (Garantito implicitamente dalla struttura a singola lettera per giorno,
    # ma validato tramite il controllo preliminare sopra).

    # 2. Vincolo: Impedire Notte (s=2) seguita da Mattina (s=0) il giorno successivo
    for n in all_nurses:
        turni = piano.get(n, [])
        for d in range(min(len(turni) - 1, num_days - 1)):
            if turni[d] == 'N' and turni[d + 1] == 'M':
                errori.append(
                    f"Infermiere {n}: Rilevato turno di Notte al giorno {d} seguito da Mattina al giorno {d + 1}. "
                    f"Il vincolo impone il divieto della sequenza N -> M."
                )

    # 3. Vincolo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2)
    for n in all_nurses:
        turni = piano.get(n, [])
        for d in range(min(len(turni), num_days)):
            if turni[d] == 'N':
                if d < num_days - 2:
                    if d + 1 < len(turni) and turni[d + 1] != 'R':
                        errori.append(
                            f"Infermiere {n}: Turno di Notte al giorno {d} richiede riposo al giorno {d + 1}. "
                            f"Rilevato invece '{turni[d + 1]}'."
                        )
                    if d + 2 < len(turni) and turni[d + 2] != 'R':
                        errori.append(
                            f"Infermiere {n}: Turno di Notte al giorno {d} richiede riposo al giorno {d + 2}. "
                            f"Rilevato invece '{turni[d + 2]}'."
                        )
                elif d == num_days - 2:
                    if d + 1 < len(turni) and turni[d + 1] != 'R':
                        errori.append(
                            f"Infermiere {n}: Turno di Notte al giorno {d} richiede riposo al giorno {d + 1}. "
                            f"Rilevato invece '{turni[d + 1]}'."
                        )

    # 4. Vincolo: Ciascun lavoratore deve coprire esattamente 25 turni di carico nel mese
    # M = 1, P = 1, N = 2, R = 0
    for n in all_nurses:
        turni = piano.get(n, [])
        carico = 0
        for d in range(min(len(turni), num_days)):
            if turni[d] == 'M':
                carico += 1
            elif turni[d] == 'P':
                carico += 1
            elif turni[d] == 'N':
                carico += 2
        if carico != 25:
            errori.append(
                f"Infermiere {n}: Carico mensile totale calcolato pari a {carico}, "
                f"ma il vincolo impone esattamente 25."
            )

    # 5. Vincolo: Limitare le ore di lavoro settimanali a un massimo di 36 ore
    # M = 6 ore, P = 6 ore, N = 12 ore, R = 0 ore
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31)
    ]
    for n in all_nurses:
        turni = piano.get(n, [])
        for idx_w, week in enumerate(weeks):
            ore_settimana = 0
            for d in week:
                if d < len(turni):
                    if turni[d] == 'M':
                        ore_settimana += 6
                    elif turni[d] == 'P':
                        ore_settimana += 6
                    elif turni[d] == 'N':
                        ore_settimana += 12
            if ore_settimana > 36:
                errori.append(
                    f"Infermiere {n}: Rilevate {ore_settimana} ore di lavoro nella settimana {idx_w + 1} "
                    f"(giorni {week.start}-{week.stop - 1}), superando il limite massimo di 36 ore."
                )

    # 6. Vincolo: Garantire almeno un giorno di riposo assoluto (0 turni lavorati) nell'arco del mese
    for n in all_nurses:
        turni = piano.get(n, [])
        giorni_lavorati = sum(1 for d in range(min(len(turni), num_days)) if turni[d] in ['M', 'P', 'N'])
        if giorni_lavorati > 30:
            errori.append(
                f"Infermiere {n}: Rilevati {giorni_lavorati} giorni lavorati su 31. "
                f"Il vincolo impone almeno 1 giorno di riposo assoluto (massimo 30 giorni lavorati)."
            )

    # 7. Vincolo: Copertura minima dei turni
    if len(spec_nurses) == 0:
        # Caso A: Lavoratori Omogenei (Almeno 2 lavoratori per turno)
        for d in range(num_days):
            for s_idx, s_char in shift_mapping.items():
                count = 0
                for n in std_nurses:
                    turni = piano.get(n, [])
                    if d < len(turni) and turni[d] == s_char:
                        count += 1
                if count < 2:
                    errori.append(
                        f"Giorno {d}, Turno {s_char}: Copertura insufficiente di infermieri standard. "
                        f"Rilevati {count}, ma il vincolo impone un minimo di 2."
                    )
    else:
        # Caso B: Lavoratori Misti (Almeno 3 totali, di cui almeno 1 specializzato)
        for d in range(num_days):
            for s_idx, s_char in shift_mapping.items():
                tot_count = 0
                spec_count = 0
                for n in all_nurses:
                    turni = piano.get(n, [])
                    if d < len(turni) and turni[d] == s_char:
                        tot_count += 1
                        if n in spec_nurses:
                            spec_count += 1
                if tot_count < 3:
                    errori.append(
                        f"Giorno {d}, Turno {s_char}: Copertura totale insufficiente. "
                        f"Rilevati {tot_count} infermieri, ma il vincolo impone un minimo di 3."
                    )
                if spec_count < 1:
                    errori.append(
                        f"Giorno {d}, Turno {s_char}: Mancanza di personale specializzato. "
                        f"Rilevati {spec_count} specializzati, ma il vincolo impone un minimo di 1."
                    )

    return errori