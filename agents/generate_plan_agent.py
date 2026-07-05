from input_type import SchedulerForm, Piano
from llm import llm_call
from dotenv import load_dotenv
import os

load_dotenv()
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_GEN")

CALENDARIO = """

Dicembre 2026
 L|  M|  M|  G|  V|  S|  D
 7|  8|  9| 10| 11| 12| 13
14| 15| 16| 17| 18| 19| 20
21| 22| 23| 24| 25| 26| 27
28| 29| 30| 31|  -|  -|  -

Gennaio 2027
 L| M| M| G| V| S| D|
 -| -| -| -| 1| 2| 3
 4| 5| 6 

**Giorni festivi**: 8 Dicembre, 25 Dicembre, 26 Dicembre, 1 Gennaio, 6 Gennaio
"""

SYSTEM_PROMPT = """
## Il tuo Ruolo:
Sei un agente intelligente incaricato di generare un piano di turni per un gruppo di dipendenti di una struttura ospedaliera.
Devi produrre un piano valido per tutti i dipendenti indicati nell'input.

## Cosa Devi Fare:
Genera un piano turni che rispetti prima di tutto i vincoli hard.
Solo dopo aver rispettato i vincoli hard, prova a soddisfare le preferenze soft dei dipendenti.
I vincoli hard sono obbligatori.
Le preferenze soft sono desiderabili, ma possono essere ignorate se entrano in conflitto con i vincoli hard.

{hard_constraints}

{strategy}

## Il tuo input:
- Il calendario da seguire con evidenziati i giorni festivi.
- Le preferenze soft estratte dall'Agente di Estrazione Preferenze.
- Il piano generato precedentemente (se presente, altrimenti ignora questo punto).
- Eventuali errori hard riscontrati nel piano precedente (se presenti, altrimenti ignora questo punto).

## Il tuo Output:
Devi restituire un piano di turni completo per tutti i dipendenti per ogni giorno del periodo di pianificazione (7 Dicembre - 7 Gennaio).
Restituisci il piano nel formato strutturato indicato.

"""

PROMPT_PLANNER_GENERATORE = """
## Il tuo Ruolo:
Sei il Senior Planning Agent (Esperto Pianificatore) di una struttura ospedaliera. 
Il tuo compito NON è risolvere matematicamente il piano dei turni, ma agire come "Mente Strategica". 
Devi creare una Task Decomposition, una guida al ragionamento (CoT) e una checklist di Self-Control che un altro agente AI (il Generatore di Turni) utilizzerà come manuale di istruzioni per incastrare i turni.

## Descrizione dell'Input:
Riceverai in input un testo che contiene le regole operative e i vincoli di legge (Hard Constraints) inviolabili del reparto:

Devi leggere attentamente questo testo per capire quali sono i limiti orari, i requisiti di copertura e i colli di bottiglia logici (es. turni che bloccano i giorni successivi).

## Struttura Dati Obiettivo:
Tutta la tua strategia deve essere costruita attorno alla struttura dati che il Generatore dovrà produrre. 
Il Generatore strutturerà il piano mentalmente come una matrice: **per ogni dipendente, dovrà generare una lista di esattamente 31 stringhe** (una per ogni giorno del mese).
I valori ammessi in questa lista sono esclusivamente: **'M' (Mattina), 'P' (Pomeriggio), 'N' (Notte), 'R' (Riposo)**.
Le tue istruzioni dovranno guidarlo su come scorrere, riempire e validare in sicurezza queste liste di 31 elementi.

## Struttura del Prompt:
Il tuo output deve essere strutturato ESATTAMENTE in queste tre sezioni Markdown:
1. ## Strategia di Generazione
2. ## Strategia di Correzione Errori
3. ## Autocontrollo prima dell'output

## Strategia di Generazione passo passo (Come scrivere le sezioni):
Per compilare le tre sezioni, applica rigorosamente questa logica:

- **Per la "Strategia di Generazione":** Istruisci l'agente su come riempire le liste di 31 giorni. Analizza l'input e digli quali turni posizionare per primi negli array (es. se un turno impone riposi successivi, digli di piazzare prima quello e immediatamente i valori 'R' negli indici successivi della lista). 
Spiegagli poi come riempire gli indici rimanenti per raggiungere i carichi mensili in modo bilanciato e esplicitando di cercare di accontentare più dipendenti possibili.
- **Per la "Strategia di Correzione Errori":** Crea un protocollo di intervento chirurgico. Se l'agente riceverà una lista di errori, spiegagli che deve usare la tecnica dello "Scambio": per risolvere un errore, deve prendere l'indice `d` (giorno) nella lista del dipendente sfortunato e scambiare il valore (es. 'M' con 'R') con lo stesso indice `d` della lista di un collega compatibile (rispettando le qualifiche), senza sballare i conteggi totali di entrambi.
- **Per l'"Autocontrollo":** Crea una rigida checklist matematica basata sulla matrice. Istruisci l'agente a:
  1. Scorrere verticalmente lo stesso indice (da 0 a 30) su tutte le liste dei dipendenti per contare se ci sono abbastanza 'M', 'P', 'N' per garantire la copertura.
  2. Scorrere orizzontalmente le singole liste di 31 elementi per sommare i carichi (assegnando i giusti pesi a M, P, N) e le ore settimanali (controllando blocchi di 7 indici alla volta), per verificare che nessuno superi i limiti letti nei vincoli.

## Descrizione dell'Output atteso:
Restituisci ESCLUSIVAMENTE il testo delle tre sezioni richieste, formattato in Markdown.
Adatta le tue istruzioni e i tuoi esempi specificamente a ciò che hai dedotto dal testo dei vincoli in input.
NON inserire preamboli, saluti, conferme di comprensione o commenti finali.
"""

def leggi_piano_da_excel(percorso_file: str, lista_tutti_dipendenti = None):
        """
        Legge il piano turni da un file Excel strutturato con 3 righe (Mattina, Pomeriggio, Notte)
        e N colonne rappresentanti i giorni. Le celle contengono ID separati da virgole.
        """
        # Leggiamo il DataFrame
        import pandas as pd
        from input_type import TurniDipendente, TurnoAssegnato, Piano
        df = pd.read_excel(percorso_file)
        
        # Assumiamo che se la prima colonna contiene stringhe come "Mattina", "Pomeriggio", "Notte", 
        # i giorni veri e propri partano dalla seconda colonna (indice 1). 
        # Se il tuo file non ha l'etichetta del turno, metti semplicemente colonne_giorni = df.columns
        colonne_giorni = df.columns[1:] if len(df.columns) > 31 else df.columns
        num_giorni = len(colonne_giorni)

        # Inizializziamo un dizionario per tenere traccia dei turni: { 'A': ['R', 'R', ...], 'B': [...] }
        assegnamenti_dict = {}
        
        # Mappatura della riga dell'Excel al tipo di turno
        # Riga 0 = Mattina, Riga 1 = Pomeriggio, Riga 2 = Notte
        mappa_turni = {0: 'M', 1: 'P', 2: 'N'}
        
        # Iteriamo solo sulle prime 3 righe per sicurezza
        for indice_riga in range(3):
            turno_corrente = mappa_turni[indice_riga]
            
            # Iteriamo su tutte le colonne che rappresentano le date
            for indice_giorno, nome_colonna in enumerate(colonne_giorni):
                # Otteniamo il valore della cella
                cella = df.iloc[indice_riga, df.columns.get_loc(nome_colonna)]
                
                # Se la cella non è vuota (NaN)
                if pd.notna(cella):
                    # Dividiamo la stringa per virgola e togliamo eventuali spazi (es. "A, B, C" -> ['A', 'B', 'C'])
                    dipendenti_assegnati = [d.strip() for d in str(cella).split(',')]
                    
                    for dipendente in dipendenti_assegnati:
                        if dipendente: # Controlla che non sia una stringa vuota
                            # Se è la prima volta che incontriamo questo dipendente, inizializziamo i suoi 31 giorni a 'R'
                            if dipendente not in assegnamenti_dict:
                                assegnamenti_dict[dipendente] = ['R'] * num_giorni
                            
                            # Assegniamo il turno in quel giorno specifico
                            assegnamenti_dict[dipendente][indice_giorno] = turno_corrente

        # Se hai passato una lista con tutti i dipendenti noti (es. da 'A' a 'S'), 
        # garantiamo che anche chi non ha MAI lavorato nel mese (solo 'R') venga aggiunto al Piano
        if lista_tutti_dipendenti:
            for dipendente in lista_tutti_dipendenti:
                if dipendente not in assegnamenti_dict:
                    assegnamenti_dict[dipendente] = ['R'] * num_giorni

        # Convertiamo il dizionario negli oggetti Pydantic richiesti
        lista_turni_dipendente = []
        
        # Ordiniamo alfabeticamente gli ID dei dipendenti per avere un output pulito
        for dipendente in sorted(assegnamenti_dict.keys()):
            # Trasformiamo la lista di stringhe ['M', 'R', 'N'...] nella lista di Enum
            turni_enum = [TurnoAssegnato(t) for t in assegnamenti_dict[dipendente]]
            
            # Creiamo l'oggetto TurniDipendente
            obj_dipendente = TurniDipendente(
                id_dipendente=dipendente, 
                turni_assegnati=turni_enum
            )
            lista_turni_dipendente.append(obj_dipendente)

        # Restituiamo l'oggetto Piano finale
        return Piano(assegnamenti=lista_turni_dipendente)

def generate_strategy(hard_constraints_dal_file: str) -> str:
    """
    Fase 1: Agente LLM che produce la strategia di generazione e autocontrollo.
    """
    prompt_variables = { "hard_constraints_dal_file": hard_constraints_dal_file }
    
    strategy_text = llm_call(
        prompts=[
            ("system", PROMPT_PLANNER_GENERATORE),
            ("user", "## Vincoli Hard da seguire:\n{hard_constraints_dal_file}")
        ],
        #model = GEMINI_MODEL_NAME,
        prompt_variables=prompt_variables,
        #use_prod=True,
        #thinking_level = "high",
        temperature=0.3
    )

    return strategy_text.content.strip()

def generate_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    #print("Generazione del piano in corso...")
    #print("Generazione del piano completata") 
    #return { "n_iter_piano": state.n_iter_piano + 1,"piano_attuale" : leggi_piano_da_excel("/home/angelo/Project/uni/AI/progetto/output/piano_di_turni_1781547259.4604442.xlsx").model_dump()}
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": state.input['hard_constraints'].__str__(),
                        "strategy": state.planner_strategy if state.planner_strategy else generate_strategy(state.input['hard_constraints'].__str__()),
                        "vincoli_soft": state.vincoli_soft.__str__()  
                    }

    prompts = [
        ("system", SYSTEM_PROMPT),
        ("user", "##Calendario da seguire: {calendario}\n##Agente Estrattore Preferenze [Output]: {vincoli_soft}")
    ]
    if state.piano_attuale:
        prompt_variables["piano_precedente"] = state.piano_attuale.__str__()
        prompts[1] = ("user",prompts[1][1] + "\n##Piano generato precendentemente:\n{piano_precedente}")
    
    if state.feedback_errori_hard:
        prompt_variables["feedback_errori_hard"] = state.feedback_errori_hard.__str__()
        prompts[1] = ("user",prompts[1][1] + "\n##Feedback errori hard del piano precedente:\n{feedback_errori_hard}")
    
    print('Generazione del piano in corso')      
        
    piano_attuale = llm_call(
        prompts=prompts,
        model = GEMINI_MODEL_NAME,
        prompt_variables=prompt_variables,
        thinking_level = "high",
        structured_output=Piano,
        temperature=0.0
    )

    print(f"Fine generazione del piano.")

    return {"piano_attuale": piano_attuale.model_dump(), 
            "n_iter_piano": state.n_iter_piano + 1,
            "planner_strategy": prompt_variables["strategy"]}
