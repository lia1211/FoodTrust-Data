# 1.3.2 SQL Script for Database

FoodTrust uses one runtime database: **`product_data/products.db`** (SQLite, read-only at runtime).
It contains one table, `products`, with **6920 packaged infant and toddler food products** from Open Food Facts.
The scripts below were generated from the deployed `products.db` on the `main` branch.

| File | Purpose |
|---|---|
| `01_create_products_table.sql` | Creates the empty `products` table with the deployed schema |
| `02_products_full_dump.sql` | Recreates the table and inserts all 6920 rows (complete rebuild) |
| `03_validation_queries.sql` | Row count and data-quality checks to run after a rebuild |

## Rebuild the database

```bash
sqlite3 products.db < 02_products_full_dump.sql
sqlite3 products.db < 03_validation_queries.sql
cp products.db <repo>/product_data/products.db
```

## Notes
- `code` (barcode) is the primary key.
- Nutrient columns are per 100 g / 100 mL; sodium is stored in mg (`sodium_mg_100g`), with `sodium_source` recording whether it was measured or derived from salt.
- List-type columns (e.g. `categories_tags`, `allergens_tags`, `labels_tags`) are stored as JSON array text; empty values are stored as NULL.
- `brands` duplicates `brand` and is kept for compatibility with the API.
- To regenerate the data itself from Open Food Facts, see `1.3.1 Data pre-processing`.
