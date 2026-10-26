# 1.3.1 Data Pre-processing

This folder contains the code used to turn raw open data into the data FoodTrust uses.
Full step-by-step detail is in the Data Management Plan.

## 1_product_data — Open Food Facts → `products.db` (used at runtime)
| File | Purpose |
|---|---|
| `01_EDA_food_parquet.ipynb` | Exploratory analysis of the Open Food Facts Parquet export (scale, missing values, tag fields, category filter validation) |
| `field_review_*.csv` | Review of all raw fields: kept for product info, kept for nutrition, or not used |
| `02_build_product_database.ipynb` | Builds `products.db`: filters `en:baby-foods`, selects and renames fields, converts sodium to mg, selects the front image, cleans HTML from ingredients, stores empty values as NULL, removes obsolete products and rows with no name and no brand |

Input: Open Food Facts `food.parquet` (https://world.openfoodfacts.org/data, ODbL).
Output: `products.db`, table `products` (6920 rows). SQL scripts are in `1.3.2`.

## 2_rag_evidence_corpus — official PDFs → `corpus.jsonl` (used at runtime)
| File | Purpose |
|---|---|
| `sources.json` | List of official source documents (FSANZ, WHO, NHMRC, ANZ NRV) with metadata |
| `corpus.py` | Extracts PDF text with pdfplumber, splits it into overlapping chunks and writes `backend/rag_index/corpus.jsonl` |
| `__main__.py` | Command-line entry point |

Run from `backend/`: `python -m app.rag ingest`

## 3_iteration1_reference_databases — not used at runtime
Notebooks that built the Iteration 1 structured reference databases (`reference_values.db`, `who_nppm_thresholds.db`, `claim_rules.db`, `product_nppm_category_mapping.db`).
From Iteration 2 the backend retrieves evidence directly from the official PDFs instead; these are kept for traceability and possible future use.
