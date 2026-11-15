# FoodTrust-Data

**Data pipeline & SQLite databases behind FoodTrust, a nutrition-claim checker for baby food**

*Monash University · FIT5120 Industry Experience (team capstone) · 2026*

FoodTrust helps Australian parents check whether a nutrition or health claim on a
baby/toddler food package (e.g. *"no added sugar"*) actually matches the product's
real nutrition data and Australian food-standards law.

This repo contains the **data layer** of FoodTrust: the pipeline that turns raw open
data and official regulatory PDFs into the structured databases the product runs on,
plus the databases themselves.

## My role

This is my contribution as the **data role** on a 6-person cross-functional team
(Data Science, AI, Business Information Systems, IT, Computer Science) building
FoodTrust as our Monash FIT5120 Industry Experience capstone project. I owned the
product database (Open Food Facts → SQLite), the reference-value and claim-rule
databases, and the regulatory evidence pipeline feeding the team's RAG backend.

## What's in here

```
data_pipeline/      Notebooks + scripts that build every database from raw sources
sql/                 SQL to recreate the runtime products table from scratch
databases/           The actual SQLite databases (open with any SQLite client)
docs/                 Full schema + data-lineage documentation
```

- **`data_pipeline/1_product_data`** — Open Food Facts (13GB raw Parquet export) →
  `products.db`: EDA, field selection, unit normalisation, cleaning. Ends with
  6,920 packaged infant/toddler food products.
- **`data_pipeline/2_rag_evidence_corpus`** — turns official regulatory PDFs (FSANZ,
  WHO, NHMRC) into a chunked evidence corpus for the team's retrieval-augmented
  generation backend. Source list with official government URLs in `sources.json`.
- **`data_pipeline/3_iteration1_reference_databases`** — first-pass structured
  reference databases (nutrition reference intakes, WHO category thresholds, claim
  rules). Kept for traceability; the live backend now pulls evidence from the PDFs
  directly via the RAG corpus above.
- **`sql/`** — DDL + full data dump to rebuild `products.db` from scratch, plus
  validation queries.
- **`databases/`** — the five SQLite databases this pipeline produces, ready to
  open and query.
- **`docs/DATABASE_GUIDE.md`** — the full guide: exact schema for every database,
  how they join to each other, data-quality caveats, and what's still unfinished.
  **Read this first if you want the real detail.**

## Tech stack

Python (pandas, pdfplumber), SQL/SQLite, Jupyter.

## Note on data

The two raw source files this pipeline starts from (`food.parquet`, ~7.3GB, and
`en.openfoodfacts.org.products.csv`, ~13GB) are intentionally not included here —
they're the public [Open Food Facts](https://world.openfoodfacts.org/data) export
(ODbL license), too large for a repo. The official regulatory PDFs referenced in
`data_pipeline/2_rag_evidence_corpus/sources.json` are left out for the same reason
(size) and because they're linked there by official government URL. Everything this
pipeline *produces* — the five databases — is included in `databases/`.
