-- Quick checks after rebuilding products.db
-- Usage: sqlite3 products.db < 03_validation_queries.sql

SELECT COUNT(*) AS total_products FROM products;              -- expected: 6920
SELECT COUNT(*) AS missing_name_and_brand FROM products
 WHERE (name IS NULL OR name = '') AND (brand IS NULL OR brand = '');   -- expected: 0
SELECT COUNT(*) AS zero_product_quantity FROM products WHERE product_quantity = 0;  -- expected: 0
SELECT sodium_source, COUNT(*) FROM products GROUP BY sodium_source;
SELECT COUNT(energy_kcal_100g) AS with_energy, COUNT(sugars_100g) AS with_sugars,
       COUNT(sodium_mg_100g) AS with_sodium, COUNT(fiber_100g) AS with_fibre FROM products;
