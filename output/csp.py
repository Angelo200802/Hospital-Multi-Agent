# File generato automaticamente dallo Stage 1 (Workers Agent)
# Contiene la specifica OR-Tools e il modello di soddisfazione (Fairness)

from ortools.sat.python import cp_model

def crea_modello_vincoli_hard(model, shifts, std_nurses, spec_nurses):
    """
    Configura i vincoli hard per la pianificazione dei turni ospedalieri.
    
    Parametri:
    - model: Istanza di cp_model.CpModel.
    - shifts: Dizionario vuoto che conterrà le variabili decisionali.
    - std_nurses: Lista di stringhe con gli ID dei dipendenti Standard.
    - spec_nurses: Lista di stringhe con gli ID dei dipendenti Specializzati.
    
    Ritorna:
    - model: Il modello OR-Tools con i vincoli applicati.
    - shifts: Il dizionario delle variabili decisionali popolate.
    """
    
    # Uniamo tutti i dipendenti in un'unica lista per facilitare l'iterazione globale
    all_nurses = std_nurses + spec_nurses
    num_days = 31  # Dal 7 Dicembre al 6 Gennaio compresi
    num_shifts = 3  # 0 = Mattina, 1 = Pomeriggio, 2 = Notte

    # =========================================================================
    # 1. CREAZIONE DELLE VARIABILI DECISIONALI
    # =========================================================================
    # CoT:
    # - Obiettivo: Definire le variabili booleane per l'assegnazione dei turni.
    # - Variabili coinvolte: shifts[(n, d, s)] per ogni infermiere 'n', giorno 'd' e turno 's'.
    # - Funzione OR-Tools: model.NewBoolVar per creare variabili decisionali binarie (0 o 1).
    for n in all_nurses:
        for d in range(num_days):
            for s in range(num_shifts):
                shifts[(n, d, s)] = model.NewBoolVar(f'shift_{n}_{d}_{s}')

    # =========================================================================
    # 2. VINCOLO: MASSIMO UN TURNO GIORNALIERO
    # =========================================================================
    # CoT:
    # - Obiettivo: Impedire che un dipendente lavori in più di un turno nello stesso giorno.
    # - Variabili coinvolte: shifts[(n, d, s)] per un dipendente 'n' e giorno 'd' fissati, al variare di 's'.
    # - Funzione OR-Tools: model.Add(sum(...) <= 1) per garantire che la somma dei turni giornalieri sia al massimo 1.
    for n in all_nurses:
        for d in range(num_days):
            model.Add(sum(shifts[(n, d, s)] for s in range(num_shifts)) <= 1)

    # =========================================================================
    # 3. VINCOLO: NESSUN TURNO CONSECUTIVO (NOTTE -> MATTINA)
    # =========================================================================
    # CoT:
    # - Obiettivo: Impedire l'assegnazione del turno di Mattina (s=0) il giorno successivo a un turno di Notte (s=2).
    # - Variabili coinvolte: shifts[(n, d, 2)] (Notte del giorno d) e shifts[(n, d+1, 0)] (Mattina del giorno d+1).
    # - Funzione OR-Tools: model.AddImplication per imporre che se il turno di Notte è attivo, il turno di Mattina successivo deve essere disattivato.
    for n in all_nurses:
        for d in range(num_days - 1):
            model.AddImplication(shifts[(n, d, 2)], shifts[(n, d + 1, 0)].Not())

    # =========================================================================
    # 4. VINCOLO: RIPOSO POST-NOTTE (2 GIORNI INTERI DI RIPOSO)
    # =========================================================================
    # CoT:
    # - Obiettivo: Garantire 2 giorni interi di riposo consecutivi (d+1 e d+2) dopo un turno di Notte (s=2) al giorno d.
    # - Variabili coinvolte: shifts[(n, d, 2)] e tutti i turni dei giorni d+1 e d+2.
    # - Funzione OR-Tools: model.Add(sum(shifts del giorno d+1 o d+2) == 0).OnlyEnforceIf(shifts[(n, d, 2)]) per forzare il riposo assoluto nei due giorni successivi.
    for n in all_nurses:
        for d in range(num_days):
            # Se il giorno successivo d+1 rientra nell'orizzonte temporale
            if d + 1 < num_days:
                model.Add(sum(shifts[(n, d + 1, s)] for s in range(num_shifts)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])
            # Se il secondo giorno successivo d+2 rientra nell'orizzonte temporale
            if d + 2 < num_days:
                model.Add(sum(shifts[(n, d + 2, s)] for s in range(num_shifts)) == 0).OnlyEnforceIf(shifts[(n, d, 2)])

    # =========================================================================
    # 5. VINCOLO: CARICO DI LAVORO MENSILE (ESATTAMENTE 25 TURNI EQUIVALENTI)
    # =========================================================================
    # CoT:
    # - Obiettivo: Ogni lavoratore deve coprire esattamente 25 turni equivalenti nel mese.
    # - Pesi: Mattina (s=0) vale 1, Pomeriggio (s=1) vale 1, Notte (s=2) vale 2.
    # - Variabili coinvolte: Tutte le variabili shifts[(n, d, s)] per un determinato dipendente 'n'.
    # - Funzione OR-Tools: model.Add(sum(peso * shift) == 25) per imporre il carico esatto.
    for n in all_nurses:
        carico_mensile = sum(
            shifts[(n, d, 0)] + shifts[(n, d, 1)] + 2 * shifts[(n, d, 2)]
            for d in range(num_days)
        )
        model.Add(carico_mensile == 25)

    # =========================================================================
    # 6. VINCOLO: LIMITE ORARIO SETTIMANALE (MASSIMO 36 ORE)
    # =========================================================================
    # CoT:
    # - Obiettivo: Impedire che un dipendente superi le 36 ore di lavoro in ciascuna settimana fissa.
    # - Durate: Mattina = 6 ore, Pomeriggio = 6 ore, Notte = 12 ore.
    # - Settimane fisse: Definiamo 5 finestre temporali per coprire i 31 giorni.
    # - Variabili coinvolte: shifts[(n, d, s)] per i giorni appartenenti alla specifica settimana.
    # - Funzione OR-Tools: model.Add(sum(ore * shift) <= 36) per ciascuna settimana e dipendente.
    settimane = [
        range(0, 7),    # Settimana 1: giorni 0-6
        range(7, 14),   # Settimana 2: giorni 7-13
        range(14, 21),  # Settimana 3: giorni 14-20
        range(21, 28),  # Settimana 4: giorni 21-27
        range(28, 31)   # Settimana 5: giorni 28-30 (3 giorni rimanenti)
    ]
    
    for n in all_nurses:
        for settimana in settimane:
            ore_settimanali = sum(
                6 * shifts[(n, d, 0)] + 6 * shifts[(n, d, 1)] + 12 * shifts[(n, d, 2)]
                for d in settimana
            )
            model.Add(ore_settimanali <= 36)

    # =========================================================================
    # 7. VINCOLO: RIPOSO MENSILE MINIMO (ALMENO 1 GIORNO DI RIPOSO ASSOLUTO)
    # =========================================================================
    # CoT:
    # - Obiettivo: Garantire che ciascun dipendente abbia almeno un giorno di riposo assoluto (0 turni assegnati) nel mese.
    # - Logica matematica: Poiché il mese ha 31 giorni e un dipendente può fare al massimo 1 turno al giorno, avere almeno 1 giorno di riposo equivale a lavorare al massimo in 30 giorni su 31.
    # - Variabili coinvolte: shifts[(n, d, s)] per tutti i giorni e turni di un dipendente 'n'.
    # - Funzione OR-Tools: model.Add(sum(tutti i turni del mese) <= 30).
    for n in all_nurses:
        giorni_lavorati = sum(shifts[(n, d, s)] for d in range(num_days) for s in range(num_shifts))
        model.Add(giorni_lavorati <= 30)

    # =========================================================================
    # 8. VINCOLO: REQUISITI DI COPERTURA (CASO A VS CASO B)
    # =========================================================================
    # CoT:
    # - Obiettivo: Garantire la copertura minima dei turni in base alla presenza di personale specializzato.
    # - Logica di selezione:
    #   - Se 'spec_nurses' è vuota (Caso A - Lavoratori Omogenei): Ogni turno deve essere coperto da almeno 2 lavoratori.
    #   - Se 'spec_nurses' non è vuota (Caso B - Lavoratori Misti): Ogni turno deve avere almeno 3 lavoratori totali, di cui almeno 1 specializzato.
    # - Variabili coinvolte: shifts[(n, d, s)] per tutti i dipendenti disponibili per quel turno.
    # - Funzione OR-Tools: model.Add(sum(...) >= copertura_minima).
    specializzati_presenti = len(spec_nurses) > 0

    for d in range(num_days):
        for s in range(num_shifts):
            if not specializzati_presenti:
                # Caso A: Almeno 2 lavoratori omogenei per turno
                model.Add(sum(shifts[(n, d, s)] for n in std_nurses) >= 2)
            else:
                # Caso B: Almeno 3 lavoratori totali per turno
                model.Add(sum(shifts[(n, d, s)] for n in all_nurses) >= 3)
                # Caso B: Almeno 1 dei lavoratori deve essere specializzato
                model.Add(sum(shifts[(n, d, s)] for n in spec_nurses) >= 1)

    # =========================================================================
    # 9. VINCOLI DI INDISPONIBILITÀ / FERIE SPECIFICHE
    # =========================================================================
    # CoT:
    # - Obiettivo: Gestire eventuali ferie o indisponibilità assolute dichiarate.
    # - Analisi del testo in input: Non sono state dichiarate ferie o indisponibilità specifiche per singoli dipendenti nominati nel testo fornito.
    # - Di conseguenza, non vengono applicati vincoli di indisponibilità ad-hoc in questa esecuzione.

    return model, shifts