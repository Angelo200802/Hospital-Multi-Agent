# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses) -> list[str]:
    errori = []
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    shift_names = {0: 'Mattina (M)', 1: 'Pomeriggio (P)', 2: 'Notte (N)'}

    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift_val(nurse, day, shift_idx):
        if nurse not in piano_assegnamenti:
            return 0
        if day >= len(piano_assegnamenti[nurse]):
            return 0
        val = piano_assegnamenti[nurse][day]
        if val == 'M' and shift_idx == 0:
            return 1
        if val == 'P' and shift_idx == 1:
            return 1
        if val == 'N' and shift_idx == 2:
            return 1
        return 0

    # 1. Copertura minima per ogni turno di ogni giorno
    if len(spec_nurses) == 0:
        # Caso A: almeno 2 lavoratori per turno
        for d in range(num_days):
            for s in range(3):
                tot = sum(get_shift_val(n, d, s) for n in all_nurses)
                if tot < 2:
                    errori.append(f"Giorno {d}, turno {shift_names[s]}: copertura insufficiente. Assegnati {tot} infermieri, richiesti almeno 2.")
    else:
        # Caso B: almeno 3 lavoratori totali e almeno 1 specializzato
        for d in range(num_days):
            for s in range(3):
                tot = sum(get_shift_val(n, d, s) for n in all_nurses)
                if tot < 3:
                    errori.append(f"Giorno {d}, turno {shift_names[s]}: copertura totale insufficiente. Assegnati {tot} infermieri, richiesti almeno 3.")
                tot_spec = sum(get_shift_val(n, d, s) for n in spec_nurses)
                if tot_spec < 1:
                    errori.append(f"Giorno {d}, turno {shift_names[s]}: copertura specializzata insufficiente. Assegnati {tot_spec} specializzati, richiesto almeno 1.")

    # 2. Impedire ad un dipendente di lavorare in più di un turno nello stesso giorno
    for n in all_nurses:
        for d in range(num_days):
            tot = sum(get_shift_val(n, d, s) for s in range(3))
            if tot > 1:
                errori.append(f"Infermiere {n}, giorno {d}: assegnati {tot} turni nello stesso giorno, massimo consentito 1.")

    # 3. Impedire turno di Mattina (s=0) il giorno successivo a un turno di Pomeriggio (s=1)
    for n in all_nurses:
        for d in range(num_days - 1):
            if get_shift_val(n, d, 1) == 1 and get_shift_val(n, d + 1, 0) == 1:
                errori.append(f"Infermiere {n}: violato riposo insufficiente. Assegnato turno Pomeriggio il giorno {d} e Mattina il giorno {d+1}.")

    # 4. Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2)
    for n in all_nurses:
        for d in range(num_days):
            if get_shift_val(n, d, 2) == 1:
                # Giorno successivo (d+1)
                if d + 1 < num_days:
                    for s in range(3):
                        if get_shift_val(n, d + 1, s) == 1:
                            errori.append(f"Infermiere {n}: violato riposo post-notte. Assegnato turno {shift_names[s]} il giorno {d+1} dopo la Notte del giorno {d}.")
                # Secondo giorno successivo (d+2)
                if d + 2 < num_days:
                    for s in range(3):
                        if get_shift_val(n, d + 2, s) == 1:
                            errori.append(f"Infermiere {n}: violato riposo post-notte. Assegnato turno {shift_names[s]} il giorno {d+2} dopo la Notte del giorno {d}.")

    # 5. Rispettare il carico di lavoro mensile di esattamente 25 turni equivalenti
    for n in all_nurses:
        tot_equiv = sum(get_shift_val(n, d, 0) + get_shift_val(n, d, 1) + 2 * get_shift_val(n, d, 2) for d in range(num_days))
        if tot_equiv != 25:
            errori.append(f"Infermiere {n}: carico di lavoro mensile errato. Assegnati {tot_equiv} turni equivalenti, richiesti esattamente 25.")

    # 6. Limitare le ore di lavoro settimanali a un massimo di 36 ore su finestre fisse
    weeks = [
        range(0, 7),    # Settimana 1
        range(7, 14),   # Settimana 2
        range(14, 21),  # Settimana 3
        range(21, 28),  # Settimana 4
        range(28, 31)   # Settimana 5
    ]
    for n in all_nurses:
        for idx, week in enumerate(weeks):
            ore = sum(6 * get_shift_val(n, d, 0) + 6 * get_shift_val(n, d, 1) + 12 * get_shift_val(n, d, 2) for d in week)
            if ore > 36:
                errori.append(f"Infermiere {n}: superate ore settimanali nella settimana {idx+1} (giorni {week[0]}-{week[-1]}). Assegnate {ore} ore, massimo consentito 36.")

    # 7. Garantire almeno un giorno di riposo assoluto nell'arco del mese
    for n in all_nurses:
        tot_giorni_lavorati = sum(get_shift_val(n, d, s) for d in range(num_days) for s in range(3))
        if tot_giorni_lavorati > (num_days - 1):
            errori.append(f"Infermiere {n}: nessun giorno di riposo assoluto nel mese. Lavorati {tot_giorni_lavorati} giorni su {num_days}.")

    return errori