# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model


def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # Uniamo tutti i dipendenti in un'unica lista per facilitare l'iterazione
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3  # 0: Mattina, 1: Pomeriggio, 2: Notte

    # CoT:
    # 1. Obiettivo: Creare le variabili decisionali booleane per ciascun infermiere, giorno e turno.
    # 2. Variabili coinvolte: shifts[(n, d, s)] dove n è in all_nurses, d in range(31), s in range(3).
    # 3. Funzione OR-Tools: model.NewBoolVar.
    for n in all_nurses:
        for d in range(num_days):
            for s in range(num_shifts):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # CoT:
    # 1. Obiettivo: Garantire che ciascun dipendente lavori al massimo un turno al giorno.
    # 2. Variabili coinvolte: shifts[(n, d, s)] per un dipendente 'n' e giorno 'd' fissati, al variare di 's' in {0, 1, 2}.
    # 3. Funzione OR-Tools: model.Add(sum(...) <= 1).
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(num_shifts)) <= 1)

    # CoT:
    # 1. Obiettivo: Impedire che un dipendente faccia il turno di Notte (s=2) e il turno di Mattina (s=0) del giorno successivo.
    # 2. Variabili coinvolte: shifts[(n, d, 2)] e shifts[(n, d+1, 0)] per ogni dipendente 'n' e giorno 'd' da 0 a 29.
    # 3. Funzione OR-Tools: model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not()).
    for n in all_nurses:
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, 0)].Not())

    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2).
    #    Se un dipendente lavora di Notte il giorno 'd', non può lavorare in nessun turno nei giorni 'd+1' e 'd+2'.
    # 2. Variabili coinvolte: shifts[(n, d, 2)] e tutti i turni 's' nei giorni 'd+1' e 'd+2'.
    # 3. Funzione OR-Tools: model.AddImplication per ciascun turno dei due giorni successivi.
    #    Per d in range(29): impone che se shifts[(n, d, 2)] è True, allora shifts[(n, d+1, s)] e shifts[(n, d+2, s)] devono essere False per s in {0, 1, 2}.
    #    Per d = 29: impone lo stesso solo per il giorno d+1 (giorno 30), poiché il giorno d+2 non esiste nell'orizzonte temporale.
    for n in all_nurses:
        for d in range(num_days):
            if d < num_days - 2:
                for s in range(num_shifts):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, s)].Not())
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 2, s)].Not())
            elif d == num_days - 2:
                for s in range(num_shifts):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, s)].Not())

    # CoT:
    # 1. Obiettivo: Ciascun lavoratore deve coprire esattamente 25 turni di carico nel mese.
    #    I turni di Mattina (s=0) e Pomeriggio (s=1) valgono 1, il turno di Notte (s=2) vale 2.
    # 2. Variabili coinvolte: shifts[(n, d, s)] per un dipendente 'n' su tutti i giorni 'd' e turni 's'.
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, 0)] * 1 + shifts[(n, d, 1)] * 1 + shifts[(n, d, 2)] * 2) == 25).
    for n in all_nurses:
        model.Add(
            sum(
                shifts[(n, d, 0)] * 1 + shifts[(n, d, 1)] * 1 + shifts[(n, d, 2)] * 2
                for d in range(num_days)
            ) == 25
        )

    # CoT:
    # 1. Obiettivo: Limitare le ore di lavoro settimanali a un massimo di 36 ore per ciascun dipendente.
    #    I turni s=0 e s=1 durano 6 ore, il turno s=2 dura 12 ore.
    #    Le settimane sono definite su finestre fisse di 7 giorni (giorni 0-6, 7-13, 14-20, 21-27, 28-30).
    # 2. Variabili coinvolte: shifts[(n, d, s)] per ciascun dipendente 'n', raggruppati per settimana.
    # 3. Funzione OR-Tools: model.Add(sum(ore_turno * shifts[(n, d, s)]) <= 36) per ogni settimana e dipendente.
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31)
    ]
    for n in all_nurses:
        for week in weeks:
            model.Add(
                sum(
                    shifts[(n, d, 0)] * 6 + shifts[(n, d, 1)] * 6 + shifts[(n, d, 2)] * 12
                    for d in week
                ) <= 36
            )

    # CoT:
    # 1. Obiettivo: Garantire almeno un giorno di riposo assoluto (0 turni lavorati) nell'arco del mese per ciascun dipendente.
    # 2. Variabili e indici coinvolti: shifts[(n, d, s)] per ciascun dipendente 'n' su tutti i giorni 'd' e turni 's'.
    #    Dato che un dipendente può fare al massimo 1 turno al giorno, il numero di giorni lavorati è pari alla somma di tutte le variabili di turno.
    #    Per avere almeno un giorno di riposo su 31 giorni, il numero totale di giorni lavorati deve essere al massimo 30.
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, s)] per d in range(31) per s in range(3)) <= 30).
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, s)] for d in range(num_days) for s in range(num_shifts)) <= 30
        )

    # CoT:
    # 1. Obiettivo: Garantire la copertura minima dei turni in base alla presenza di personale specializzato.
    #    - Caso A (Solo Standard / Omogenei, ovvero spec_nurses è vuota): Almeno 2 lavoratori per turno.
    #    - Caso B (Misti, ovvero spec_nurses non è vuota): Almeno 3 lavoratori in totale per turno, di cui almeno 1 specializzato.
    # 2. Variabili coinvolte: shifts[(n, d, s)] per tutti i dipendenti 'n' (standard e specializzati) per ciascun giorno 'd' e turno 's'.
    # 3. Funzione OR-Tools: model.Add(sum(...) >= target) per ciascun giorno 'd' e turno 's'.
    if len(spec_nurses) == 0:
        # Caso A: Lavoratori Omogenei
        for d in range(num_days):
            for s in range(num_shifts):
                model.Add(sum(shifts[(n, d, s)] for n in std_nurses) >= 2)
    else:
        # Caso B: Lavoratori Misti
        for d in range(num_days):
            for s in range(num_shifts):
                # Almeno 3 lavoratori in totale
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                # Almeno 1 lavoratore specializzato
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    return model, shifts