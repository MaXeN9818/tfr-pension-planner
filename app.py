"""Dashboard Streamlit per il confronto tra fondi pensione e TFR."""
import json
from io import BytesIO
from pathlib import Path

import pandas as pd
import streamlit as st

from charts import accumulation_chart
from data_loader import load_contributions
from simulation import FundConfig, estimated_annuity, simulate


st.set_page_config(page_title="Confronto fondi pensione", page_icon="📈", layout="wide")

DATA_PATH = Path(__file__).with_name("estratto_conto_contributivo.csv")
CONFIG_PATH = Path(__file__).with_name("config.json")


def load_config(path: Path) -> dict:
    """Carica la configurazione JSON e verifica che sia un oggetto."""
    try:
        with path.open(encoding="utf-8") as config_file:
            config = json.load(config_file)
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"Configurazione JSON non valida: {error}") from error
    if not isinstance(config, dict):
        raise ValueError("La configurazione JSON deve contenere un oggetto.")
    return config


def normalize_plan_label(gestore: str, nome_piano: str) -> str:
    """Normalizza il nome visualizzato del piano per evitare duplicazioni di Gestore."""
    base_name = (nome_piano or "").strip()
    manager_name = (gestore or "").strip()
    for prefix in [manager_name, manager_name.split()[0] if manager_name else ""]:
        if not prefix:
            continue
        if base_name.lower().startswith(prefix.lower()):
            base_name = base_name[len(prefix):].lstrip(" -")
            break
    return f"{manager_name} - {base_name}" if base_name else manager_name


def flatten_funds(config: dict) -> list[dict]:
    """Raccoglie tutti i piani disponibili in un unico catalogo flat."""
    funds = []
    for manager_key, manager_config in config.get("fondi", {}).items():
        if not isinstance(manager_config, dict):
            continue
        gestore = manager_config.get("gestore", manager_key)
        for plan in manager_config.get("piani", []):
            if not isinstance(plan, dict):
                continue
            label = normalize_plan_label(gestore, plan.get("nome", ""))
            funds.append({
                "label": label,
                "gestore": gestore,
                "manager_key": manager_key,
                "piano": plan,
            })
    return funds


def get_reported_float(plan: dict, key: str, label: str) -> float | None:
    """Restituisce un numero dichiarato nel config; se manca, segnala esplicitamente."""
    value = plan.get(key)
    if value is None:
        st.caption(f"{label}: N/D")
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        st.error(f"Il piano '{label}' contiene un valore non numerico per '{key}' nel config.json.")
        raise ValueError(f"Valore non numerico per '{key}' nel piano '{label}'.")


def euro(value: float) -> str:
    return f"€ {value:,.0f}".replace(",", "X").replace(".", ",").replace("X", ".")


def to_excel(frame: pd.DataFrame) -> bytes:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="Simulazione")
    return output.getvalue()


st.title("Confronto previdenza complementare")

try:
    data = load_contributions(DATA_PATH)
    config = load_config(CONFIG_PATH)
except (FileNotFoundError, ValueError) as error:
    st.error(f"Impossibile caricare dati o configurazione: {error}")
    st.stop()

min_year, max_year = int(data["Anno"].min()), int(data["Anno"].max())
simulation_config = config["simulazione"]
all_funds = flatten_funds(config)
option_labels = [entry["label"] for entry in all_funds]
default_labels = ["Cometa - Crescita", "Allianz INSIEME - Linea Bilanciata"]
selected_default = [label for label in default_labels if label in option_labels]
if not selected_default and option_labels:
    selected_default = option_labels[:2]

with st.sidebar:
    st.header("Parametri")
    start_year = st.slider("Anno di inizio", min_year, max_year, min_year)
    retirement_year = st.slider("Anno di pensionamento", start_year, max_year, max_year)
    st.subheader("Contributi")
    tfr_rate = st.number_input("TFR destinato al fondo (%)", 0.0, 100.0, float(simulation_config["tfr_destinato_percento"]), 0.01)
    worker_rate = st.number_input("Contributo lavoratore (%)", 0.0, 20.0, float(simulation_config["contributo_lavoratore_percento"]), 0.05)
    employer_rate = st.number_input("Contributo datore (%)", 0.0, 20.0, float(simulation_config["contributo_datore_percento"]), 0.05)
    extra_for_allianz = st.checkbox("Applica extra-TFR anche ad Allianz", value=bool(simulation_config["extra_allianz"]))
    st.caption("Il contributo datoriale è normalmente previsto da Cometa tramite adesione collettiva CCNL. Per Allianz INSIEME è disponibile solo in caso di adesione collettiva: attiva questa opzione solo se applicabile al tuo caso.")

    st.subheader("Rendimenti e costi")
    scenario = st.selectbox("Scenario prospettico", ["Pessimistico", "Base", "Ottimistico"], index=["Pessimistico", "Base", "Ottimistico"].index(simulation_config["scenario_default"]))
    cost_method = st.radio("Metodo costi", ["ISC", "Commissione di gestione"], index=["ISC", "Commissione di gestione"].index(simulation_config["metodo_costi_default"]))
    tfr_return = st.slider("TFR aziendale: rivalutazione netta (%)", -2.0, 8.0, float(simulation_config["rendimento_tfr_netto_percento"]), 0.05) / 100
    life_cycle = st.checkbox("Includi opzione Life Cycle Allianz (+30 €/anno)", value=bool(simulation_config["life_cycle_allianz"]))
    annuity_divisor = st.number_input("Divisore rendita (anni)", 1.0, 50.0, float(simulation_config["divisore_rendita_anni"]), 0.5)

    st.subheader("Piani disponibili")
    selected_labels = st.multiselect(
        "Seleziona fondi da confrontare",
        options=option_labels,
        default=selected_default,
        max_selections=5,
    )
    if len(selected_labels) > 5:
        st.warning("Sono visibili al massimo 5 piani contemporaneamente per mantenere leggibile il grafico.")

    label_lookup = {entry["label"]: entry for entry in all_funds}
    selected_templates = [label_lookup[label] for label in selected_labels]
    all_selected_fund_configs = []

    with st.expander("Configurazione dettagliata fondi"):
        for entry in selected_templates:
            manager_name = entry["gestore"]
            plan = entry["piano"]
            st.markdown(f"**{entry['label']}**")
            probability = plan.get("probabilita_raggiungimento_obiettivo_percento")
            if probability is None:
                st.caption("Probabilità di raggiungimento obiettivo: N/D")
            else:
                st.caption(f"Probabilità di raggiungimento obiettivo: {float(probability):.1f}%")

            asset_allocation = plan.get("asset_allocation") or {}
            equity = asset_allocation.get("azionario_percento")
            if equity is None:
                st.error(f"Il piano '{entry['label']}' non specifica 'asset_allocation.azionario_percento' nel config.json.")
                st.stop()
            equity = int(float(equity))

            expected_return_value = get_reported_float(plan, "rendimento_atteso_percento", entry["label"])
            proxy_note = " (proxy: media storica, non proiezione ufficiale)" if plan.get("rendimento_atteso_e_proxy_storico") is True else ""
            if expected_return_value is None:
                st.caption(f"Rendimento atteso: N/D{proxy_note}")
                expected_return = 0.0
            else:
                expected_return = st.slider(
                    f"{entry['label']}: rendimento atteso (%){proxy_note}",
                    -5.0,
                    15.0,
                    float(expected_return_value),
                    0.10,
                ) / 100

            own_asset_allocation = st.slider(f"Azionario {entry['label']} (%)", 0, 100, equity)

            isc_map = plan.get("isc_percento") or {}
            isc_value = isc_map.get("35_anni") if isinstance(isc_map, dict) else None
            if isc_value is None:
                st.caption("ISC annualizzato: N/D")
                isc_annual = None
            else:
                isc_annual = st.number_input(f"ISC {entry['label']} annualizzato (%)", 0.0, 5.0, float(isc_value), 0.01) / 100

            management_value = get_reported_float(plan, "commissione_gestione_percento", entry["label"])
            if management_value is None:
                st.error(f"Il piano '{entry['label']}' non specifica 'commissione_gestione_percento' nel config.json.")
                st.stop()
            management_fee = st.number_input(f"Gestione {entry['label']} (%)", 0.0, 5.0, float(management_value), 0.01) / 100

            entry_fee_value = get_reported_float(plan, "costo_adesione_euro", entry["label"])
            if entry_fee_value is None:
                st.error(f"Il piano '{entry['label']}' non specifica 'costo_adesione_euro' nel config.json.")
                st.stop()
            entry_fee = st.number_input(f"Adesione {entry['label']} (€)", 0.0, 500.0, float(entry_fee_value), 1.0)

            annual_fixed_fee_value = get_reported_float(plan, "costo_fisso_annuo_euro", entry["label"])
            if annual_fixed_fee_value is None:
                st.caption(f"Quota associativa {entry['label']} annua (€): N/D")
                annual_fixed_fee = 0.0
            else:
                annual_fixed_fee = st.number_input(f"Quota associativa {entry['label']} annua (€)", 0.0, 100.0, float(annual_fixed_fee_value), 1.0)

            historical_returns = {}
            for year_key, value in (plan.get("rendimenti_storici_percento") or {}).items():
                try:
                    year = int(year_key)
                except (TypeError, ValueError):
                    continue
                historical_returns[year] = float(value) / 100

            if isc_annual is None:
                st.warning(f"Il piano '{entry['label']}' non indica ISC annualizzato esplicito; la simulazione proseguirà con un costo ISC N/D, ma va verificato nel config.json.")
                isc_annual = 0.0

            st.caption(f"Asset allocation configurata: {entry['label']} {own_asset_allocation}% azionario / {100 - own_asset_allocation}% obbligazionario.")
            all_selected_fund_configs.append(
                FundConfig(
                    name=entry["label"],
                    historical_returns=historical_returns,
                    expected_return=expected_return,
                    management_fee=management_fee,
                    isc_annual=isc_annual,
                    entry_fee=entry_fee,
                    annual_fixed_fee=annual_fixed_fee,
                    manager=manager_name,
                    employer_contribution=(manager_name == "Cometa"),
                )
            )

    st.caption(f"Piani selezionati: {', '.join(selected_labels) if selected_labels else 'nessuno'}")

if not selected_labels:
    st.warning("Nessun fondo selezionato. Seleziona almeno un piano per avviare la simulazione.")
    st.stop()

funds_for_simulation = [
    config_fund for config_fund in all_selected_fund_configs
    if config_fund.name in selected_labels
]

if len(funds_for_simulation) == 0:
    st.warning("Nessun fondo valido trovato nella configurazione selezionata.")
    st.stop()

st.caption(f"{selected_labels[0]} · {selected_labels[1]} · TFR in azienda" if len(selected_labels) >= 2 else f"{selected_labels[0]} · TFR in azienda")

try:
    result = simulate(
        data,
        start_year,
        retirement_year,
        tfr_rate / 100,
        worker_rate / 100,
        employer_rate / 100,
        extra_for_allianz,
        cost_method,
        scenario,
        tfr_return,
        life_cycle,
        funds_for_simulation,
    )
except ValueError as error:
    st.error(str(error))
    st.stop()

last = result.iloc[-1]
selected_fund_names = [fund.name for fund in funds_for_simulation]
selected_fund_final_values = {fund.name: last[f"Montante {fund.name}"] for fund in funds_for_simulation}
summary_columns = st.columns(len(selected_fund_names) + 2)
for index, fund_name in enumerate(selected_fund_names):
    final_value = selected_fund_final_values[fund_name]
    summary_columns[index].metric(f"{fund_name} a pensionamento", euro(final_value), f"Rendita: {euro(estimated_annuity(final_value, annuity_divisor))}/anno")

tfr_final = last["Montante TFR non investito"]
inps_final = last["Montante INPS"]
summary_columns[len(selected_fund_names)].metric("TFR lasciato in azienda", euro(tfr_final), f"Rendita: {euro(estimated_annuity(tfr_final, annuity_divisor))}/anno")
summary_columns[len(selected_fund_names) + 1].metric("Montante INPS", euro(inps_final), "I pilastro, dal CSV")

st.info("I rendimenti 2024 e 2025 sono quelli storici indicati; gli anni successivi usano il tasso prospettico scelto. I costi sono applicati come proxy annuale: l'ISC è un indicatore sintetico e non coincide necessariamente con il costo effettivo di ogni anno.")

st.subheader("Confronto finale")
if len(selected_fund_names) >= 2:
    first_fund, second_fund = selected_fund_names[:2]
    difference = selected_fund_final_values[first_fund] - selected_fund_final_values[second_fund]
    percentage = difference / selected_fund_final_values[second_fund] * 100 if selected_fund_final_values[second_fund] else 0
    st.write(f"{first_fund} rispetto a {second_fund}: **{euro(difference)}** ({percentage:+.1f}%). Il confronto è sul capitale lordo simulato, prima della fiscalità e di eventuali costi di uscita.")

plot_series = [(f"Montante {fund.name}", fund.name) for fund in funds_for_simulation]
plot_series.extend([
    ("Montante TFR non investito", "TFR in azienda"),
    ("Montante INPS", "INPS"),
])
st.plotly_chart(accumulation_chart(result, plot_series), width="stretch")

st.subheader("Dettaglio anno per anno")
display_columns = ["Anno", "Retribuzione"]
for fund in funds_for_simulation:
    display_columns.append(f"Contributo annuo {fund.name}")
    display_columns.append(f"Montante {fund.name}")
display_columns.extend(["Montante TFR non investito", "Montante INPS"])

style_map = {column: "€ {:,.2f}" for column in display_columns if column != "Anno"}
st.dataframe(result[display_columns].style.format(style_map), width="stretch", hide_index=True)

export_frame = result[display_columns].copy()
export_frame.columns = [
    "Anno",
    "Retribuzione",
    *[f"Contributo annuo {fund.name}" for fund in funds_for_simulation],
    *[f"Montante {fund.name}" for fund in funds_for_simulation],
    "Montante TFR non investito",
    "Montante INPS",
]
col_csv, col_excel = st.columns(2)
col_csv.download_button("Scarica CSV", export_frame.to_csv(index=False).encode("utf-8-sig"), "simulazione_fondi.csv", "text/csv")
col_excel.download_button("Scarica Excel", to_excel(export_frame), "simulazione_fondi.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

with st.expander("Note metodologiche"):
    st.markdown("""
    - Il TFR destinato al fondo è calcolato come aliquota configurabile della retribuzione lorda del CSV.
    - La quota associativa e la quota di adesione sono mostrate nella configurazione, ma non vengono sottratte automaticamente dal montante: la simulazione applica i costi ricorrenti come tasso sul patrimonio, senza introdurre un costo fisso sproporzionato rispetto alla retribuzione.
    - La rendita è una divisione semplificata per il divisore scelto (default 20 anni), non il coefficiente attuariale ufficiale, che dipende da età, sesso, opzione e regolamento del fondo.
    - Il montante INPS è il primo pilastro riportato nel file e non viene sommato ai montanti dei fondi nel grafico.
    """)

st.warning("Simulazione indicativa con dati storici e stime dichiarate dai fondi, non è una proiezione ufficiale COVIP né sostituisce il Documento sulle rendite o la Nota Informativa ufficiale di ciascun fondo")
