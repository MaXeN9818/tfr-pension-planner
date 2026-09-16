# Calcolatore TFR e previdenza complementare

Dashboard Streamlit per confrontare, in modo indicativo, l'accumulo del TFR lasciato in azienda con quello destinato a fondi pensione. La simulazione mostra anche il montante contributivo INPS riportato nel CSV.

> **Attenzione:** questo progetto è uno strumento dimostrativo. Non produce una proiezione ufficiale COVIP, INPS o del fondo pensione e non sostituisce la Nota Informativa, il Documento sulle rendite o una consulenza professionale.

## Requisiti

- Python 3.10 o superiore
- `pip`

Le dipendenze sono elencate in `requirements.txt`: Streamlit, pandas, Plotly e openpyxl.

## Installazione e avvio

Dalla cartella del progetto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m streamlit run app.py
```

Streamlit aprirà la dashboard nel browser, normalmente all'indirizzo `http://localhost:8501`.

Su Windows, per attivare l'ambiente virtuale usare:

```powershell
.venv\Scripts\Activate.ps1
```

## Utilizzo

1. Scegli nella barra laterale l'anno di inizio e l'anno di pensionamento.
2. Imposta la percentuale di TFR destinata al fondo, il contributo del lavoratore e quello del datore di lavoro.
3. Seleziona lo scenario prospettico: pessimistico, base od ottimistico.
4. Scegli il metodo di costo, l'eventuale opzione Life Cycle e il divisore usato per la rendita indicativa.
5. Seleziona uno o più piani pensionistici e, se necessario, modifica i parametri del piano nell'espansore di configurazione.
6. Consulta metriche, grafico e dettaglio annuale.
7. Usa i pulsanti finali per scaricare il risultato in CSV o Excel.

La rendita visualizzata è una divisione semplificata del capitale per il divisore scelto, predefinito a 20 anni. Non è un coefficiente attuariale ufficiale.

## Dati

Il file utilizzato dall'app è:

```text
estratto_conto_contributivo.csv
```

Il file deve contenere queste colonne:

- `Descrizione`
- `Anno`
- `Retribuzione/Reddito`
- `Aliquota di computo (%)`
- `Contribuzione nell'anno`
- `Montante Contributivo`

Gli importi possono usare il formato italiano, per esempio `€ 27.012,21` o `33,00`. Gli anni devono essere unici e numerici.

Il CSV presente nel progetto è dimostrativo. Gli anni successivi al 2025 sono stime basate sul profilo di crescita osservato nei dati reali disponibili, non dati ufficiali futuri. Il file `data_private/estratto_conto_contributivo.csv` contiene dati separati e non viene caricato automaticamente dall'app.

### Prompt per convertire un estratto INPS in CSV

È possibile fornire a un LLM il testo copiato dalla simulazione pensione INPS e usare un prompt come questo. Sostituisci il contenuto tra parentesi con i tuoi dati; non inserire nel prompt l'esempio seguente come se fosse un dato reale.

```text
Devi convertire i dati che ti fornirò da un estratto della simulazione pensione INPS in un CSV compatibile con un'applicazione Python.

Obiettivo:
- estrarre una riga per ogni anno;
- mantenere separati gli anni storici/reali dagli anni simulati, usando la descrizione presente nei dati oppure "Lavoratori dipendenti" se non è indicata;
- ordinare le righe per anno crescente;
- usare esattamente queste colonne e questo ordine:
	Descrizione,Anno,Retribuzione/Reddito,Aliquota di computo (%),Contribuzione nell'anno,Montante Contributivo

Regole:
1. Non inventare gli anni storici, le retribuzioni, le aliquote o i montanti che ti fornisco.
2. Mantieni il formato italiano per gli importi: "€ 12.345,67". Per l'aliquota usa, per esempio, "33,00" senza il simbolo percentuale.
3. Se un valore è assente o illeggibile, fermati e chiedimi di correggerlo: non stimarlo senza autorizzazione.
4. Verifica che "Contribuzione nell'anno" sia coerente con retribuzione e aliquota, salvo differenze già presenti nella fonte.
5. Verifica che il "Montante Contributivo" sia cumulativo e che ogni anno parta dal montante dell'anno precedente.
6. Se ti chiedo di aggiungere anni simulati, usa una descrizione chiaramente distinguibile, per esempio "Lavoratori dipendenti - simulato", e applica solo le ipotesi che ti indicherò. Non confondere mai le stime con i dati storici.
7. Restituisci prima un breve riepilogo delle ipotesi e poi esclusivamente il CSV racchiuso in un blocco di codice csv, senza testo aggiuntivo dentro il blocco.

Dati da convertire:
[INCOLLA QUI L'ESTRATTO INPS]

Eventuali ipotesi autorizzate per gli anni simulati:
[INSERISCI QUI CRESCITA RETRIBUZIONE, ALIQUOTA, ANNI DA AGGIUNGERE E ALTRE IPOTESI]
```

Esempio inventato di formato atteso, non basato su dati personali reali:

```csv
Descrizione,Anno,Retribuzione/Reddito,Aliquota di computo (%),Contribuzione nell'anno,Montante Contributivo
Lavoratori dipendenti,2022,"€ 18.500,00","33,00","€ 6.105,00","€ 6.105,00"
Lavoratori dipendenti,2023,"€ 19.055,00","33,00","€ 6.288,15","€ 12.393,15"
Lavoratori dipendenti - simulato,2024,"€ 19.626,65","33,00","€ 6.476,79","€ 18.869,94"
```

## Logica della simulazione

- Il TFR annuale è calcolato come retribuzione moltiplicata per la percentuale configurata.
- I contributi del lavoratore e del datore sono calcolati sulla retribuzione del CSV.
- I montanti dei fondi vengono aggiornati annualmente con contributi, rendimento e costo proxy.
- I rendimenti storici configurati per 2024 e 2025 vengono usati per quegli anni; gli anni successivi usano il rendimento prospettico scelto e lo scenario.
- Il montante INPS viene letto dal campo `Montante Contributivo` e non viene sommato ai montanti dei fondi.
- I piani, i rendimenti, i costi e le asset allocation sono configurati in `config.json`.

## Struttura principale

```text
app.py                              Dashboard Streamlit
simulation.py                       Motore di simulazione
charts.py                           Grafico Plotly
data_loader.py                     Lettura e normalizzazione del CSV
config.json                         Parametri dei fondi e default
estratto_conto_contributivo.csv     Dati dimostrativi usati dall'app
requirements.txt                    Dipendenze Python
```
