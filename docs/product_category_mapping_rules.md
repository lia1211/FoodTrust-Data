# Product → WHO NPPM Category Mapping — Rules Summary

_Companion document to `build_category_mapping.ipynb` and `product_nppm_category_mapping.db` in this folder. This file is the quick-read version — the notebook has the full executable code and is the source of truth if this summary and the code ever disagree._

## What this is for

Epic 3's US3.1 comparison cards need to know which of WHO NPPM 2022's 13 product subcategories a given product belongs to, so they can pick the right threshold row from `who_nppm_thresholds.db` (in `reference_value/`). `products.db` has no such column — this mapping was built to fill that gap, using Open Food Facts' `categories_tags` and product `name` fields as input.

**This is a first-pass, rule-based classifier, not a finished answer.** It was built and tested against the real 7036 products in `products.db`, and the actual results below (not estimates) show real limits — read the whole document before wiring this into anything user-facing.

## Real results from running this against all 7036 products

| category_code | count | % | meaning |
|---|---|---|---|
| unclassified | 2961 | 42.1% | no rule matched — see "Known gaps" below |
| out_of_scope | 1411 | 20.1% | infant formula / growth milk — not covered by WHO NPPM at all (see below) |
| 4.1 | 721 | 10.2% | savoury meal, no protein/cheese named |
| 3.1 | 621 | 8.8% | fruit-containing product |
| 1 | 356 | 5.1% | dry cereal/starch |
| 4.3 | 326 | 4.6% | savoury meal, protein named but not first |
| 5.2 | 233 | 3.3% | dry/semi-dry snack |
| 2 | 177 | 2.5% | dairy dessert |
| 8 | 158 | 2.2% | drink (excluded from promotion) |
| 4.4 | 23 | 0.3% | savoury meal, protein named first |
| 3.2 | 22 | 0.3% | vegetable-only product |
| 6 | 11 | 0.2% | ingredient |
| 7 | 10 | 0.1% | confectionery (excluded from promotion) |
| 4.2 | 6 | 0.1% | savoury meal, cheese named, no other protein |

Confidence breakdown: 2114 high, 1950 medium, 11 low, 2961 none (= unclassified).

**42% unclassified is a real, large number — not a rounding error.** It means categories_tags/labels_tags genuinely did not contain any tag this rule set recognized for those products. Before this feeds anything user-facing, someone should look at a sample of the unclassified rows (query `product_nppm_category_mapping.db` for `category_code='unclassified'`, join against `products.name`) and decide whether more tag rules would catch them, or whether they genuinely fall outside all 13 categories (e.g. multi-item variety packs, which do not fit any single category cleanly).

## The most important structural finding: infant formula is out of scope, not "category 8"

`en:baby-milks`, `en:infant-formulas`, `en:growth-milks` and related tags (1411 products, 20% of the dataset) were deliberately routed to `out_of_scope`, not to category 8 (Drinks). WHO NPPM's own Table 1 text excludes "breastmilk substitutes or unsweetened milk/milk alternatives" even from its own Drinks category — infant formula is regulated under a separate WHO framework entirely (the Code of Marketing of Breast-Milk Substitutes). Do not force these into category 8's sodium/sugar/fat thresholds; they need a "not applicable" state in the UI, not a red/green verdict.

## Rule priority order (checked in this order, first match wins)

1. **Out of scope** — formula/growth-milk tags (`en:baby-milks`, `en:infant-formulas`, `en:growth-milks`, etc.)
2. **3.1 puree exception** — `en:compotes-to-drink` / `en:smoothies` / `en:fruit-smoothies`: WHO explicitly excludes purees from Drinks regardless of drinkable format, so these go to 3.1, not 8
3. **8 Drinks** (excluded) — `en:beverages`, `en:baby-drinks`, `en:fruit-juices`, etc.
4. **7 Confectionery** (excluded) — narrowly, only `en:chocolate-desserts` / `en:cocoa-and-its-products`
5. **4.1-4.5 Savoury meals** — any of a broad tag set (`en:main-meals-for-babies`, `en:meat-menus-for-babies`, any tag containing `vegetable-dish-for-bab`, etc.), then sub-classified by scanning the product `name` for a small multi-language (EN/FR/NL/DE) protein or cheese keyword list:
   - protein keyword found in the first two words of the name -> **4.4**
   - protein keyword found elsewhere -> **4.3**
   - cheese keyword found, no protein keyword -> **4.2**
   - neither found -> **4.1**
6. **3.1 fruit-tagged dairy dessert** — dairy tag + fruit-variant tag together (e.g. `en:fruit-yogurts`) -> defaults to 3.1, since WHO's real rule (>5% fruit) needs a percentage the tags cannot supply
7. **2 Dairy dessert** — plain dairy tag with no fruit-variant tag
8. **3.1 Fruit-containing** — `en:compotes`, `en:apple-compotes`, `en:fruits-based-foods`, etc.
9. **3.2 Vegetable-only** — `en:mashed-vegetables`, `en:vegetables-based-foods`, etc. (only reached if nothing above matched — but see the known gap below, this ordering is not perfect)
10. **5.2 Dry/semi-dry snack** — `en:biscuits-for-babies`, `en:cereal-bars`, etc.
11. **6 Ingredients** — `en:seeds`, `en:spreads`, `en:cheeses`, etc.
12. **1 Dry cereal/starch** — `en:cereals-for-babies`, `en:breakfast-cereals`, `en:cereal-flours`, etc.
13. Nothing matched -> **unclassified**

## Known gaps and judgment calls (confirmed by inspecting real sample output, not theoretical)

- **Category 4.3 vs 4.4 depends on word order in the product name**, approximated with a short EN/FR/NL/DE keyword list. This will misfire on names using words outside the list, or on languages beyond these four. Every 4.3/4.4 result is `medium` confidence, never certain.
- **Category 4.5 (protein is the ONLY named food) is not auto-detected at all.** A real example surfaced in the sample check: the product named simply **"Le poulet"** ("The chicken") was classified as 4.4 by this rule set, but by WHO's own definition this is almost certainly 4.5 (protein is the only named food, nothing else). This is a concrete, confirmed miss, not a hypothetical one -- flagging it here so it is not missed.
- **A real vegetable/savoury-meal boundary miss was also found in the sample check**: a product named "cauliflower, ham, pasta, parmesan (organic, from 12 months)" was classified as 3.2 (vegetable-only) even though it clearly contains ham and pasta -- its `categories_tags` did not contain any of the savoury-meal tags this rule set recognizes, so it fell through to a generic vegetable tag instead. This is exactly the kind of case a stratified spot-check (see below) would catch.
- **Category 5.1 (fruit snacks, e.g. dried fruit pieces) has no matching OFF tag anywhere in this dataset** — the rule set has zero rows routed there. Would need a name/ingredients keyword search to populate, not attempted here.
- **Category 2 vs 3.1** genuinely depends on an exact fruit percentage (WHO's own "<=5%" rule) that no OFF tag captures — the default (fruit-tagged dairy -> 3.1) is a judgment call, not a measurement.
- **Chocolate-coated snacks** (`en:chocolate-biscuits`) were kept in 5.2, not routed to Confectionery (7) — arguable either way, flagged rather than hidden.

## Recommended before this goes anywhere user-facing

Pull a stratified random sample across `medium`/`low`/`unclassified` rows (the same spot-check method already used to validate the `en:baby-foods` product filter earlier in this project — see `products.db`'s own build notebook) and hand-correct or refine the rule set from what that sample shows. The two concrete misses found above (the "Le poulet" 4.5 case and the "ham/pasta" 3.2 case) are proof this is needed, not just a theoretical caveat.

## Files in this folder related to this mapping

- `product_nppm_category_mapping.db` — the actual output table (`code`, `category_code`, `confidence`, `match_reason`), one row per product in `products.db`
- `build_category_mapping.ipynb` — the executable notebook: full rule-set code, real captured output (the counts above came from its own run), and this same explanation in markdown cells
- `products.db` / `who_nppm_thresholds.db` (the latter in `../reference_value/`) — the two tables this mapping connects
