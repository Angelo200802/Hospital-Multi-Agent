# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []

    # Unifica il piano_assegnamenti in un unico dizionario per facilitare l'accesso
    piano = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                piano.update(item)
    elif isinstance(piano_assegnamenti, dict):
        piano = piano_assegnamenti

    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3  # 0: Mattina (M), 1: Pomeriggio (P), 2: Notte (N)

    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift_val(n, d, s):
        if n not in piano:
            return 0
        turni = piano[n]
        if d >= len(turni):
            return 0
        turno_giorno = turni[d]
        if turno_giorno == "R":
            return 0
        if s == 0 and turno_giorno == "M":
            return 1
        if s == 1 and turno_giorno == "P":
            return 1
        if s == 2 and turno_giorno == "N":
            return 1
        return 0

    # 1. Controllo validità dei caratteri inseriti nel piano
    for n in all_nurses:
        if n in piano:
            for d in range(min(num_days, len(piano[n]))):
                val = piano[n][d]
                if val not in ["M", "P", "N", "R"]:
                    errori.append(
                        f"Infermiere {n} al giorno {d} ha un turno non valido '{val}'. I turni ammessi sono M, P, N, R."
                    )

    # 2. Impedire l'assegnazione consecutiva del turno di Notte e del turno di Mattina del giorno successivo
    for n in all_nurses:
        for d in range(num_days - 1):
            if get_shift_val(n, d, 2) == 1 and get_shift_val(n, d + 1, 0) == 1:
                errori.append(
                    f"Infermiere {n} ha un turno di Notte al giorno {d} seguito da un turno di Mattina al giorno {d+1} (rilevato 'M', ma il vincolo lo vieta)."
                )

    # 3. Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte
    for n in all_nurses:
        for d in range(num_days):
            if get_shift_val(n, d, 2) == 1:
                # Giorno d+1
                if d + 1 < num_days:
                    for s in range(num_shifts):
                        if get_shift_val(n, d + 1, s) == 1:
                            turno_effettivo = (
                                piano[n][d + 1] if d + 1 < len(piano[n]) else ""
                            )
                            errori.append(
                                f"Infermiere {n} ha lavorato al giorno {d+1} (turno '{turno_effettivo}') dopo un turno di Notte al giorno {d} (richiesto riposo nei 2 giorni successivi)."
                            )
                # Giorno d+2
                if d + 2 < num_days:
                    for s in range(num_shifts):
                        if get_shift_val(n, d + 2, s) == 1:
                            turno_effettivo = (
                                piano[n][d + 2] if d + 2 < len(piano[n]) else ""
                            )
                            errori.append(
                                f"Infermiere {n} ha lavorato al giorno {d+2} (turno '{turno_effettivo}') dopo un turno di Notte al giorno {d} (richiesto riposo nei 2 giorni successivi)."
                            )

    # 4. Rispettare il carico di lavoro mensile di esattamente 25 turni equivalenti (Notte vale doppio)
    for n in all_nurses:
        carico = 0
        for d in range(num_days):
            carico += (
                get_shift_val(n, d, 0) * 1
                + get_shift_val(n, d, 1) * 1
                + get_shift_val(n, d, 2) * 2
            )
        if carico != 25:
            errori.append(
                f"Infermiere {n} ha un carico di lavoro mensile di {carico} turni equivalenti, ma il vincolo imponeva esattamente 25."
            )

    # 5. Limitare le ore di lavoro settimanali a un massimo di 36 ore su finestre fisse
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31),
    ]
    for n in all_nurses:
        for idx, week in enumerate(weeks):
            ore = 0
            for d in week:
                ore += (
                    get_shift_val(n, d, 0) * 6
                    + get_shift_val(n, d, 1) * 6
                    + get_shift_val(n, d, 2) * 12
                )
            if ore > 36:
                errori.append(
                    f"Infermiere {n} supera il limite di ore settimanali nella settimana {idx+1} (giorni {week.start}-{week.stop-1}): rilevate {ore} ore, limite massimo 36."
                )

    # 6. Assicurare almeno un giorno di riposo assoluto nel mese per ciascun dipendente
    for n in all_nurses:
        tot_turni = sum(
            get_shift_val(n, d, s)
            for d in range(num_days)
            for s in range(num_shifts)
        )
        if tot_turni > 30:
            errori.append(
                f"Infermiere {n} non ha alcun giorno di riposo assoluto nel mese: assegnati {tot_turni} turni attivi su 31 giorni (massimo consentito 30)."
            )

    # 7. Garantire la copertura minima giornaliera per turno in base alla tipologia di personale
    shift_names = {0: "Mattina (M)", 1: "Pomeriggio (P)", 2: "Notte (N)"}
    if len(spec_nurses) == 0:
        # Caso A: Lavoratori Omogenei
        for d in range(num_days):
            for s in range(num_shifts):
                copertura = sum(get_shift_val(n, d, s) for n in std_nurses)
                if copertura < 2:
                    errori.append(
                        f"Giorno {d}, turno {shift_names[s]}: copertura insufficiente di infermieri standard. Rilevati {copertura}, richiesti almeno 2."
                    )
    else:
        # Caso B: Lavoratori Misti
        for d in range(num_days):
            for s in range(num_shifts):
                copertura_tot = sum(get_shift_val(n, d, s) for n in all_nurses)
                copertura_spec = sum(
                    get_shift_val(n, d, s) for n in spec_nurses
                )
                if copertura_tot < 3:
                    errori.append(
                        f"Giorno {d}, turno {shift_names[s]}: copertura totale insufficiente. Rilevati {copertura_tot}, richiesti almeno 3."
                    )
                if copertura_spec < 1:
                    errori.append(
                        f"Giorno {d}, turno {shift_names[s]}: copertura di infermieri specializzati insufficiente. Rilevati {copertura_spec}, richiesto almeno 1."
                    )

    return errori