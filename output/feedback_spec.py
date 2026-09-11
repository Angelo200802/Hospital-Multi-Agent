# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la funzione di estrazione feedback dagli errori hard del piano


def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses) -> list[str]:
    errori = []
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    
    # Helper per mappare i turni testuali ai valori numerici del CSP
    def get_shift_val(n, d, s):
        if n not in piano_assegnamenti:
            return 0
        if d >= len(piano_assegnamenti[n]):
            return 0
        val = piano_assegnamenti[n][d]
        if val == 'M' and s == 0: return 1
        if val == 'P' and s == 1: return 1
        if val == 'N' and s == 2: return 1
        return 0

    shift_names = {0: "Mattina (M)", 1: "Pomeriggio (P)", 2: "Notte (N)"}

    # 1. Copertura Minima per ogni turno di ogni giorno
    for d in range(num_days):
        for s in range(3):
            tot_assigned = sum(get_shift_val(n, d, s) for n in all_nurses)
            spec_assigned = sum(get_shift_val(n, d, s) for n in spec_nurses)
            
            if len(spec_nurses) == 0:
                # Caso A: Almeno 2 lavoratori per turno
                if tot_assigned < 2:
                    errori.append(
                        f"Giorno {d+1}: Copertura insufficiente nel turno {shift_names[s]}. "
                        f"Assegnati: {tot_assigned}, richiesti: almeno 2."
                    )
            else:
                # Caso B: Almeno 3 lavoratori totali, di cui almeno 1 specializzato
                if tot_assigned < 3:
                    errori.append(
                        f"Giorno {d+1}: Copertura totale insufficiente nel turno {shift_names[s]}. "
                        f"Assegnati: {tot_assigned}, richiesti: almeno 3."
                    )
                if spec_assigned < 1:
                    errori.append(
                        f"Giorno {d+1}: Mancanza di personale specializzato nel turno {shift_names[s]}. "
                        f"Specializzati assegnati: {spec_assigned}, richiesti: almeno 1."
                    )

    # 2. Massimo un turno al giorno per dipendente
    for n in all_nurses:
        if n in piano_assegnamenti:
            for d in range(min(num_days, len(piano_assegnamenti[n]))):
                val = piano_assegnamenti[n][d]
                if val not in ['M', 'P', 'N', 'R']:
                    errori.append(
                        f"Infermiere {n}, Giorno {d+1}: Turno non valido '{val}'. "
                        f"I valori ammessi sono M, P, N, R."
                    )

    # 3. Riposo post-notte (2 giorni interi di riposo consecutivi dopo un turno di Notte)
    for n in all_nurses:
        for d in range(num_days):
            if get_shift_val(n, d, 2) == 1:  # Turno di Notte al giorno d
                # Controllo giorno d+1
                if d + 1 < num_days:
                    worked_shifts_d1 = [s for s in range(3) if get_shift_val(n, d + 1, s) == 1]
                    if worked_shifts_d1:
                        assigned_shift = piano_assegnamenti[n][d + 1]
                        errori.append(
                            f"Infermiere {n}: Violazione riposo post-notte. Ha lavorato di Notte il giorno {d+1} "
                            f"ed è stato assegnato al turno {assigned_shift} il giorno {d+2} (richiesto riposo)."
                        )
                # Controllo giorno d+2
                if d + 2 < num_days:
                    worked_shifts_d2 = [s for s in range(3) if get_shift_val(n, d + 2, s) == 1]
                    if worked_shifts_d2:
                        assigned_shift = piano_assegnamenti[n][d + 2]
                        errori.append(
                            f"Infermiere {n}: Violazione riposo post-notte. Ha lavorato di Notte il giorno {d+1} "
                            f"ed è stato assegnato al turno {assigned_shift} il giorno {d+3} (richiesto riposo)."
                        )

    # 4. Carico di lavoro mensile (esattamente 25 turni equivalenti: M=1, P=1, N=2)
    for n in all_nurses:
        tot_weight = sum(
            get_shift_val(n, d, 0) + get_shift_val(n, d, 1) + 2 * get_shift_val(n, d, 2)
            for d in range(num_days)
        )
        if tot_weight != 25:
            errori.append(
                f"Infermiere {n}: Carico di lavoro mensile errato. "
                f"Totale turni equivalenti assegnati: {tot_weight}, richiesti: 25."
            )

    # 5. Ore di lavoro settimanali (massimo 36 ore su finestre fisse: M=6h, P=6h, N=12h)
    weeks = [
        range(0, 7),    # Settimana 1
        range(7, 14),   # Settimana 2
        range(14, 21),  # Settimana 3
        range(21, 28),  # Settimana 4
        range(28, 31)   # Settimana 5
    ]
    for n in all_nurses:
        for idx, week in enumerate(weeks):
            hours = sum(
                6 * get_shift_val(n, d, 0) + 6 * get_shift_val(n, d, 1) + 12 * get_shift_val(n, d, 2)
                for d in week
            )
            if hours > 36:
                week_str = f"giorni {week.start+1}-{week.stop}"
                errori.append(
                    f"Infermiere {n}: Superamento ore settimanali nella settimana {idx+1} ({week_str}). "
                    f"Ore lavorate: {hours}, limite consentito: 36."
                )

    # 6. Almeno un giorno di riposo assoluto nell'arco del mese (lavorare in al massimo 30 giorni)
    for n in all_nurses:
        tot_active_days = sum(
            get_shift_val(n, d, s) for d in range(num_days) for s in range(3)
        )
        if tot_active_days > 30:
            errori.append(
                f"Infermiere {n}: Violazione riposo mensile. "
                f"Ha lavorato {tot_active_days} giorni su 31 (richiesto almeno 1 giorno di riposo assoluto)."
            )

    return errori