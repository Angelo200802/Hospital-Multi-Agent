# File generato automaticamente dallo Stage 1 (Workers Agent)
# Contiene la specifica OR-Tools e il modello di soddisfazione (Fairness)

from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    # Uniamo tutti i dipendenti in un'unica lista per poter applicare i vincoli generali
    all_nurses = std_nurses + spec_nurses
    num_days = 31
    num_shifts = 3  # 0 = Mattina, 1 = Pomeriggio, 2 = Notte

    # ==========================================
    # 1. CREAZIONE DELLE VARIABILI DECISIONALI
    # ==========================================
    # CoT:
    # 1. Obiettivo: Definire le variabili decisionali booleane per ogni combinazione di lavoratore, giorno e turno.
    # 2. Variabili e indici: n (ID lavoratore in all_nurses), d (giorno da 0 a 30), s (turno da 0 a 2).
    # 3. Funzione OR-Tools: model.NewBoolVar per creare variabili binarie (0 o 1).
    for n in all_nurses:
        for d in range(num_days):
            for s in range(num_shifts):
                shifts[(n, d, s)] = model.NewBoolVar(f"shift_{n}_{d}_{s}")

    # ==========================================
    # 2. VINCOLO: MASSIMO UN TURNO GIORNALIERO
    # ==========================================
    # CoT:
    # 1. Obiettivo: Impedire che un dipendente lavori in più di un turno nello stesso giorno.
    # 2. Variabili e indici: n in all_nurses, d in range(31).
    # 3. Funzione OR-Tools: model.Add con la somma delle variabili dei 3 turni dello stesso giorno <= 1.
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(num_shifts)) <= 1)

    # ==========================================
    # 3. VINCOLO: REQUISITI DI COPERTURA (PERSONALE)
    # ==========================================
    # CoT:
    # 1. Obiettivo: Garantire la copertura minima per ogni turno in base alla presenza di personale specializzato.
    #    - Caso A (Solo Standard): Almeno 2 lavoratori per turno.
    #    - Caso B (Misti): Almeno 3 lavoratori in totale, di cui almeno 1 deve essere specializzato.
    # 2. Variabili e indici: d in range(31), s in range(3), n in all_nurses / spec_nurses.
    # 3. Funzione OR-Tools: model.Add con somme e disuguaglianze (>= 2 o >= 3 e >= 1).
    has_specialized = len(spec_nurses) > 0

    for d in range(num_days):
        for s in range(num_shifts):
            if not has_specialized:
                # Caso A: Lavoratori Omogenei (almeno 2 per turno)
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 2)
            else:
                # Caso B: Lavoratori Misti (almeno 3 in totale, di cui almeno 1 specializzato)
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    # ==========================================
    # 4. VINCOLO: NESSUN TURNO CONSECUTIVO (NOTTE -> MATTINA)
    # ==========================================
    # CoT:
    # 1. Obiettivo: Impedire l'assegnazione del turno di Mattina (s=0) il giorno successivo a un turno di Notte (s=2).
    # 2. Variabili e indici: n in all_nurses, d in range(30) (fino al penultimo giorno).
    # 3. Funzione OR-Tools: model.AddImplication per imporre che se shifts[(n, d, 2)] è True, allora shifts[(n, d+1, 0)] deve essere False.
    for n in all_nurses:
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, 0)].Not())

    # ==========================================
    # 5. VINCOLO: RIPOSI POST-NOTTE (2 GIORNI DI RIPOSO)
    # ==========================================
    # CoT:
    # 1. Obiettivo: Garantire 2 giorni interi di riposo consecutivi dopo un turno di Notte (s=2).
    # 2. Variabili e indici: n in all_nurses, d in range(31). Giorni successivi d+1 e d+2 (se entro i limiti del mese).
    # 3. Funzione OR-Tools: model.Add(sum(...) == 0).OnlyEnforceIf(shifts[(n, d, 2)]) per azzerare tutti i turni nei due giorni successivi.
    for n in all_nurses:
        for d in range(num_days):
            if d + 1 < num_days:
                model.Add(sum(shifts[(n, d + 1, s)] for s in range(num_shifts)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])
            if d + 2 < num_days:
                model.Add(sum(shifts[(n, d + 2, s)] for s in range(num_shifts)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])

    # ==========================================
    # 6. VINCOLO: CARICO DI LAVORO MENSILE (ESATTAMENTE 25 TURNI)
    # ==========================================
    # CoT:
    # 1. Obiettivo: Rispettare il carico di lavoro mensile di esattamente 25 turni di carico.
    #    - Mattina (s=0) = 1 carico
    #    - Pomeriggio (s=1) = 1 carico
    #    - Notte (s=2) = 2 carichi
    # 2. Variabili e indici: n in all_nurses, d in range(31).
    # 3. Funzione OR-Tools: model.Add con equazione lineare pesata == 25.
    for n in all_nurses:
        model.Add(
            sum(shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)] for d in range(num_days)) == 25
        )

    # ==========================================
    # 7. VINCOLO: LIMITE ORARIO SETTIMANALE (MAX 36 ORE)
    # ==========================================
    # CoT:
    # 1. Obiettivo: Impedire il superamento di 36 ore lavorative in ciascuna settimana fissa di 7 giorni.
    #    - Mattina (s=0) = 6 ore
    #    - Pomeriggio (s=1) = 6 ore
    #    - Notte (s=2) = 12 ore
    # 2. Variabili e indici: n in all_nurses, d suddiviso in finestre fisse di 7 giorni.
    # 3. Funzione OR-Tools: model.Add con somma pesata delle ore <= 36 per ogni settimana.
    weeks = [
        range(0, 7),      # Settimana 1 (7-13 Dic)
        range(7, 14),     # Settimana 2 (14-20 Dic)
        range(14, 21),    # Settimana 3 (21-27 Dic)
        range(21, 28),    # Settimana 4 (28 Dic - 3 Gen)
        range(28, 31)     # Settimana 5 (4-6 Gen, giorni rimanenti)
    ]
    for n in all_nurses:
        for week in weeks:
            model.Add(
                sum(6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)] for d in week) <= 36
            )

    # ==========================================
    # 8. VINCOLO: RIPOSO MENSILE MINIMO (ALMENO 1 GIORNO)
    # ==========================================
    # CoT:
    # 1. Obiettivo: Garantire almeno un giorno di riposo assoluto (0 turni assegnati) nell'arco del mese.
    # 2. Variabili e indici: n in all_nurses, d in range(31).
    # 3. Funzione OR-Tools: Poiché un dipendente può fare al massimo 1 turno al giorno, se la somma totale dei turni
    #    assegnati nel mese è <= 30, allora ci sarà matematicamente almeno 1 giorno con 0 turni.
    for n in all_nurses:
        model.Add(sum(shifts[(n, d, s)] for d in range(num_days) for s in range(num_shifts)) <= 30)

    # ==========================================
    # 9. VINCOLI HARD SPECIFICI (FERIE E INDISPONIBILITÀ ASSOLUTE)
    # ==========================================
    
    # CoT:
    # 1. Obiettivo: Implementare l'indisponibilità assoluta del Dipendente C per ferie il 25 e 26 Dicembre 2026.
    # 2. Variabili e indici: n = 'C', d = 18 (25 Dicembre) e d = 19 (26 Dicembre), per tutti i turni s.
    # 3. Funzione OR-Tools: model.Add per forzare le variabili a 0.
    if 'C' in all_nurses:
        for s in range(num_shifts):
            model.Add(shifts[('C', 18, s)] == 0)
            model.Add(shifts[('C', 19, s)] == 0)

    # CoT:
    # 1. Obiettivo: Implementare l'indisponibilità assoluta del Dipendente H per il turno di notte il 31 Dicembre 2026.
    # 2. Variabili e indici: n = 'H', d = 24 (31 Dicembre), s = 2 (Notte).
    # 3. Funzione OR-Tools: model.Add per forzare la variabile a 0.
    if 'H' in all_nurses:
        model.Add(shifts[('H', 24, 2)] == 0)

    # CoT:
    # 1. Obiettivo: Implementare l'indisponibilità assoluta del Dipendente K per ferie l'8 Dicembre 2026.
    # 2. Variabili e indici: n = 'K', d = 1 (8 Dicembre), per tutti i turni s.
    # 3. Funzione OR-Tools: model.Add per forzare le variabili a 0.
    if 'K' in all_nurses:
        for s in range(num_shifts):
            model.Add(shifts[('K', 1, s)] == 0)

    return model, shifts