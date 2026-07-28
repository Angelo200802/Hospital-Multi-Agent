# # File generato automaticamente dallo Stage 1 (Coding Agent)

# # Contiene la specifica OR-Tools)


from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # CoT:
    # 1. Creazione dell'unione di tutti i lavoratori (Standard + Specializzati).
    # 2. Inizializzazione delle variabili decisionali booleane nel dizionario 'shifts'.
    # 3. La chiave del dizionario è la tupla (n, d, s) dove:
    #    - n: ID del lavoratore (stringa)
    #    - d: indice del giorno (da 0 a 30, per un totale di 31 giorni)
    #    - s: indice del turno (0 = Mattina, 1 = Pomeriggio, 2 = Notte)
    # 4. Utilizziamo model.NewBoolVar per definire ciascuna variabile.
    all_nurses = std_nurses + spec_nurses
    for n in all_nurses:
        for d in range(31):
            for s in range(3):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # CoT:
    # 1. Obiettivo: Garantire che ciascun dipendente copra al massimo un turno al giorno.
    # 2. Variabili coinvolte: shifts[(n, d, s)] per ogni turno s in {0, 1, 2} dello stesso giorno d.
    # 3. Funzione OR-Tools: model.Add(sum(...) <= 1) applicata per ogni infermiere e ogni giorno.
    for n in all_nurses:
        for d in range(31):
            model.Add(sum(shifts[(n, d, s)] for s in range(3)) <= 1)

    # CoT:
    # 1. Obiettivo: Impedire l'assegnazione di turni consecutivi a cavallo di due giorni (Notte -> Mattina del giorno dopo).
    # 2. Variabili coinvolte: shifts[(n, d, 2)] (Notte del giorno d) e shifts[(n, d+1, 0)] (Mattina del giorno d+1).
    # 3. Funzione OR-Tools: model.AddImplication per imporre che se il turno di Notte al giorno d è attivo, 
    #    allora il turno di Mattina al giorno d+1 deve essere disattivato.
    for n in all_nurses:
        for d in range(30):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, 0)].Not())

    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte.
    # 2. Variabili coinvolte: shifts[(n, d, 2)] (Notte al giorno d) e tutti i turni s in {0, 1, 2} dei giorni d+1 e d+2.
    # 3. Funzione OR-Tools: model.AddImplication per forzare a 0 tutti i turni dei giorni d+1 e d+2 se l'infermiere fa la Notte al giorno d.
    for n in all_nurses:
        for d in range(31):
            if d + 1 < 31:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+1, s)].Not())
            if d + 2 < 31:
                for s in range(3):
                    model.AddImplication(shifts[(n, d, 2)], shifts[(n, d+2, s)].Not())

    # CoT:
    # 1. Obiettivo: Rispettare il carico di lavoro mensile di esattamente 25 turni equivalenti per ciascun lavoratore.
    # 2. Peso dei turni: Mattina (s=0) vale 1, Pomeriggio (s=1) vale 1, Notte (s=2) vale 2.
    # 3. Variabili coinvolte: shifts[(n, d, s)] per tutti i giorni d e turni s di un lavoratore n.
    # 4. Funzione OR-Tools: model.Add(sum(pesi * variabili) == 25) per ciascun lavoratore.
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] for d in range(31)) == 25
        )

    # CoT:
    # 1. Obiettivo: Limitare il tempo di lavoro settimanale a un massimo di 36 ore su finestre fisse.
    # 2. Finestre fisse (settimane): Settimana 1 (giorni 0-6), Settimana 2 (giorni 7-13), Settimana 3 (giorni 14-20), Settimana 4 (giorni 21-27), Settimana 5 (giorni 28-30).
    # 3. Durata turni: Mattina (s=0) = 6 ore, Pomeriggio (s=1) = 6 ore, Notte (s=2) = 12 ore.
    # 4. Funzione OR-Tools: model.Add(sum(ore * variabili) <= 36) per ciascun lavoratore e ciascuna settimana.
    weeks = [
        range(0, 7),
        range(7, 14),
        range(14, 21),
        range(21, 28),
        range(28, 31)
    ]
    for n in all_nurses:
        for w in weeks:
            model.Add(
                sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] for d in w) <= 36
            )

    # CoT:
    # 1. Obiettivo: Garantire almeno un giorno di riposo assoluto (0 turni assegnati) nell'arco del mese.
    # 2. Poiché un dipendente può fare al massimo 1 turno al giorno, avere almeno un giorno di riposo significa che il numero totale di giorni lavorati deve essere al massimo 30 (su 31 giorni totali).
    # 3. Funzione OR-Tools: model.Add(sum(tutti i turni del mese) <= 30) per ciascun lavoratore.
    for n in all_nurses:
        model.Add(sum(shifts[(n, d, s)] for d in range(31) for s in range(3)) <= 30)

    # CoT:
    # 1. Obiettivo: Implementare i requisiti di copertura del personale in base allo scenario (Caso A o Caso B).
    # 2. Caso A (Lavoratori Omogenei): Se non ci sono infermieri specializzati (spec_nurses è vuota), ogni turno deve avere almeno 2 lavoratori.
    # 3. Caso B (Lavoratori Misti): Se ci sono infermieri specializzati, ogni turno deve avere almeno 3 lavoratori totali, di cui almeno 1 deve essere specializzato.
    # 4. Funzione OR-Tools: model.Add(sum(...) >= target) applicata per ogni giorno d e turno s.
    if len(spec_nurses) == 0:
        # Caso A: Lavoratori Omogenei
        for d in range(31):
            for s in range(3):
                model.Add(sum(shifts[(n, d, s)] for n in std_nurses) >= 2)
    else:
        # Caso B: Lavoratori Misti
        for d in range(31):
            for s in range(3):
                # Almeno 3 lavoratori in totale (standard + specializzati)
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                # Almeno 1 lavoratore specializzato
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    return model, shifts