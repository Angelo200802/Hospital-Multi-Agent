# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # Unione di tutti i lavoratori per iterare facilmente
    all_nurses = std_nurses + spec_nurses
    num_days = 31  # Dal 7 Dicembre al 6 Gennaio compresi

    # CoT:
    # 1. Obiettivo: Creare le variabili decisionali booleane per ciascun infermiere, giorno e turno.
    # 2. Variabili: shifts[(n, d, s)] dove n è l'ID dell'infermiere, d è il giorno (0-30), s è il turno (0=Mattina, 1=Pomeriggio, 2=Notte).
    # 3. Funzione OR-Tools: model.NewBoolVar per ogni combinazione.
    for n in all_nurses:
        for d in range(num_days):
            for s in range(3):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # CoT:
    # 1. Obiettivo: Garantire la copertura minima per ogni turno di ogni giorno.
    #    - Caso A (Lavoratori Omogenei, se spec_nurses è vuoto): almeno 2 lavoratori per turno.
    #    - Caso B (Lavoratori Misti, se spec_nurses non è vuoto): almeno 3 lavoratori totali per turno, di cui almeno 1 specializzato.
    # 2. Variabili: shifts[(n, d, s)] per tutti i dipendenti e per i soli specializzati.
    # 3. Funzione OR-Tools: model.Add(sum(...) >= valore) per ogni giorno d e turno s.
    if len(spec_nurses) == 0:
        # Caso A
        for d in range(num_days):
            for s in range(3):
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 2)
    else:
        # Caso B
        for d in range(num_days):
            for s in range(3):
                # Almeno 3 lavoratori in totale
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                # Almeno 1 lavoratore specializzato
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    # CoT:
    # 1. Obiettivo: Impedire ad un dipendente di lavorare in più di un turno nello stesso giorno.
    # 2. Variabili: shifts[(n, d, s)] per un dipendente n e giorno d, su tutti i turni s (0, 1, 2).
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, s)] per s in range(3)) <= 1).
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(3)) <= 1)

    # CoT:
    # 1. Obiettivo: Impedire il turno di Mattina (s=0) il giorno successivo a un turno di Notte (s=2).
    # 2. Variabili: shifts[(n, d, 2)] e shifts[(n, d+1, 0)] per ogni dipendente n e giorno d da 0 a 29.
    # 3. Funzione OR-Tools: model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not()).
    for n in all_nurses:
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, 0)].Not())

    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2).
    #    Quindi, se lavora di Notte il giorno d, non può lavorare in nessun turno nei giorni d+1 e d+2.
    # 2. Variabili: shifts[(n, d, 2)] e shifts[(n, d+k, s)] per k in [1, 2] e s in [0, 1, 2].
    # 3. Funzione OR-Tools: model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+k, s)].Not()) per d+k < 31.
    for n in all_nurses:
        for d in range(num_days):
            # Giorno successivo (d+1)
            if d + 1 < num_days:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, s)].Not())
            # Secondo giorno successivo (d+2)
            if d + 2 < num_days:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 2, s)].Not())

    # CoT:
    # 1. Obiettivo: Rispettare il carico di lavoro mensile di esattamente 25 turni equivalenti.
    #    I turni di Mattina (s=0) e Pomeriggio (s=1) valgono 1, il turno di Notte (s=2) vale 2.
    # 2. Variabili: shifts[(n, d, s)] per ogni dipendente n su tutto il mese.
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] per d in range(31)) == 25).
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] for d in range(num_days)) == 25
        )

    # CoT:
    # 1. Obiettivo: Limitare le ore di lavoro settimanali a un massimo di 36 ore su finestre fisse di 7 giorni.
    #    Le ore sono: Mattina (s=0) = 6h, Pomeriggio (s=1) = 6h, Notte (s=2) = 12h.
    #    Le settimane fisse sono: Giorni 0-6, 7-13, 14-20, 21-27, 28-30.
    # 2. Variabili: shifts[(n, d, s)] per ogni dipendente n, raggruppati per settimana.
    # 3. Funzione OR-Tools: model.Add(sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] per d in settimana) <= 36).
    weeks = [
        range(0, 7),    # Settimana 1
        range(7, 14),   # Settimana 2
        range(14, 21),  # Settimana 3
        range(21, 28),  # Settimana 4
        range(28, 31)   # Settimana 5 (giorni rimanenti)
    ]
    for n in all_nurses:
        for week in weeks:
            model.Add(
                sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] for d in week) <= 36
            )

    # CoT:
    # 1. Obiettivo: Garantire almeno un giorno di riposo assoluto (nessun turno) nell'arco del mese.
    #    Dato che un dipendente può fare al massimo 1 turno al giorno, se lavora in totale in al massimo 30 giorni,
    #    avrà necessariamente almeno 1 giorno di riposo assoluto su 31 giorni totali.
    # 2. Variabili: shifts[(n, d, s)] per ogni dipendente n su tutto il mese.
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, s)] per d in range(31) per s in range(3)) <= 30).
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, s)] for d in range(num_days) for s in range(3)) <= (num_days - 1)
        )

    return model, shifts