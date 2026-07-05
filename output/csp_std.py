# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model


def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # Uniamo tutti i dipendenti in un'unica lista per facilitare l'iterazione
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3  # 0: Mattina, 1: Pomeriggio, 2: Notte

    # CoT:
    # 1. Obiettivo: Inizializzare le variabili decisionali booleane per ogni infermiere, giorno e turno.
    # 2. Variabili: shifts[(n, d, s)] per ciascun infermiere, giorno e turno.
    # 3. Funzione: model.NewBoolVar per creare le variabili booleane.
    for n in all_nurses:
        for d in range(num_days):
            for s in range(num_shifts):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # CoT:
    # 1. Obiettivo: Limitare l'assegnazione a massimo un turno al giorno per ciascun dipendente.
    # 2. Variabili: Somma dei turni s in {0, 1, 2} per ciascun dipendente n e giorno d.
    # 3. Funzione: model.Add con operatore <= 1.
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(num_shifts)) <= 1)

    # CoT:
    # 1. Obiettivo: Impedire l'assegnazione consecutiva del turno di Notte e del turno di Mattina del giorno successivo.
    # 2. Variabili: shifts[(n, d, 2)] e shifts[(n, d+1, 0)] per d da 0 a 29.
    # 3. Funzione: model.AddImplication per vincolare la transizione.
    for n in all_nurses:
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, 0)].Not())

    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte.
    # 2. Variabili: shifts[(n, d, 2)] e tutti i turni dei giorni d+1 e d+2 se rientrano nell'orizzonte temporale.
    # 3. Funzione: model.AddImplication applicata condizionatamente per evitare errori di indice.
    for n in all_nurses:
        for d in range(num_days):
            if d + 1 < num_days:
                for s in range(num_shifts):
                    model.AddImplication(
                        shifts[(n, d, 2)], shifts[(n, d + 1, s)].Not()
                    )
            if d + 2 < num_days:
                for s in range(num_shifts):
                    model.AddImplication(
                        shifts[(n, d, 2)], shifts[(n, d + 2, s)].Not()
                    )

    # CoT:
    # 1. Obiettivo: Rispettare il carico di lavoro mensile di esattamente 25 turni equivalenti (Notte vale doppio).
    # 2. Variabili: shifts[(n, d, s)] pesati per il rispettivo valore di carico (1 per Mattina/Pomeriggio, 2 per Notte).
    # 3. Funzione: model.Add con operatore == 25.
    for n in all_nurses:
        model.Add(
            sum(
                shifts[(n, d, 0)] * 1
                + shifts[(n, d, 1)] * 1
                + shifts[(n, d, 2)] * 2
                for d in range(num_days)
            )
            == 25
        )

    # CoT:
    # 1. Obiettivo: Limitare le ore di lavoro settimanali a un massimo di 36 ore su finestre fisse.
    # 2. Variabili: shifts[(n, d, s)] moltiplicati per le ore di durata (6 per Mattina/Pomeriggio, 12 per Notte) su base settimanale.
    # 3. Funzione: model.Add con operatore <= 36 per ciascuna settimana definita.
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31),
    ]
    for n in all_nurses:
        for week in weeks:
            model.Add(
                sum(
                    shifts[(n, d, 0)] * 6
                    + shifts[(n, d, 1)] * 6
                    + shifts[(n, d, 2)] * 12
                    for d in week
                )
                <= 36
            )

    # CoT:
    # 1. Obiettivo: Assicurare almeno un giorno di riposo assoluto nel mese per ciascun dipendente.
    # 2. Variabili: Somma totale di tutti i turni assegnati nel mese per ciascun dipendente.
    # 3. Funzione: model.Add con operatore <= 30 (su 31 giorni totali).
    for n in all_nurses:
        model.Add(
            sum(
                shifts[(n, d, s)]
                for d in range(num_days)
                for s in range(num_shifts)
            )
            <= 30
        )

    # CoT:
    # 1. Obiettivo: Garantire la copertura minima giornaliera per turno in base alla tipologia di personale.
    # 2. Variabili: shifts[(n, d, s)] per tutti i dipendenti attivi nel turno.
    # 3. Funzione: model.Add con operatore >= target (2 per Caso A, 3 totali e 1 specializzato per Caso B).
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