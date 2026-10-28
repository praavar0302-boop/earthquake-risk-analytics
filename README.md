Earthquake Risk Analytics

Regional Earthquake Probability Forecasting & Illustrative Insurance Pricing

A Data Analytics research project investigating whether historical earthquake activity can help estimate the annual probability of a strong earthquake in a geographical region.

Using 60 years of USGS earthquake data, we explore seismic patterns, develop and compare statistical and machine-learning models, and demonstrate how predicted probabilities can inform illustrative risk-based insurance pricing.

The project includes an interactive Streamlit application that walks through the complete analytical process.



Research Objective

Can a region's historical earthquake activity help estimate the probability of at least one magnitude 6.0 or higher earthquake occurring in the following year?

The analysis focuses on three questions:

What geographical and historical patterns can be identified in earthquake activity?

Do machine-learning models outperform simpler historical-frequency approaches?

How can regional earthquake probabilities be translated into illustrative insurance premiums?

The objective is to estimate annual regional occurrence probabilities, not exact earthquake dates, precise city-level hazards, or property damage.

Dataset

The project uses historical earthquake records from the United States Geological Survey (USGS).

| Attribute | Details |
|---|---|
| Source | USGS Earthquake Catalogue |
| Period | 1965–2025 |
| Total recorded events | 28,557 |
| Minimum recorded magnitude | 5.5 |
| Prediction target | At least one M ≥ 6.0 earthquake per region-year |
| Geographical aggregation | 5° × 5° latitude–longitude grid |
| Modelled regions | 722 |
| Region-year observations | 36,822 |
| Evaluation period | 2016–2025 |

Records include earthquake magnitude, depth, geographical coordinates, timestamps and related metadata.

Methodology

| Stage | Method | Objective |
|---|---|---|
| 1. Data Preparation | Cleaning, validation and preprocessing | Prepare consistent earthquake records |
| 2. Exploratory Analysis | Statistical summaries, distributions and maps | Identify seismic patterns and data limitations |
| 3. Feature Engineering | Regional aggregation and historical activity features | Convert historical observations into model inputs |
| 4. Predictive Modelling | Logistic, Cloglog, Random Forest, CART and historical baseline | Estimate annual regional earthquake probabilities |
| 5. Model Evaluation | ROC-AUC, Brier Score, calibration and rolling-origin evaluation | Assess predictive performance and reliability |
| 6. Insurance Illustration | Expected payout and target loss ratio | Demonstrate illustrative risk-based pricing |

Above mentioned stages are described below in detail:

1. Data Collection & Preparation

Earthquake records are collected, inspected for missing or inconsistent values, and cleaned for analysis.

2. Exploratory Data Analysis

Magnitude distributions, earthquake depths, annual activity, geographical concentration and measurement differences are examined to understand historical patterns.

3. Regional Aggregation & Feature Engineering

Earthquakes are grouped into geographical regions. Historical features include recent earthquake counts, maximum recorded magnitudes, time since a strong earthquake and long-term activity rates.

4. Predictive Modelling

Five approaches are compared:

a. Historical-frequency baseline

b. Logistic Regression

c. Complementary Log-Log Regression

d. Random Forest

e. Classification and Regression Tree (CART)

5. Model Evaluation

Performance is assessed using chronological evaluation, ROC-AUC, Brier Score, calibration analysis and exploratory rolling-origin comparisons.

6. Insurance Pricing Illustration

Predicted probabilities are converted into expected fixed payouts and illustrative premiums using explicit pricing assumptions.

Model Performance

Results from the 2016–2025 exploratory evaluation:

| Model | ROC-AUC ↑ | Brier Score ↓ |
|---|---:|---:|
| Random Forest | **0.8922** | **0.06383** |
| Historical-frequency baseline | 0.8896 | 0.06445 |
| CART | 0.8881 | 0.06503 |
| Logistic Regression | 0.8821 | 0.06487 |
| Complementary Log-Log | 0.8788 | 0.06522 |
| Constant-probability baseline | 0.5000 | 0.09453 |

Key Findings

Random Forest achieved the strongest overall performance, with ROC-AUC of 0.8922 and Brier Score of 0.06383.

Historical earthquake frequency proved highly competitive. Random Forest reduced its Brier Score by only approximately 0.96% relative to the historical-rate baseline.

Model complexity did not guarantee substantial improvements. The historical-frequency baseline outperformed several more sophisticated models.

Probability calibration remains imperfect. Good discrimination does not necessarily translate into accurate probabilities.

Regional risk-based pricing is a useful analytical illustration, but does not establish commercially valid insurance premiums.

The central finding is that historical regional earthquake activity captures much of the predictive signal, while additional model complexity provides relatively limited improvement.

Interactive Streamlit Application

The accompanying Streamlit application provides a guided research walkthrough, from the research question and dataset to modelling results and insurance pricing.

Features include:

Step-by-step navigation through the research workflow

Interactive earthquake data exploration

Geographical visualizations and regional-grid explanations

Model performance and calibration comparisons

Regional earthquake probability forecasts

Illustrative insurance-premium calculator

Explanations of findings, assumptions and limitations

Run Locally

Python 3.13 is recommended for the tested environment.

git clone <YOUR_REPOSITORY_URL>
cd earthquake-risk-analytics

python -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt
streamlit run streamlit_app.py

On Windows PowerShell, use .venv\Scripts\Activate.ps1 instead of the source command.

See Streamlit Documentation for further instructions.

Project Structure

earthquake-risk-analytics/
├── earthquake_risk_analysis.ipynb       # Research notebook
├── streamlit_app.py             # Interactive walkthrough
├── app_support.py               # Streamlit utilities
├── app_assets/                  # App visualizations and data
├── data/
│   ├── raw/                     # Source earthquake data
│   ├── external/                # Plate-boundary data
│   └── processed/revised/       # Processed results
├── figures/revised/             # Analysis figures
├── scripts/                     # Export and validation tools
├── tests/                       # Application tests
├── requirements.txt             # App dependencies
├── requirements-analysis.txt    # Notebook dependencies
└── README.md

Reproducibility

The research notebook contains the complete analytical workflow, including data preparation, feature engineering, model evaluation, calibration and insurance calculations.

To run the notebook, install the additional analysis dependencies:

pip install -r requirements-analysis.txt

Open earthquake_risk_analysis.ipynb in Jupyter and execute it using the configured Python environment.

The repository includes verified datasets, outputs, figures and reproducibility checks. Refer to the publication documentation and supporting scripts for detailed verification and export procedures.

Limitations

This project is an exploratory academic analysis. Important limitations include:

Evaluation years influenced model development and therefore do not constitute an independent untouched holdout.

Earthquake catalogue revisions and historical measurement differences may affect comparability.

Geographical grid cells cover large areas and cannot represent precise city-level or property-level risk.

Earthquake observations exhibit temporal and spatial dependence.

Rare high-risk events and imperfect calibration introduce uncertainty.

Insurance pricing excludes actual damage, property exposure, vulnerability and other commercial requirements.

Results should be interpreted as regional probability estimates and educational pricing illustrations, not precise earthquake predictions or commercial insurance recommendations.

Data Sources & Attribution

Earthquake records are sourced from the USGS Earthquake Catalog.

Plate-boundary data are used for geographical context. See Third-Party Notices for dataset attribution and licensing information.

Academic Context

Developed as a group project for a university-level Data Analytics course.

The project demonstrates the practical application of exploratory data analysis, feature engineering, statistical modelling, machine learning, model validation, interpretability and risk-based decision-making.