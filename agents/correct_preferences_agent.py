from input_type import SchedulerForm, VincoliStrutturati
from llm import llm_call

SYSTEM_PROMPT = f""" 
## Il tuo ruolo:
Sei un agente specializzato nella correzione delle preferenze per la pianificazione dei turni di una struttura ospedaliera. 
Il tuo compito è correggere le preferenze estratte da un agente LLM per renderle valide e coerenti con l'input originale fornito dall'utente.

## Cosa devi Fare:
- Devi analizzare le preferenze segnalate come non valide dall'agente di verifica, confrontarle con l'input originale e applicare le correzioni suggerite per renderle valide.
- Se le preferenze sono già valide, non devi apportare alcuna modifica.
- Se le preferenze non sono valide, ma non ci sono suggerimenti specifici, devi identificare autonomamente le discrepanze e correggerle basandoti sull'input originale. 

## Output Atteso:
Un set di preferenze che riguardano **esclusivamente** i dipendenti segnalati come non validi, corrette secondo i suggerimenti forniti o secondo la tua analisi, e strutturate in un formato JSON/Dict coerentes.
"""

def correct_preferences_node(state: SchedulerForm):
    
    testo_preferenze = state.input.strip()   
    vincoli_estratti = state.vincoli_soft if state.vincoli_soft else {}
    preferenze_valide = state.preferenze_valide
    
    print("Preferenze non valide per i seguenti dipendenti: ",[ s.dipendente_id for s in preferenze_valide.suggerimenti] if preferenze_valide and preferenze_valide.suggerimenti else "Nessun suggerimento specifico fornito." )
    
    correzioni = preferenze_valide.__str__()
    preferenze_sbagliate: str = VincoliStrutturati(
        preferenze_dipendenti=[
            pref for pref in vincoli_estratti.preferenze_dipendenti 
            if pref in [s.dipendente_id for s in preferenze_valide.suggerimenti]]
    ).__str__()

    
    prompt = [
        ("system", SYSTEM_PROMPT),
        ("user", """Ecco l'input originale con le preferenze espresse dai dipendenti:\n{testo_preferenze}\n\nAgente Verificatore[Output]:\nPreferenze Errate -> \n{preferenze_sbagliate}Correzioni -> \n{correzioni}""")
    ]

    print("Correzione delle preferenze in corso...")
    
    preferenze_corrette = llm_call(
        prompts=prompt,
        prompt_variables={
            "testo_preferenze": testo_preferenze,
            "preferenze_sbagliate": preferenze_sbagliate,
            "correzioni": correzioni
        },
        structured_output=VincoliStrutturati,
        temperature=0.5
    )
    print("Correzione delle preferenze completata.")
    
    id_corretti = [p.id_dipendente for p in preferenze_corrette.preferenze_dipendenti]
    
    # 2. Inizializziamo la lista finale inserendo DIRETTAMENTE tutti i nuovi vincoli corretti
    nuovi_vincoli = list(preferenze_corrette.preferenze_dipendenti)

    # 3. Estraiamo i vecchi vincoli gestendo sia il caso in cui sia un oggetto sia un dict
    if hasattr(vincoli_estratti, "preferenze_dipendenti"):
        vecchia_lista = vincoli_estratti.preferenze_dipendenti
    else:
        # Se per qualche motivo è un dizionario (o viene letto come tale)
        vecchia_lista = vincoli_estratti.get("preferenze_dipendenti", [])

    # 4. Aggiungiamo i vecchi vincoli SOLO se il dipendente non è presente tra quelli appena corretti
    for v in vecchia_lista:
        # Recuperiamo l'ID sia se v è un oggetto sia se è un dict
        v_id = v.id_dipendente if hasattr(v, "id_dipendente") else v.get("id_dipendente")
        
        if v_id not in id_corretti:
            nuovi_vincoli.append(v)

    # 5. Creiamo il container finale con la lista perfettamente pulita
    nuove_preferenze = VincoliStrutturati(preferenze_dipendenti=nuovi_vincoli)
    
    
    return {"vincoli_soft": nuove_preferenze.model_dump()}