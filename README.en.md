# TFR and supplementary pension calculator

A Streamlit dashboard for an indicative comparison between TFR left with the employer and TFR allocated to pension funds. The simulation also displays the INPS contribution balance reported in the CSV file.

> **Warning:** this is a demonstrative tool. It does not provide an official COVIP, INPS, or pension-fund projection and does not replace the fund's official information documents or professional advice.

## Requirements

- Python 3.10 or newer
- `pip`

Dependencies are listed in `requirements.txt`: Streamlit, pandas, Plotly, and openpyxl.

## Installation and launch

From the project directory:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit will open the dashboard in a browser, usually at `http://localhost:8501`.

On Windows, activate the virtual environment with:

```powershell
.venv\Scripts\Activate.ps1
```

## How to use it

1. Choose the starting year and retirement year in the sidebar.
2. Set the percentage of TFR allocated to the fund, the employee contribution, and the employer contribution.
3. Choose a prospective scenario: pessimistic, base, or optimistic.
4. Choose the cost method, the optional Life Cycle setting, and the divisor used for the indicative annuity.
5. Select one or more pension plans and adjust their parameters in the fund configuration expander when needed.
6. Review the metrics, chart, and year-by-year details.
7. Use the buttons at the bottom to download the result as CSV or Excel.

The displayed annuity is a simplified division of the final capital by the selected divisor, which defaults to 20 years. It is not an official actuarial conversion factor.

## Data

The application loads this file:

```text
estratto_conto_contributivo.csv
```

The file must contain these columns:

- `Descrizione`
- `Anno`
- `Retribuzione/Reddito`
- `Aliquota di computo (%)`
- `Contribuzione nell'anno`
- `Montante Contributivo`

Amounts may use the Italian format, for example `€ 27.012,21` or `33,00`. Years must be numeric and unique.

The CSV included in the project is demonstrative. Years after 2025 are estimates based on the growth profile observed in the available real data, not official future data. The `data_private/estratto_conto_contributivo.csv` file contains separate data and is not loaded automatically by the app.

### Prompt for converting an INPS extract to CSV

You can give an LLM the text copied from the INPS pension simulation and use a prompt like the one below. Replace the placeholders with your own data; do not treat the example below as real data.

```text
Convert the data I provide from an INPS pension simulation extract into a CSV compatible with a Python application.

Goal:
- create one row for each year;
- keep historical/real years separate from simulated years, using the description provided in the source or "Lavoratori dipendenti" when no description is available;
- sort rows by ascending year;
- use exactly these columns in this order:
	Descrizione,Anno,Retribuzione/Reddito,Aliquota di computo (%),Contribuzione nell'anno,Montante Contributivo

Rules:
1. Do not invent historical years, salaries, rates, or balances that I provide.
2. Keep the Italian number format for amounts: "€ 12.345,67". For the contribution rate use, for example, "33,00" without the percent sign.
3. If a value is missing or unreadable, stop and ask me to correct it; do not estimate it without authorization.
4. Check that "Contribuzione nell'anno" is consistent with salary and contribution rate, except where the source already contains a difference.
5. Check that "Montante Contributivo" is cumulative and that each year starts from the previous year's balance.
6. If I ask you to add simulated years, use a clearly distinguishable description such as "Lavoratori dipendenti - simulato" and apply only the assumptions I specify. Never mix estimates with historical data.
7. First return a short summary of the assumptions, then return only the CSV inside a csv code block, with no extra text inside the block.

Data to convert:
[PASTE THE INPS EXTRACT HERE]

Authorized assumptions for simulated years, if any:
[INSERT SALARY GROWTH, CONTRIBUTION RATE, YEARS TO ADD, AND OTHER ASSUMPTIONS HERE]
```

Invented example of the expected format, not based on real personal data:

```csv
Descrizione,Anno,Retribuzione/Reddito,Aliquota di computo (%),Contribuzione nell'anno,Montante Contributivo
Lavoratori dipendenti,2022,"€ 18.500,00","33,00","€ 6.105,00","€ 6.105,00"
Lavoratori dipendenti,2023,"€ 19.055,00","33,00","€ 6.288,15","€ 12.393,15"
Lavoratori dipendenti - simulato,2024,"€ 19.626,65","33,00","€ 6.476,79","€ 18.869,94"
```

## Simulation logic

- Annual TFR is calculated as salary multiplied by the configured percentage.
- Employee and employer contributions are calculated from the salary in the CSV.
- Fund balances are updated each year using contributions, returns, and a proxy cost.
- Historical returns configured for 2024 and 2025 are used for those years; later years use the selected prospective return and scenario.
- The INPS balance is read from `Montante Contributivo` and is not added to the fund balances.
- Fund plans, returns, costs, and asset allocations are configured in `config.json`.

## Main structure

```text
app.py                              Streamlit dashboard
simulation.py                       Simulation engine
charts.py                           Plotly chart
data_loader.py                     CSV loading and normalization
config.json                         Fund parameters and defaults
estratto_conto_contributivo.csv     Demo data loaded by the app
requirements.txt                    Python dependencies
```
