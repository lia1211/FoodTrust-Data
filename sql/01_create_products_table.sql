-- FoodTrust runtime database: products table (SQLite)
-- Creates an empty products table with the deployed schema.
-- Usage: sqlite3 products.db < 01_create_products_table.sql

DROP TABLE IF EXISTS products;
CREATE TABLE products (
        code TEXT PRIMARY KEY,
        name TEXT,
        brand TEXT,
        quantity TEXT,
        product_quantity REAL,
        product_quantity_unit TEXT,
        serving_size TEXT,
        serving_quantity TEXT,
        categories_tags TEXT,
        countries_tags TEXT,
        brand_tags TEXT,
        image_url TEXT,
        lang TEXT,
        last_modified_t INTEGER,
        last_modified_date TEXT,
        energy_kcal_100g REAL,
        energy_kj_100g REAL,
        protein_100g REAL,
        fat_100g REAL,
        saturated_fat_100g REAL,
        carbohydrates_100g REAL,
        sugars_100g REAL,
        fiber_100g REAL,
        sodium_mg_100g REAL,
        sodium_source TEXT,
        nutrition_data_per TEXT,
        ingredients_text TEXT,
        ingredients_tags TEXT,
        additives_tags TEXT,
        allergens_tags TEXT,
        labels_tags TEXT,
        food_groups_tags TEXT,
        minerals_tags TEXT,
        vitamins_tags TEXT,
        nutriscore_grade TEXT,
        nova_group INTEGER
    , brands TEXT);
