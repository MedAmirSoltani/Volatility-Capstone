<div align="center">

<img src="https://img.shields.io/badge/data-15min%20Forex%20MT5-00897B?style=for-the-badge"/>
<img src="https://img.shields.io/badge/models-GARCH%20vs%20XGBoost-00897B?style=for-the-badge"/>
<img src="https://img.shields.io/badge/horizon-4%20hours-00897B?style=for-the-badge"/>
<img src="https://img.shields.io/badge/app-Django-00897B?style=for-the-badge&logo=django&logoColor=white"/>

# 📈 Forex Volatility Forecasting
### GARCH vs XGBoost — 15-Minute High-Frequency Data

> *Can a machine learning model beat a 40-year-old econometric standard?*
> *Short answer: yes — by half.*

</div>

---

## 📖 Overview

Short-term volatility forecasting on Forex 15-minute interval data from **MetaTrader 5 (MT5)**, spanning **October 2002 to October 2022** (20 years). Two approaches are compared head-to-head:

- **GARCH(1,1)** with GED distribution — the econometric baseline
- **XGBoost** with engineered temporal + autoregressive features — the ML challenger

The study demonstrates that XGBoost **reduces MAPE by ~50%** over GARCH on out-of-sample predictions, while GARCH remains competitive and interpretable for baseline volatility modeling.

---

## 📊 Dataset

| | |
|---|---|
| **Source** | MetaTrader 5 (MT5) — `forexdata.csv` |
| **Period** | October 29, 2002 → October 25, 2022 |
| **Granularity** | 15-minute intervals |
| **Intervals/day** | 96 (24h × 4) |
| **Target** | Short-term rolling volatility (4-hour horizon = 16 intervals) |
| **Feature used** | `close` price → percentage returns |

> 74 zero-return intervals removed (market closed days — data artifact).

---

## 🧠 Methodology

### Volatility Measurement
Returns computed as percentage change of `close` prices. Annualized volatility scaled via:

```
vol_daily   = √96  × vol_15min
vol_monthly = √(96 × 21) × vol_15min
vol_yearly  = √(96 × 252) × vol_15min
```

Rolling volatility window: **16 intervals (4 hours)** — used as ground truth for evaluation.

---

### Model 1 — GARCH(1,1) with GED

- Grid search over `p, q ∈ [1,5]` → optimal: **GARCH(1,1)**
- Distribution: **Generalized Error Distribution (GED)** for heavy tails
- Rolling forecast: trained on expanding window, predicts next 16 intervals (4h)
- PACF of squared returns confirms positive autocorrelation → volatility clustering validated

### Model 2 — XGBoost

**Feature engineering from timestamp:**
`dayofweek`, `quarter`, `month`, `year`, `dayofyear`, `dayofmonth`, `hour`, `minute`

**Autoregressive features:**
`prev1`, `prev2`, `prev3`, `prev4` — lagged close prices (captures momentum)

**Feature selection:** importance threshold ≥ 250 (XGBoost weight-based) to keep only significant predictors.

**Training:**
- `n_estimators=1000`, `early_stopping_rounds=50`
- Eval set: `[(X_train, y_train), (X_test, y_test)]`
- Model serialized to `xgboost_model.pkl`

---

## 📉 Results

| Model | MAPE Train | MAPE Test |
|---|---|---|
| **GARCH(1,1)** | — | ~8–9% |
| **XGBoost** | low | **~4.43%** |

> XGBoost reduces out-of-sample MAPE by approximately **half** compared to GARCH.

Key insight from the notebook:
> *"The GARCH model can effectively predict rolling volatility of Forex. However, XGBoost improves upon this — MAPE reduced by half to 4.43%. This underscores the importance of combining ML with domain knowledge of financial time series."*

---

## 🛠️ Stack

| Layer | Tool |
|---|---|
| Data | MT5 CSV export |
| Processing | Pandas, NumPy |
| Statistical model | `arch` library — GARCH |
| ML model | XGBoost |
| Evaluation | Scikit-learn (RMSE, MAPE) |
| Visualization | Plotly, Matplotlib, Seaborn |
| Web app | Django (`/app`) |

---

## 🚀 Getting Started

```bash
git clone https://github.com/YOUR_USERNAME/forex-volatility-forecasting.git
cd forex-volatility-forecasting

pip install -r requirements.txt
```

### Run the notebook
```bash
jupyter notebook final_notebook.ipynb
```

> Place `forexdata.csv` (MT5 export, tab-delimited) in the root directory before running.

### Run the Django app
```bash
cd app
python manage.py migrate
python manage.py runserver
```

The app loads `xgboost_model.pkl` to serve live volatility predictions.

---

## 👤 Author

**Amir Soltani** — Data Science & NLP  
Master's student · Alternance @ Benman Partners  
ESPRIT · PST&B · UTT Mastère Spécialisé 2026

[![LinkedIn](https://img.shields.io/badge/LinkedIn-Connect-0A66C2?style=flat&logo=linkedin)](https://linkedin.com/in/YOUR_PROFILE)

---

<div align="center">
<sub>Academic research project · High-frequency financial time series · GARCH vs ML</sub>
</div>
