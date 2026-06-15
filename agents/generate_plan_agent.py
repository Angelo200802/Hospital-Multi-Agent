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

##Strategia di Generazione:
Segui questa strategia mentale prima di produrre l'output:
1. Crea una distribuzione iniziale bilanciata dei turni tra i dipendenti.
2. Assegna prima i turni di notte, perché impongono due giorni successivi di riposo.
3. Dopo ogni notte, inserisci immediatamente due riposi R, R.
4. Completa poi i turni di mattina e pomeriggio.
5. Controlla che ogni giorno abbia copertura sufficiente (almeno 2 dipendenti per turno giornaliero + 1 specializzato se presente).
6. Controlla che ogni dipendente non superi 36 ore settimanali.
7. Controlla che ogni dipendente abbia 31 valori.
8. Controlla che tutti i valori siano solo M, P, N, R.
9. Solo alla fine prova ad adattare il piano alle preferenze soft.

## Strategia di Correzione Errori (Se ricevi feedback di violazioni): 
Se ti viene fornito un piano precedente accompagnato da una lista di errori, il tuo compito non è ricreare il piano da zero, ma applicare esclusivamente correzioni chirurgiche:
1. Isola il problema: Leggi attentamente ogni errore per individuare esattamente l'ID del dipendente e il giorno/settimana in cui si verifica la violazione.
2. Non stravolgere il piano: Modifica SOLO i turni dei dipendenti menzionati negli errori o i turni strettamente necessari per compensare una modifica. Considera corretta tutta la parte del piano non menzionata negli errori.
3. Usa la tecnica dello Scambio (Swap): Per risolvere un errore di copertura o di ore, non aggiungere semplicemente un turno, altrimenti sballerai il conteggio totale dei 25 turni. Se devi aggiungere un turno a un dipendente in un giorno scoperto, toglili un turno in un altro giorno, passandolo a un collega.
4. Attenzione agli Specializzati: Se l'errore riguarda la copertura di uno specializzato (minimo 1 richiesto), puoi scambiare quel turno solo con un altro lavoratore specializzato.
5. Ribilanciamento a catena: Ogni volta che sposti una 'N' (Notte) per correggere un errore, ricordati che la Notte vale doppio per il carico mensile (2) e richiede obbligatoriamente di spostare anche i due riposi 'R' successivi.

## Autocontrollo prima dell'output (Passo-Passo): 
Prima di generare l'output finale, verifica mentalmente il piano:
1. Per ogni dipendente crea mentalmente una lista di 31 turni (es. Dipendente A -> ['M', 'R', 'N', ...]) che rappresentano i turni assegnati per ogni giorno del mese.
2. Verifica dei 2 giorni post-notte: Controlla che ogni 'N' sia categoricamente seguito da due 'R'.
3. Verifica delle 36 ore: Assicurati che nei 7 giorni che compongono la settimana ci sia almeno un turno di riposo per rietrare nel vincolo di 36 ore settimanli.
4. Calcolo dei 25 turni: Per ogni dipendente, conta il carico sommando i turni 'M' e 'P' (valore 1) e i turni 'N' (valore 2) finché non arrivi a ESATTAMENTE 25 per ciascuno, se li ha già raggiunti, non assegnare più turni a quel dipendente.
5. Verifica che per ogni colonna virtuale (giorno della settimana) ci siano i numeri minimi di dipendenti richiesti:
    - 2 M, 2 P, 2 N se non ci sono specializzati.
    - 1 specializzato + 2 qualsiasi se ci sono specializzati.
6. Verifica Correzione Feedback: Rileggi la lista degli errori che ti è stata fornita in input. Per ogni errore elencato, controlla mentalmente la nuova matrice che hai generato: hai effettivamente eliminato la violazione in quel giorno specifico per quel dipendente?
7. Verifica dei Danni Collaterali: Assicurati che, per correggere gli errori di un dipendente, tu non abbia inavvertitamente modificato la struttura dei dipendenti che non avevano errori (es. rompendo i loro 25 turni mensili o le loro coperture).
8. **IMPORTANTE** : Non sacrificare **MAI** un vincolo hard per soddisfare una preferenza soft altrimenti **MORIRAI**.

## Il tuo input:
- Il calendario da seguire con evidenziati i giorni festivi.
- Le preferenze soft estratte dall'Agente di Estrazione Preferenze.
- Il piano generato precedentemente (se presente, altrimenti ignora questo punto).
- Eventuali errori hard riscontrati nel piano precedente (se presenti, altrimenti ignora questo punto).

## Il tuo Output:
Devi restituire un piano di turni completo per tutti i dipendenti per ogni giorno del periodo di pianificazione (7 Dicembre - 7 Gennaio).
Restituisci il piano nel formato strutturato indicato.

"""

HARD_CONSTRAINTS = """
## Vincoli Hard da Rispettare **AD OGNI FOTTUTISSIMO COSTO**:
- Ogni dipendente può lavorare al **massimo un turno al giorno**.
- Non sono permessi turni consecutivi a cavallo di due giorni (es. Notte -> Mattina).
- Dopo un turno di notte, il dipendente deve avere **almeno 2 giorni di riposo**.
- Requisiti di copertura per ogni turno:
    - Se ci sono dipendenti specializzati, ogni turno deve avere **almeno 1 specializzato** e **almeno 3 persone in totale**.
    - Se non ci sono dipendenti specializzati, ogni turno deve avere **almeno 2 lavoratori qualsiasi**.
- Ogni dipendente deve lavorare esattamente **25 turni mensili** (considerando la notte come carico di lavoro doppio).
- Ogni dipendente può lavorare per un **massimo di 36 ore settimanali** (ogni turno dura 6 ore tranne la notte che dura 12 ore).
- All'interno del mese di lavoro ogni dipendente deve avere **almeno un giorno di riposo garantito**.
"""

def generate_plan_node(state: SchedulerForm) -> SchedulerForm:
    """
    Fase 2 e Fase 4: Agente LLM che produce la bozza o la raffina tramite callback.
    Se riceve errori hard, corregge il piano. 
    Se riceve un 'dipendente_piu_sfortunato', tenta di migliorare la sua situazione.
    """
    
    prompt_variables = { "calendario": CALENDARIO , 
                        "hard_constraints": HARD_CONSTRAINTS,
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
        #use_prod=True,
        thinking_level = "high",
        structured_output=Piano,
        temperature=0.0
    )

    print(f"Fine generazione del piano.")

    return {"piano_attuale": piano_attuale.model_dump(), "n_iter_piano": state.n_iter_piano + 1}
