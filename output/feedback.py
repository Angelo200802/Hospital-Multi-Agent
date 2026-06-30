# File generato automaticamente dallo Stage 1 (Workers Agent)
# Contieneil codice per l'estrazione di feedback da un modello OR-Tools

def estrai_feedback_errori_hard(piano_assegnamenti, std_nurses, spec_nurses):
    errori = []
    
    # Normalizzazione del piano di assegnamenti (gestisce dizionari o liste di coppie/dizionari)
    piano = {}
    if isinstance(piano_assegnamenti, list):
        for item in piano_assegnamenti:
            if isinstance(item, dict):
                piano.update(item)
            elif isinstance(item, tuple) and len(item) == 2:
                piano[item[0]] = item[1]
    elif isinstance(piano_assegnamenti, dict):
        piano = piano_assegnamenti

    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3
    shift_names = {0: 'Mattina', 1: 'Pomeriggio', 2: 'Notte'}

    # Funzione di utilità per mappare i caratteri testuali ai valori del CSP
    def get_shift_val(p, n, d, s):
        if n not in p:
            return 0
        lista_turni = p[n]
        if d >= len(lista_turni):
            return 0
        val = lista_turni[d]
        if val == 'M' and s == 0:
            return 1
        elif val == 'P' and s == 1:
            return 1
        elif val == 'N' and s == 2:
            return 1
        return 0

    # =========================================================================
    # 2. VINCOLO: MASSIMO UN TURNO GIORNALIERO
    # =========================================================================
    for n in all_nurses:
        for d in range(num_days):
            somma_turni = sum(get_shift_val(piano, n, d, s) for s in range(num_shifts))
            if somma_turni > 1:
                errori.append(
                    f"Violazione Massimo Un Turno Giornaliero per l'infermiere {n} il giorno {d}: "
                    f"assegnati {somma_turni} turni contemporaneamente, ma il limite massimo consentito è 1."
                )

    # =========================================================================
    # 3. VINCOLO: NESSUN TURNO CONSECUTIVO (NOTTE -> MATTINA)
    # =========================================================================
    for n in all_nurses:
        for d in range(num_days - 1):
            if get_shift_val(piano, n, d, 2) == 1:
                if get_shift_val(piano, n, d + 1, 0) == 1:
                    errori.append(
                        f"Violazione Turno Consecutivo (Notte -> Mattina) per l'infermiere {n}: "
                        f"ha lavorato nel turno di Notte il giorno {d} e nel turno di Mattina il giorno {d+1}."
                    )

    # =========================================================================
    # 4. VINCOLO: RIPOSO POST-NOTTE (2 GIORNI INTERI DI RIPOSO)
    # =========================================================================
    for n in all_nurses:
        for d in range(num_days):
            if get_shift_val(piano, n, d, 2) == 1:
                # Controllo giorno d+1
                if d + 1 < num_days:
                    somma_d1 = sum(get_shift_val(piano, n, d + 1, s) for s in range(num_shifts))
                    if somma_d1 != 0:
                        errori.append(
                            f"Violazione Riposo Post-Notte per l'infermiere {n}: ha lavorato di Notte il giorno {d}, "
                            f"ma il giorno {d+1} non è a riposo (rilevati {somma_d1} turni assegnati, richiesto 0)."
                        )
                # Controllo giorno d+2
                if d + 2 < num_days:
                    somma_d2 = sum(get_shift_val(piano, n, d + 2, s) for s in range(num_shifts))
                    if somma_d2 != 0:
                        errori.append(
                            f"Violazione Riposo Post-Notte per l'infermiere {n}: ha lavorato di Notte il giorno {d}, "
                            f"ma il giorno {d+2} non è a riposo (rilevati {somma_d2} turni assegnati, richiesto 0)."
                        )

    # =========================================================================
    # 5. VINCOLO: CARICO DI LAVORO MENSILE (ESATTAMENTE 25 TURNI EQUIVALENTI)
    # =========================================================================
    for n in all_nurses:
        carico_mensile = sum(
            get_shift_val(piano, n, d, 0) + get_shift_val(piano, n, d, 1) + 2 * get_shift_val(piano, n, d, 2)
            for d in range(num_days)
        )
        if carico_mensile != 25:
            errori.append(
                f"Violazione Carico Mensile per l'infermiere {n}: carico totale calcolato pari a {carico_mensile} "
                f"turni equivalenti, ma il vincolo impone esattamente 25."
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
        for idx, settimana in enumerate(settimane):
            ore_settimanali = sum(
                6 * get_shift_val(piano, n, d, 0) + 6 * get_shift_val(piano, n, d, 1) + 12 * get_shift_val(piano, n, d, 2)
                for d in settimana
            )
            if ore_settimanali > 36:
                errori.append(
                    f"Violazione Limite Orario Settimanale per l'infermiere {n} nella settimana {idx+1} "
                    f"(giorni {settimana.start}-{settimana.stop-1}): rilevate {ore_settimanali} ore lavorate, "
                    f"ma il limite massimo consentito è 36 ore."
                )

    # =========================================================================
    # 7. VINCOLO: RIPOSO MENSILE MINIMO (ALMENO 1 GIORNO DI RIPOSO ASSOLUTO)
    # =========================================================================
    for n in all_nurses:
        giorni_lavorati = sum(get_shift_val(piano, n, d, s) for d in range(num_days) for s in range(num_shifts))
        if giorni_lavorati > 30:
            errori.append(
                f"Violazione Riposo Mensile Minimo per l'infermiere {n}: ha lavorato {giorni_lavorati} giorni su 31, "
                f"ma deve avere almeno 1 giorno di riposo assoluto (massimo 30 giorni lavorati)."
            )

    # =========================================================================
    # 8. VINCOLO: REQUISITI DI COPERTURA (CASO A VS CASO B)
    # =========================================================================
    specializzati_presenti = len(spec_nurses) > 0

    for d in range(num_days):
        for s in range(num_shifts):
            if not specializzati_presenti:
                # Caso A: Almeno 2 lavoratori omogenei per turno
                somma_std = sum(get_shift_val(piano, n, d, s) for n in std_nurses)
                if somma_std < 2:
                    errori.append(
                        f"Violazione Copertura Turno (Caso A) il giorno {d} nel turno di {shift_names[s]}: "
                        f"presenti {somma_std} infermieri standard, ma il minimo richiesto è 2."
                    )
            else:
                # Caso B: Almeno 3 lavoratori totali per turno
                somma_tot = sum(get_shift_val(piano, n, d, s) for n in all_nurses)
                if somma_tot < 3:
                    errori.append(
                        f"Violazione Copertura Turno (Caso B - Totale) il giorno {d} nel turno di {shift_names[s]}: "
                        f"presenti {somma_tot} infermieri totali, ma il minimo richiesto è 3."
                    )
                # Caso B: Almeno 1 dei lavoratori deve essere specializzato
                somma_spec = sum(get_shift_val(piano, n, d, s) for n in spec_nurses)
                if somma_spec < 1:
                    errori.append(
                        f"Violazione Copertura Turno (Caso B - Specializzati) il giorno {d} nel turno di {shift_names[s]}: "
                        f"presenti {somma_spec} infermieri specializzati, ma il minimo richiesto è almeno 1."
                    )

    return errori