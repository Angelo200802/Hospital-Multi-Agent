from typing import Optional
from typing import List, Optional, Union
from pydantic import BaseModel, Field
from enum import Enum

class CategoriaTurno(Enum):
    MATTINA = "mattina"
    POMERIGGIO = "pomeriggio"
    NOTTE = "notte"
    FESTIVO = "festivo"
    WEEKEND = "weekend"

class TurnoReale(Enum):
    MATTINA = "mattina"
    POMERIGGIO = "pomeriggio"
    NOTTE = "notte"
    TUTTI = "tutti" 

class TurnoAssegnato(Enum):
    M = "M"
    P = "P"
    N = "N"
    R = "R"  # Riposo

class GiornoSettimana(Enum):
    LUNEDI = "lunedì"
    MARTEDI = "martedì"
    MERCOLEDI = "mercoledì"
    GIOVEDI = "giovedì"
    VENERDI = "venerdì"
    SABATO = "sabato"
    DOMENICA = "domenica"

class RichiestaSpecifica(BaseModel):
    data: str = Field(..., description="La data specifica (formato YYYY-MM-DD)")
    turno: List[TurnoReale] = Field(..., description="Il turno interessato (mattina, pomeriggio, notte, o tutti se indisponibile l'intero giorno)")
    desiderato: bool = Field(..., description="True se il dipendente VUOLE lavorare, False se NON PUO'/NON VUOLE lavorare in quel turno")

class PreferenzeDipendente(BaseModel):
    id_dipendente: str = Field(..., description="L'identificativo del dipendente (es. 'A')")
    is_specialised: bool = Field(default=False, description="Indica se il dipendente è specializzato")
    
    turni_desiderati: List[CategoriaTurno] = Field(default=[], description="Elenco dei turni preferiti")
    turni_da_evitare: List[CategoriaTurno] = Field(default=[], description="Elenco dei turni sgraditi")
    giorni_settimana_graditi: List[GiornoSettimana] = Field(
        default=[], 
        description="Giorni della settimana ricorrenti in cui il dipendente PREFERISCE lavorare (es. 'lunedì', 'martedì')"
    )
    
    giorni_settimana_sgraditi: List[GiornoSettimana] = Field(
        default=[], 
        description="Giorni della settimana ricorrenti in cui il dipendente preferisce NON lavorare (es. 'venerdì', 'domenica')"
    )
    richieste_specifiche: List[RichiestaSpecifica] = Field(
        default=[], 
        description="Richieste esatte per date specifiche. Se il dipendente non vuole lavorare in un giorno ricorrente (es. 'venerdì'), l'LLM deve calcolare le date esatte tra il 07-12-2026 e il 06-01-2027 e inserirle qui."
    )
    
    max_emergenze: Optional[int] = Field(default=None, description="Max turni di emergenza accettati")

    giorno_riposo_preferito: Optional[Union[GiornoSettimana, str]] = Field(
        default=None, 
        description="Il riposo desiderato. Può essere un giorno della settimana (es. 'domenica') OPPURE una data specifica in formato YYYY-MM-DD (es. '2026-12-24')."
    )
    tolleranza_turni_consecutivi: List[CategoriaTurno] = Field(default=[], description="Combinazioni di turni consecutivi sgraditi (es. festivi)")

class VincoliStrutturati(BaseModel):
    preferenze_dipendenti: List[PreferenzeDipendente] = Field(
        description="Lista delle preferenze strutturate per tutti i dipendenti menzionati nell'input"
    )

    def __str__(self):
        stringa = "Vincoli Strutturati:\n"
        for pref in self.preferenze_dipendenti:
            stringa += f"  - Dipendente {pref.id_dipendente} (Specializzato: {pref.is_specialised}):\n"
            stringa += f"    Turni desiderati: {[t.value for t in pref.turni_desiderati]}\n"
            stringa += f"    Turni da evitare: {[t.value for t in pref.turni_da_evitare]}\n"
            stringa += f"    Giorni della settimana graditi: {[g.value for g in pref.giorni_settimana_graditi]}\n"
            stringa += f"    Giorni della settimana sgraditi: {[g.value for g in pref.giorni_settimana_sgraditi]}\n"
            stringa += f"    Richieste specifiche:\n"
            for req in pref.richieste_specifiche:
                turni = [t.value for t in req.turno]
                stringa += f"      - Data: {req.data}, Turno: {turni}, Desiderato: {req.desiderato}\n"
            if pref.max_emergenze is not None:
                stringa += f"    Max emergenze accettate: {pref.max_emergenze}\n"
            if pref.giorno_riposo_preferito is not None:
                riposo = pref.giorno_riposo_preferito.value if isinstance(pref.giorno_riposo_preferito, GiornoSettimana) else pref.giorno_riposo_preferito
                stringa += f"    Giorno di riposo preferito: {riposo}\n"
            if pref.tolleranza_turni_consecutivi:
                turni_consecutivi = [t.value for t in pref.tolleranza_turni_consecutivi]
                stringa += f"    Tolleranza turni consecutivi sgraditi: {turni_consecutivi}\n"
        return stringa

class Suggerimento(BaseModel):
        dipendente_id: str = Field(..., description="ID del dipendente a cui si riferisce il suggerimento")
        messaggio: str = Field(..., description="Il suggerimento specifico su cosa correggere nelle preferenze estratte per rendere valide")

class PreferenzeValidate(BaseModel):
    
    valide : bool = Field(..., description="Indica se le preferenze estratte sono valide e coerenti con l'input originale")
    suggerimenti: Optional[List[Suggerimento]] = Field(default=None, description="Se valide è None, altrimenti contiene una lista di coppie chiave-valore dove la chiave è l'ID del dipendente e il valore è un suggerimento su cosa correggere nelle preferenze estratte per renderle valide")

    def __str__(self):
        if self.valide:
            return "Le preferenze estratte sono valide."
        
        if not self.suggerimenti:
            return "Le preferenze non sono valide, ma nessun dettaglio è stato fornito."
            
        # Corretto l'accesso alla lista di oggetti Pydantic
        suggerimenti_str = "\n".join([
            f"  - Dipendente {s.dipendente_id}: {s.messaggio}" 
            for s in self.suggerimenti
        ])
        return f"Suggerimenti:\n{suggerimenti_str}"

class TurniDipendente(BaseModel):
    id_dipendente: str = Field(..., description="L'identificativo del dipendente (es. 'A')")
    turni_assegnati: List[TurnoAssegnato] = Field(default=[], description="Elenco dei turni assegnati al dipendente")

class Piano(BaseModel):
    
    assegnamenti: List[TurniDipendente] = Field(default=[], description="Elenco degli assegnamenti dei turni per ogni dipendente")
    
    def __str__(self):
        string = "Piano Attuale:\n"
        for turni_dipendente in self.assegnamenti:
            string += f"  - Dipendente {turni_dipendente.id_dipendente}:\n"
            string += " ".join([t.value for t in turni_dipendente.turni_assegnati]) + "\n"
        return string

class SchedulerForm(BaseModel):
    # Input iniziale
    input: str
    
    # Fase 1a/4: Estrazione preferenze
    vincoli_soft: VincoliStrutturati = None      
    # Fase 1b/4: Verifica preferenze estratte
    preferenze_valide: PreferenzeValidate = None

    # Fase 2/4: Bozza del piano
    best_plan: Piano = None
    piano_attuale: Piano = None    
    
    # Fase 3a/4: Verifica vincoli Hard
    hard_constraints_valid: bool = None    
    feedback_errori_hard: str = None        
    
    # Fase 3b/4: Valutazione Fairness
    dipendente_piu_sfortunato: str = None  
    fairness_score: float = None             

    # Criteri di terminazione
    terminazione_raggiunta: bool = None     