# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    """
    Crea e applica i vincoli hard per la pianificazione dei turni ospedalieri.
    
    Parametri:
    - model: Oggetto cp_model.CpModel di OR-Tools.
    - shifts: Dizionario vuoto da popolare con le variabili decisionali.
    - std_nurses: Lista di stringhe con gli ID dei dipendenti Standard.
    - spec_nurses: Lista di stringhe con gli ID dei dipendenti Specializzati.
    
    Ritorna:
    - model: Il modello OR-Tools con i vincoli applicati.
    - shifts: Il dizionario delle variabili decisionali popolate.
    """
    
    # Uniamo tutti i lavoratori in un'unica lista per iterazioni globali
    all_nurses = std_nurses + spec_nurses
    num_days = 31  # Dal 7 Dicembre al 6 Gennaio compresi
    num_shifts = 3 # 0 = Mattina, 1 = Pomeriggio, 2 = Notte

    # CoT:
    # 1. Obiettivo: Creare le variabili decisionali booleane per ciascun infermiere, giorno e turno.
    # 2. Variabili: shifts[(n, d, s)] dove n è l'ID dell'infermiere, d è il giorno (0-30), s è il turno (0-2).
    # 3. Implementazione: Usiamo model.NewBoolVar per definire ogni variabile decisionale nel dizionario shifts.
    for n in all_nurses:
        for d in range(num_days):
            for s in range(num_shifts):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # CoT:
    # 1. Obiettivo: Garantire che ciascun dipendente copra al massimo un turno al giorno.
    # 2. Variabili: shifts[(n, d, s)] per un dato infermiere 'n' e giorno 'd' su tutti i turni 's'.
    # 3. Implementazione: Per ogni infermiere 'n' e giorno 'd', la somma delle variabili su s (0, 1, 2) deve essere <= 1.
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(num_shifts)) <= 1)

    # CoT:
    # 1. Obiettivo: Garantire i requisiti di copertura giornaliera per ogni turno.
    #    - Caso A (Lavoratori Omogenei): Se non ci sono specializzati, ogni turno deve avere almeno 2 lavoratori.
    #    - Caso B (Lavoratori Misti): Se ci sono specializzati, ogni turno deve avere almeno 3 lavoratori totali, di cui almeno 1 specializzato.
    # 2. Variabili: shifts[(n, d, s)] per tutti i lavoratori 'n' in un dato giorno 'd' e turno 's'.
    # 3. Implementazione: Verifichiamo se spec_nurses è vuota. Se sì, applichiamo il Caso A. Altrimenti, applichiamo il Caso B.
    if len(spec_nurses) == 0:
        # Caso A: Almeno 2 lavoratori per turno
        for d in range(num_days):
            for s in range(num_shifts):
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 2)
    else:
        # Caso B: Almeno 3 lavoratori totali e almeno 1 specializzato per turno
        for d in range(num_days):
            for s in range(num_shifts):
                # Almeno 3 lavoratori in totale
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                # Almeno 1 lavoratore specializzato
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    # CoT:
    # 1. Obiettivo: Impedire turni consecutivi a cavallo di due giorni (Notte -> Mattina del giorno dopo).
    # 2. Variabili: shifts[(n, d, 2)] (Notte del giorno d) e shifts[(n, d+1, 0)] (Mattina del giorno d+1).
    # 3. Implementazione: Per ogni infermiere 'n' e giorno 'd' da 0 a 29, se lavora di Notte al giorno d, non può lavorare la Mattina del giorno d+1.
    #    Usiamo model.AddImplication: shifts[(n, d, 2)] => Not(shifts[(n, d+1, 0)]).
    for n in all_nurses:
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not())

    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2).
    # 2. Variabili: shifts[(n, d, 2)] e tutti i turni dei giorni d+1 e d+2 per l'infermiere 'n'.
    # 3. Implementazione: Se l'infermiere lavora di Notte al giorno 'd', non può lavorare in nessun turno al giorno 'd+1' (se d < 30) e al giorno 'd+2' (se d < 29).
    #    Usiamo model.AddImplication per ciascun turno s_next in range(3) nei giorni d+1 e d+2.
    for n in all_nurses:
        for d in range(num_days):
            if d < num_days - 1:
                # Giorno d+1: nessun turno consentito
                for s_next in range(num_shifts):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, s_next)].Not())
            if d < num_days - 2:
                # Giorno d+2: nessun turno consentito
                for s_next in range(num_shifts):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+2, s_next)].Not())

    # CoT:
    # 1. Obiettivo: Ogni lavoratore deve coprire esattamente 25 turni di carico nel mese.
    #    Mattina (s=0) vale 1, Pomeriggio (s=1) vale 1, Notte (s=2) vale 2.
    # 2. Variabili: shifts[(n, d, s)] per un infermiere 'n' su tutti i giorni 'd' e turni 's'.
    # 3. Implementazione: Per ogni infermiere 'n', la somma pesata dei turni deve essere esattamente pari a 25.
    for n in all_nurses:
        model.Add(
            sum(
                shifts[(n, d, 0)] * 1 + 
                shifts[(n, d, 1)] * 1 + 
                shifts[(n, d, 2)] * 2 
                for d in range(num_days)
            ) == 25
        )

    # CoT:
    # 1. Obiettivo: Limitare il tempo di lavoro a massimo 36 ore settimanali complessive su finestre fisse.
    #    Mattina (s=0) = 6 ore, Pomeriggio (s=1) = 6 ore, Notte (s=2) = 12 ore.
    # 2. Variabili: shifts[(n, d, s)] pesati per le ore di ciascun turno.
    # 3. Implementazione: Definiamo le 5 settimane fisse nell'arco dei 31 giorni.
    #    Per ogni settimana e per ogni infermiere 'n', la somma delle ore lavorate deve essere <= 36.
    weeks = [
        range(0, 7),    # Settimana 1: giorni 0-6
        range(7, 14),   # Settimana 2: giorni 7-13
        range(14, 21),  # Settimana 3: giorni 14-20
        range(21, 28),  # Settimana 4: giorni 21-27
        range(28, 31)   # Settimana 5: giorni 28-30 (parziale)
    ]
    
    for n in all_nurses:
        for w in weeks:
            model.Add(
                sum(
                    shifts[(n, d, 0)] * 6 + 
                    shifts[(n, d, 1)] * 6 + 
                    shifts[(n, d, 2)] * 12 
                    for d in w
                ) <= 36
            )

    # CoT:
    # 1. Obiettivo: Garantire a ciascun dipendente almeno un giorno di riposo assoluto (nessun turno) nel mese.
    # 2. Variabili: Creiamo una variabile ausiliaria booleana has_worked_day[(n, d)] che indica se l'infermiere 'n' ha lavorato nel giorno 'd'.
    # 3. Implementazione: Poiché un dipendente fa al massimo un turno al giorno, la somma dei turni in un giorno è 0 o 1.
    #    Definiamo has_worked_day come pari a questa somma. Imponiamo che la somma di has_worked_day su tutti i 31 giorni sia <= 30.
    #    Questo garantisce matematicamente che ci sia almeno un giorno in cui l'infermiere non lavora alcun turno.
    for n in all_nurses:
        has_worked_day = []
        for d in range(num_days):
            worked = model.NewBoolVar(f"worked_{n}_{d}")
            model.Add(worked == sum(shifts[(n, d, s)] for s in range(num_shifts)))
            has_worked_day.append(worked)
        model.Add(sum(has_worked_day) <= 30)

    return model, shifts