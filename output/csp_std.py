# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # Unione di tutti i lavoratori (Standard + Specializzati)
    all_nurses = std_nurses + spec_nurses
    
    # CoT:
    # 1. Obiettivo: Creare le variabili decisionali booleane per ciascun infermiere, giorno e turno.
    # 2. Variabili e indici: 'n' in all_nurses, 'd' in range(31) (31 giorni dal 7 Dicembre al 6 Gennaio), 's' in range(3) (0=Mattina, 1=Pomeriggio, 2=Notte).
    # 3. Funzione OR-Tools: model.NewBoolVar per creare variabili booleane e salvarle nel dizionario 'shifts' con chiave (n, d, s).
    for n in all_nurses:
        for d in range(31):
            for s in range(3):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")
                
    # CoT:
    # 1. Obiettivo: Garantire la copertura minima per ogni turno di ogni giorno.
    #    - Se ci sono infermieri specializzati (Caso B): almeno 3 infermieri totali per turno, di cui almeno 1 specializzato.
    #    - Se non ci sono infermieri specializzati (Caso A): almeno 2 infermieri totali per turno.
    # 2. Variabili e indici: 'd' in range(31), 's' in range(3), 'n' in all_nurses, 'spec' in spec_nurses.
    # 3. Funzione OR-Tools: model.Add(sum(...) >= 3) e model.Add(sum(...) >= 1) per il Caso B, oppure model.Add(sum(...) >= 2) per il Caso A.
    for d in range(31):
        for s in range(3):
            if len(spec_nurses) > 0:
                # Caso B: Lavoratori Misti
                # Almeno 3 lavoratori in totale per turno
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                # Almeno 1 lavoratore specializzato per turno
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)
            else:
                # Caso A: Lavoratori Omogenei
                # Almeno 2 lavoratori in totale per turno
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 2)

    # CoT:
    # 1. Obiettivo: Impedire ad un dipendente di lavorare in più di un turno nello stesso giorno.
    # 2. Variabili e indici: 'n' in all_nurses, 'd' in range(31), 's' in range(3).
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, s)] for s in range(3)) <= 1).
    for n in all_nurses:
        for d in range(31):
            model.Add(sum(shifts[(n, d, s)] for s in range(3)) <= 1)

    # CoT:
    # 1. Obiettivo: Evitare che un dipendente lavori nel turno di Mattina (s=0) del giorno d+1 dopo aver lavorato nel turno di Notte (s=2) del giorno d.
    # 2. Variabili e indici: 'n' in all_nurses, 'd' in range(30) (fino al penultimo giorno), 's' in {0, 2}.
    # 3. Funzione OR-Tools: model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not()).
    for n in all_nurses:
        for d in range(30):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not())

    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2).
    #    Se un dipendente lavora di Notte il giorno 'd', non può lavorare in nessun turno nei giorni 'd+1' e 'd+2'.
    # 2. Variabili e indici: 'n' in all_nurses, 'd' in range(31), 's' in range(3).
    # 3. Funzione OR-Tools: model.AddImplication per imporre che se shifts[(n, d, 2)] è True, allora tutti i turni dei giorni d+1 (se d+1 < 31) e d+2 (se d+2 < 31) devono essere False.
    for n in all_nurses:
        for d in range(31):
            # Giorno d+1 (smonto)
            if d + 1 < 31:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, s)].Not())
            # Giorno d+2 (recupero)
            if d + 2 < 31:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+2, s)].Not())

    # CoT:
    # 1. Obiettivo: Assicurare che ogni lavoratore copra esattamente 25 turni di carico nel mese.
    #    I turni di Mattina (s=0) e Pomeriggio (s=1) valgono 1, il turno di Notte (s=2) vale 2.
    # 2. Variabili e indici: 'n' in all_nurses, 'd' in range(31), 's' in range(3).
    # 3. Funzione OR-Tools: model.Add(sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] for d in range(31)) == 25).
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] for d in range(31)) == 25
        )

    # CoT:
    # 1. Obiettivo: Limitare il tempo di lavoro settimanale a massimo 36 ore su finestre fisse di 7 giorni.
    #    Mattina (s=0) = 6 ore, Pomeriggio (s=1) = 6 ore, Notte (s=2) = 12 ore.
    # 2. Variabili e indici: 'n' in all_nurses, 'w' (indice settimana), 'd' nei giorni della settimana.
    #    Definiamo 5 settimane fisse: giorni 0-6, 7-13, 14-20, 21-27, 28-30.
    # 3. Funzione OR-Tools: model.Add(sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] for d in week_days) <= 36).
    weeks = [
        range(0, 7),    # Settimana 1: 7 Dic - 13 Dic
        range(7, 14),   # Settimana 2: 14 Dic - 20 Dic
        range(14, 21),  # Settimana 3: 21 Dic - 27 Dic
        range(21, 28),  # Settimana 4: 28 Dic - 3 Gen
        range(28, 31)   # Settimana 5: 4 Gen - 6 Gen (parziale)
    ]
    for n in all_nurses:
        for week_days in weeks:
            model.Add(
                sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] for d in week_days) <= 36
            )

    # CoT:
    # 1. Obiettivo: Garantire ad ogni dipendente almeno un giorno di riposo assoluto (0 turni assegnati) nel mese.
    # 2. Variabili e indici: 'n' in all_nurses, 'd' in range(31), 's' in range(3).
    # 3. Funzione OR-Tools: Poiché un dipendente può fare al massimo 1 turno al giorno, se lavorasse tutti i giorni farebbe 31 turni.
    #    Imponendo che la somma dei turni effettivi lavorati nel mese sia <= 30, garantiamo matematicamente che ci sia almeno un giorno con 0 turni (riposo assoluto).
    #    model.Add(sum(shifts[(n, d, s)] for d in range(31) for s in range(3)) <= 30).
    for n in all_nurses:
        model.Add(sum(shifts[(n, d, s)] for d in range(31) for s in range(3)) <= 30)

    return model, shifts