# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses) -> list[str]:
    errori = []
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    shift_names = {0: "Mattina (M)", 1: "Pomeriggio (P)", 2: "Notte (N)"}

    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift(n, d, s):
        if n not in piano_assegnamenti or d >= len(piano_assegnamenti[n]):
            return 0
        valore = piano_assegnamenti[n][d]
        if valore == 'M' and s == 0:
            return 1
        if valore == 'P' and s == 1:
            return 1
        if valore == 'N' and s == 2:
            return 1
        return 0

    # 1. Requisiti di copertura minima per turno
    if len(spec_nurses) == 0:
        # Caso A: Almeno 2 lavoratori per turno
        for d in range(num_days):
            for s in range(3):
                tot = sum(get_shift(n, d, s) for n in all_nurses)
                if tot < 2:
                    errori.append(
                        f"Giorno {d+1}: Copertura insufficiente per il turno {shift_names[s]}. "
                        f"Assegnati: {tot}, Minimo richiesto: 2."
                    )
    else:
        # Caso B: Almeno 3 lavoratori totali per turno, con almeno 1 specializzato
        for d in range(num_days):
            for s in range(3):
                tot = sum(get_shift(n, d, s) for n in all_nurses)
                spec_tot = sum(get_shift(n, d, s) for n in spec_nurses)
                if tot < 3:
                    errori.append(
                        f"Giorno {d+1}: Copertura totale insufficiente per il turno {shift_names[s]}. "
                        f"Assegnati: {tot}, Minimo richiesto: 3."
                    )
                if spec_tot < 1:
                    errori.append(
                        f"Giorno {d+1}: Copertura specialistica insufficiente per il turno {shift_names[s]}. "
                        f"Specializzati assegnati: {spec_tot}, Minimo richiesto: 1."
                    )

    # 2. Massimo un turno giornaliero per ciascun dipendente (Verifica di sicurezza)
    for n in all_nurses:
        if n not in piano_assegnamenti:
            continue
        for d in range(num_days):
            tot_giorno = sum(get_shift(n, d, s) for s in range(3))
            if tot_giorno > 1:
                errori.append(
                    f"Infermiere {n}: Più di un turno assegnato il giorno {d+1}. "
                    f"Turni assegnati: {tot_giorno}, Massimo consentito: 1."
                )

    # 3. Impedisce l'assegnazione di turni consecutivi a cavallo di due giorni
    for n in all_nurses:
        if n not in piano_assegnamenti:
            continue
        for d in range(num_days - 1):
            # Pomeriggio (s=1) al giorno d seguito da Mattina (s=0) al giorno d+1
            if get_shift(n, d, 1) + get_shift(n, d + 1, 0) > 1:
                errori.append(
                    f"Infermiere {n}: Violato vincolo turni consecutivi. "
                    f"Assegnato Pomeriggio il giorno {d+1} e Mattina il giorno {d+2}."
                )
            # Notte (s=2) al giorno d seguito da Mattina (s=0) al giorno d+1
            if get_shift(n, d, 2) + get_shift(n, d + 1, 0) > 1:
                errori.append(
                    f"Infermiere {n}: Violato vincolo turni consecutivi. "
                    f"Assegnato Notte il giorno {d+1} e Mattina il giorno {d+2}."
                )

    # 4. Riposo post-notte obbligatorio di 2 giorni consecutivi dopo un turno di Notte
    for n in all_nurses:
        if n not in piano_assegnamenti:
            continue
        for d in range(num_days):
            if get_shift(n, d, 2) == 1:  # Turno di Notte
                if d + 1 < num_days:
                    for s in range(3):
                        if get_shift(n, d + 1, s) == 1:
                            errori.append(
                                f"Infermiere {n}: Violato riposo post-notte. "
                                f"Assegnato turno {shift_names[s]} il giorno {d+2} dopo la Notte del giorno {d+1}."
                            )
                            break
                if d + 2 < num_days:
                    for s in range(3):
                        if get_shift(n, d + 2, s) == 1:
                            errori.append(
                                f"Infermiere {n}: Violato riposo post-notte. "
                                f"Assegnato turno {shift_names[s]} il giorno {d+3} dopo la Notte del giorno {d+1}."
                            )
                            break

    # 5. Carico di lavoro mensile di esattamente 25 turni equivalenti (Notte vale 2)
    for n in all_nurses:
        if n not in piano_assegnamenti:
            continue
        tot_equivalenti = sum(
            get_shift(n, d, 0) + get_shift(n, d, 1) + 2 * get_shift(n, d, 2)
            for d in range(num_days)
        )
        if tot_equivalenti != 25:
            errori.append(
                f"Infermiere {n}: Carico di lavoro mensile errato. "
                f"Turni equivalenti assegnati: {tot_equivalenti}, richiesti: 25."
            )

    # 6. Limite orario settimanale proporzionale
    weeks = [
        range(0, 7),    # Settimana 1 (7 giorni)
        range(7, 14),   # Settimana 2 (7 giorni)
        range(14, 21),  # Settimana 3 (7 giorni)
        range(21, 28),  # Settimana 4 (7 giorni)
        range(28, 31)   # Settimana 5 (3 giorni)
    ]
    for n in all_nurses:
        if n not in piano_assegnamenti:
            continue
        for idx, week in enumerate(weeks):
            giorni = len(week)
            ore_lavorate = sum(
                6 * get_shift(n, d, 0) + 6 * get_shift(n, d, 1) + 12 * get_shift(n, d, 2)
                for d in week
            )
            if 7 * ore_lavorate > 36 * giorni:
                limite_ore = (36 * giorni) / 7
                errori.append(
                    f"Infermiere {n}: Superato limite orario nella settimana {idx+1} (giorni {week.start+1}-{week.stop}). "
                    f"Ore lavorate: {ore_lavorate}, limite proporzionale massimo: {limite_ore:.2f} ore."
                )

    # 7. Garanzia di almeno un giorno di riposo assoluto nell'arco del mese
    for n in all_nurses:
        if n not in piano_assegnamenti:
            continue
        giorni_lavorati = sum(
            get_shift(n, d, s) for d in range(num_days) for s in range(3)
        )
        if giorni_lavorati > (num_days - 1):
            errori.append(
                f"Infermiere {n}: Nessun giorno di riposo assoluto nel mese. "
                f"Giorni lavorati: {giorni_lavorati}, Massimo consentito: {num_days - 1}."
            )

    return errori