"""Caricamento e normalizzazione dell'estratto contributivo INPS."""
from pathlib import Path
import pandas as pd


NUMERIC_COLUMNS = [
    "Retribuzione/Reddito",
    "Aliquota di computo (%)",
    "Contribuzione nell'anno",
    "Montante Contributivo",
]


def parse_italian_number(value: object) -> float:
    """Converte importi/percentuali italiane in float."""
    if pd.isna(value):
        return 0.0
    text = str(value).strip().replace("€", "").replace(" ", "")
    text = text.replace(".", "").replace(",", ".")
    try:
        return float(text)
    except ValueError as exc:
        raise ValueError(f"Valore numerico non valido: {value!r}") from exc


def load_contributions(csv_path: str | Path) -> pd.DataFrame:
    """Carica il CSV, valida le colonne e ordina gli anni."""
    path = Path(csv_path)
    if not path.exists():
        raise FileNotFoundError(f"File CSV non trovato: {path}")

    frame = pd.read_csv(path, dtype=str)
    required = {"Descrizione", "Anno", *NUMERIC_COLUMNS}
    missing = required.difference(frame.columns)
    if missing:
        raise ValueError(f"Colonne mancanti nel CSV: {', '.join(sorted(missing))}")

    frame["Anno"] = pd.to_numeric(frame["Anno"], errors="raise").astype(int)
    for column in NUMERIC_COLUMNS:
        frame[column] = frame[column].map(parse_italian_number)
    frame = frame.sort_values("Anno").reset_index(drop=True)
    if frame["Anno"].duplicated().any():
        raise ValueError("Il CSV contiene più righe per lo stesso anno.")
    return frame
