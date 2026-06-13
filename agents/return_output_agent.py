from input_type import SchedulerForm, TurnoAssegnato
from datetime import date, timedelta
import pandas as pd
import os, time


def return_output_node(state: SchedulerForm) -> SchedulerForm:
    """
    Nodo finale che restituisce il piano definitivo in un formato leggibile.
    """

    print('Preparazione del piano finale in corso')
        
    piano = state.best_plan

    map_turni = {
        TurnoAssegnato.M: "Mattina",
        TurnoAssegnato.P: "Pomeriggio",
        TurnoAssegnato.N: "Notte"
    }

    data_inizio = date(2026, 12, 7)
    colonne = [(data_inizio + timedelta(days=d)).strftime("%Y-%m-%d") for d in range(31)]

    righe = {
        "Mattina": [[] for _ in range(31)],
        "Pomeriggio": [[] for _ in range(31)],
        "Notte": [[] for _ in range(31)]
    }

    for assegnamento in piano.assegnamenti:
        
        dipendente = assegnamento.id_dipendente
        turni = assegnamento.turni_assegnati

        for d_idx, turno_enum in enumerate(turni):
            if turno_enum in map_turni:
                nome_turno = map_turni[turno_enum]
                righe[nome_turno][d_idx].append(dipendente)

    for turno in righe.keys():
        for d_idx in range(31):
            cella = righe[turno][d_idx]
            righe[turno][d_idx] = ", ".join(cella) if cella else "-"

    
    df = pd.DataFrame.from_dict(righe, orient='index', columns=colonne)
    try:
        df.to_excel(f"{os.getcwd()}/output/piano_di_turni_{time.time()}.xlsx", index_label="Fascia Oraria")
    except ImportError:
        print("Errore: assicurati di aver installato la libreria 'openpyxl' (pip install openpyxl pandas) per esportare in Excel.")

    print("Piano finale preparato e salvato in output.")


