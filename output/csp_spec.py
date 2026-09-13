# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # Unione di tutti i lavoratori per iterare facilmente
    all_nurses = std_nurses + spec_nurses
    num_days = 31  # Dal 7 Dicembre al 6 Gennaio compresi

    # CoT:
    # Inizializzazione delle variabili decisionali booleane per ogni infermiere, giorno e turno.
    for n in all_nurses:
        for d in range(num_days):
            for s in range(3):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # CoT:
    # Definizione dei requisiti di copertura minima per turno in base alla presenza di personale specializzato (Caso A o Caso B).
    if len(spec_nurses) == 0:
        # Caso A: Almeno 2 lavoratori per turno.
        for d in range(num_days):
            for s in range(3):
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 2)
    else:
        # Caso B: Almeno 3 lavoratori totali per turno, con almeno 1 specializzato.
        for d in range(num_days):
            for s in range(3):
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    # CoT:
    # Limite di massimo un turno giornaliero per ciascun dipendente.
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(3)) <= 1)

    # CoT:
    # Impedisce l'assegnazione di turni consecutivi a cavallo di due giorni (es. Pomeriggio -> Mattina, Notte -> Mattina).
    for n in all_nurses:
        for d in range(num_days - 1):
            # Pomeriggio (s=1) al giorno d seguito da Mattina (s=0) al giorno d+1
            model.Add(shifts[(n, d, 1)] + shifts[(n, d + 1, 0)] <= 1)
            # Notte (s=2) al giorno d seguito da Mattina (s=0) al giorno d+1
            model.Add(shifts[(n, d, 2)] + shifts[(n, d + 1, 0)] <= 1)

    # CoT:
    # Riposo post-notte obbligatorio di 2 giorni consecutivi dopo un turno di Notte (s=2).
    for n in all_nurses:
        for d in range(num_days):
            if d + 1 < num_days:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, s)].Not())
            if d + 2 < num_days:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 2, s)].Not())

    # CoT:
    # Rispettare il carico di lavoro mensile di esattamente 25 turni equivalenti (Notte vale 2).
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] for d in range(num_days)) == 25
        )

    # CoT:
    # Limite orario settimanale proporzionale alla durata effettiva di ciascuna finestra temporale fissa.
    weeks = [
        range(0, 7),    # Settimana 1 (7 giorni)
        range(7, 14),   # Settimana 2 (7 giorni)
        range(14, 21),  # Settimana 3 (7 giorni)
        range(21, 28),  # Settimana 4 (7 giorni)
        range(28, 31)   # Settimana 5 (3 giorni)
    ]
    for n in all_nurses:
        for week in weeks:
            giorni = len(week)
            ore_lavorate = sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] for d in week)
            # Applichiamo la proporzione lineare: 7 * ore_lavorate <= 36 * giorni_settimana
            model.Add(7 * ore_lavorate <= 36 * giorni)

    # CoT:
    # Garanzia di almeno un giorno di riposo assoluto nell'arco del mese.
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, s)] for d in range(num_days) for s in range(3)) <= (num_days - 1)
        )

    return model, shifts