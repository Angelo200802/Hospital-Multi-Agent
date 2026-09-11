# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    num_days = 31
    all_nurses = std_nurses + spec_nurses
    
    # Appiattimento del piano_assegnamenti in un dizionario per accesso rapido
    assegnamenti_dict = {}
    for item in piano_assegnamenti:
        for k, v in item.items():
            assegnamenti_dict[k] = v
            
    # Funzione di utilità per mappare i turni testuali ai valori del CSP
    def get_shift(n, d, s):
        if n not in assegnamenti_dict:
            return 0
        if d >= len(assegnamenti_dict[n]):
            return 0
        val = assegnamenti_dict[n][d]
        if val == 'M' and s == 0:
            return 1
        elif val == 'P' and s == 1:
            return 1
        elif val == 'N' and s == 2:
            return 1
        return 0

    shift_names = {0: "Mattina (M)", 1: "Pomeriggio (P)", 2: "Notte (N)"}

    # 1. Copertura Minima per ogni turno di ogni giorno
    if len(spec_nurses) == 0:
        # Caso A: Almeno 2 lavoratori per turno
        for d in range(num_days):
            for s in range(3):
                tot = sum(get_shift(n, d, s) for n in all_nurses)
                if tot < 2:
                    errori.append(f"Giorno {d}, Turno {shift_names[s]}: Copertura insufficiente. Assegnati {tot} infermieri, richiesti almeno 2.")
    else:
        # Caso B: Almeno 3 lavoratori totali e almeno 1 specializzato
        for d in range(num_days):
            for s in range(3):
                tot = sum(get_shift(n, d, s) for n in all_nurses)
                spec_tot = sum(get_shift(n, d, s) for n in spec_nurses)
                if tot < 3:
                    errori.append(f"Giorno {d}, Turno {shift_names[s]}: Copertura totale insufficiente. Assegnati {tot} infermieri, richiesti almeno 3.")
                if spec_tot < 1:
                    errori.append(f"Giorno {d}, Turno {shift_names[s]}: Copertura specializzata insufficiente. Assegnati {spec_tot} specializzati, richiesto almeno 1.")

    # 2. Massimo un turno al giorno per dipendente
    for n in all_nurses:
        for d in range(num_days):
            tot_shifts = sum(get_shift(n, d, s) for s in range(3))
            if tot_shifts > 1:
                errori.append(f"Infermiere {n}, Giorno {d}: Sovrapposizione turni. Assegnati {tot_shifts} turni nello stesso giorno, massimo consentito 1.")

    # 3. Impedire turno Mattina (s=0) il giorno successivo a un turno Notte (s=2)
    for n in all_nurses:
        for d in range(num_days - 1):
            if get_shift(n, d, 2) == 1 and get_shift(n, d + 1, 0) == 1:
                errori.append(f"Infermiere {n}: Violazione riposo post-notte. Assegnato turno Mattina il giorno {d+1} immediatamente dopo il turno Notte del giorno {d}.")

    # 4. Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2)
    for n in all_nurses:
        for d in range(num_days):
            if get_shift(n, d, 2) == 1:
                # Controllo giorno d+1
                if d + 1 < num_days:
                    for s in range(3):
                        if get_shift(n, d + 1, s) == 1:
                            errori.append(f"Infermiere {n}: Violazione riposo post-notte. Assegnato turno {shift_names[s]} il giorno {d+1} (richiesto riposo assoluto nei due giorni successivi alla Notte del giorno {d}).")
                # Controllo giorno d+2
                if d + 2 < num_days:
                    for s in range(3):
                        if get_shift(n, d + 2, s) == 1:
                            errori.append(f"Infermiere {n}: Violazione riposo post-notte. Assegnato turno {shift_names[s]} il giorno {d+2} (richiesto riposo assoluto nei due giorni successivi alla Notte del giorno {d}).")

    # 5. Carico di lavoro mensile di esattamente 25 turni equivalenti
    for n in all_nurses:
        tot_equiv = sum(get_shift(n, d, 0) + get_shift(n, d, 1) + 2 * get_shift(n, d, 2) for d in range(num_days))
        if tot_equiv != 25:
            errori.append(f"Infermiere {n}: Carico di lavoro mensile errato. Assegnati {tot_equiv} turni equivalenti, richiesti esattamente 25.")

    # 6. Limite ore di lavoro settimanali a un massimo di 36 ore
    weeks = [
        range(0, 7),    # Settimana 1
        range(7, 14),   # Settimana 2
        range(14, 21),  # Settimana 3
        range(21, 28),  # Settimana 4
        range(28, 31)   # Settimana 5
    ]
    for n in all_nurses:
        for idx, week in enumerate(weeks):
            ore = sum(6 * get_shift(n, d, 0) + 6 * get_shift(n, d, 1) + 12 * get_shift(n, d, 2) for d in week)
            if ore > 36:
                errori.append(f"Infermiere {n}: Ore settimanali superate nella settimana {idx+1} (giorni {week.start}-{week.stop-1}). Assegnate {ore} ore, massimo consentito 36.")

    # 7. Almeno un giorno di riposo assoluto nell'arco del mese (lavorare al massimo 30 giorni su 31)
    for n in all_nurses:
        tot_giorni_lavorati = sum(get_shift(n, d, s) for d in range(num_days) for s in range(3))
        if tot_giorni_lavorati > 30:
            errori.append(f"Infermiere {n}: Mancanza di riposo assoluto. Lavorati {tot_giorni_lavorati} giorni su 31, richiesto almeno 1 giorno di riposo.")

    return errori