"""Motore di simulazione dei fondi pensione e del TFR aziendale."""
from dataclasses import dataclass

import pandas as pd


@dataclass
class FundConfig:
    name: str
    historical_returns: dict[int, float]
    expected_return: float
    management_fee: float
    isc_annual: float
    entry_fee: float
    annual_fixed_fee: float = 0.0
    manager: str = ""
    employer_contribution: bool = False


def _annual_rate(year: int, fund: FundConfig, scenario_return: float) -> float:
    return fund.historical_returns.get(year, scenario_return)


def simulate(
    data: pd.DataFrame,
    start_year: int,
    retirement_year: int,
    tfr_rate: float,
    worker_rate: float,
    employer_rate: float,
    extra_for_allianz: bool,
    cost_method: str,
    scenario: str,
    tfr_net_return: float,
    life_cycle_fee: bool,
    funds: list[FundConfig],
) -> pd.DataFrame:
    """Restituisce una riga per anno con tutti i montanti di fine anno."""
    if not funds:
        raise ValueError("Nessun fondo selezionato per la simulazione.")

    period = data[data["Anno"].between(start_year, retirement_year)].copy()
    if period.empty:
        raise ValueError("Intervallo di simulazione vuoto.")

    scenario_factor = {"Pessimistico": 0.75, "Base": 1.0, "Ottimistico": 1.25}[scenario]
    balances = {fund.name: 0.0 for fund in funds}
    tfr_balance = 0.0
    rows = []
    for _, record in period.iterrows():
        year = int(record["Anno"])
        salary = float(record["Retribuzione/Reddito"])
        tfr = salary * tfr_rate
        worker = salary * worker_rate
        employer = salary * employer_rate if worker_rate > 0 else 0.0

        for fund in funds:
            employer_contribution = employer if fund.employer_contribution or (fund.manager == "Allianz INSIEME" and extra_for_allianz) else 0.0
            contribution = tfr + worker + employer_contribution
            annual_rate = _annual_rate(year, fund, fund.expected_return * scenario_factor)
            annual_cost = fund.isc_annual if cost_method == "ISC" else fund.management_fee
            if fund.manager == "Allianz INSIEME" and life_cycle_fee:
                annual_cost += 30.0 / max(salary, 1.0)
            balances[fund.name] = (balances[fund.name] + contribution) * (1 + annual_rate - annual_cost)

        tfr_balance = (tfr_balance + tfr) * (1 + tfr_net_return)

        row = {
            "Anno": year,
            "Retribuzione": salary,
            "Contributo TFR": tfr,
            "Contributo lavoratore": worker,
            "Contributo datore": employer,
            "Montante TFR non investito": tfr_balance,
            "Montante INPS": float(record["Montante Contributivo"]),
        }
        for fund in funds:
            row[f"Contributo annuo {fund.name}"] = tfr + worker + (employer if fund.employer_contribution or (fund.manager == "Allianz INSIEME" and extra_for_allianz) else 0.0)
            row[f"Montante {fund.name}"] = balances[fund.name]
            row[f"Rendimento {fund.name}"] = _annual_rate(year, fund, fund.expected_return * scenario_factor)
        rows.append(row)
    return pd.DataFrame(rows)


def estimated_annuity(capital: float, divisor_years: float) -> float:
    """Rendita annua lorda semplificata, non attuariale."""
    return capital / divisor_years if divisor_years > 0 else 0.0
