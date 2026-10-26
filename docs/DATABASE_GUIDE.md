# Food Trust — Database Guide

This document describes every database the DS (data) role has built for the Food Trust
project, what each one is for, its exact schema, how the databases connect to each
other, and — just as importantly — what is **not** finished yet. Read the "Status
summary" table first if you only have five minutes.

Food Trust helps Australian parents check whether a nutrition/health claim on a
baby/toddler food package (e.g. "no added sugar") actually matches the product's real
nutrition data and Australian food-standards law. Persona: "Mia", a parent of a child
aged 0-4.

## Folder structure

```
FOODTRUST DATA/
├── product_data/                          Epic 2 + part of Epic 3
│   ├── products.db                        ← the core product database
│   ├── product_nppm_category_mapping.db   ← product → WHO category mapping (NOT VALIDATED)
│   ├── product_category_mapping_rules.md  ← plain-English rules doc for the mapping above
│   ├── build_product_database.ipynb       ← reproducible build for products.db
│   ├── build_category_mapping.ipynb       ← reproducible build for the mapping db
│   ├── en.openfoodfacts.org.products.csv  ← raw source data, 12GB — DO NOT COMMIT
│   ├── food.parquet                       ← raw source data, 7.3GB — DO NOT COMMIT
│   └── build/                             ← intermediate build artefacts — DO NOT COMMIT
├── reference_value/                       Epic 3
│   ├── reference_values.db                ← NHMRC + WHO Sugars per-day reference intakes
│   ├── who_nppm_thresholds.db             ← WHO NPPM per-100kcal category thresholds (powers the comparison cards)
│   ├── build_reference_values.ipynb
│   ├── build_nppm_thresholds.ipynb
│   ├── reference data/                    ← source PDFs
│   └── detail data/                       ← source PDFs
└── claim_data/                            Epic 4
    ├── claim_rules.db                     ← FSANZ claim-eligibility rules + NPSC scoring data
    ├── build_claim_rules.ipynb
    ├── Schedule4_Nutrition_Health_Related_Claims_2026-04-30.pdf
    ├── F2025C00833.pdf                    ← Standard 1.2.7
    ├── F2022C01053.pdf                    ← Schedule 5
    ├── F2024C00903.pdf                    ← Standard 2.9.2
    └── getting-your-claims-right.pdf
```

Every `.db` file is plain SQLite — open with any SQLite client (DB Browser for
SQLite, the VS Code SQLite Viewer extension, Python's `sqlite3`, etc.). Every `.ipynb`
is a real, executed Jupyter notebook: it contains the actual code that built the
matching `.db` file, with its actual captured output, plus markdown cells explaining
every sourcing and design decision — **read the notebook, not just this guide, before
making a change that depends on exactly how a number was derived.**

## Status summary — read this before deploying anything

| Epic | Database | Status | Safe to use as-is? |
|---|---|---|---|
| 1 — Child profile | *(no database — pure UI)* | N/A | N/A |
| 2 — Product Information | `products.db` | **Done** | Yes |
| 3 — Nutrition Comparison | `reference_values.db` | **Done** | Yes, for Epic 6/7 (per-day figures) |
| 3 — Nutrition Comparison | `who_nppm_thresholds.db` | **Done** | Yes, this is what powers the comparison cards |
| 3 — Nutrition Comparison | `product_nppm_category_mapping.db` | **First pass only** | **No — spot-check before wiring into the backend.** 42% of products are `unclassified`; 2 concrete misclassifications already found by manual inspection. See its own section below. |
| 4 — Claim Verification | `claim_rules.db` | **First pass only** | **Data is solid and citeable; the verification *logic* has not been written yet.** See its own section below for exactly what's missing. |

**Nothing here is a working backend API.** All five databases are reference/lookup
data. The actual "compare this product's numbers against this rule and return
Supported/Not Supported" logic still needs to be written by whoever builds the
backend — these databases are the data that logic will query, not a finished service.

---

## 1. `products.db` (Epic 2)

**Location**: `product_data/clean_babyfood/products.db` — SQLite, single table `products`, **6,920
rows**, one row per product. Rebuilt twice on 2026-08-31; see
`clean_babyfood/build_product_database.ipynb` for the full, executed build (both
passes) and the reasoning behind every column decision below.

**What it is**: every Open Food Facts product tagged `en:baby-foods` (and its
children, `en:baby-milks`/`en:infant-formulas` — confirmed no products are missed by
using just the parent tag), minus 116 rows dropped in the second rebuild where both
`name` and `brand` were NULL (a product a user could neither find nor recognize).
Global coverage, not filtered to Australia (OFF's contributor base skews European; a
real AU parent scanning a barcode may not find a match in this table — the app needs
a graceful "not found" path).

**⚠️ Row count changed from 7,036 → 6,920 in the second rebuild.** `product_nppm_category_mapping.db`
(section 2 below) still has 7,036 rows keyed to the *old* `products.db` — it has not
been rebuilt against this version yet, so 116 of its rows now reference barcodes that
no longer exist in `products.db`. Not currently breaking anything (the mapping table
is only ever looked up *from* a `products.db` row, never the other way around), but
it needs a rebuild before anyone relies on `product_nppm_category_mapping.db`'s row
count matching `products.db`'s.

**Columns** (36 total):

| Column | Type / example | Notes |
|---|---|---|
| `code` | text, barcode | Primary key. Join key into `product_nppm_category_mapping.db` (see caveat above). |
| `name` | text | 98.8% coverage (falls back to OFF's `generic_name` when `product_name` is empty). |
| `brand` | text | 95.5% coverage. Renamed from `brands` in the second rebuild. |
| `quantity` | text | 64.5% coverage — OFF's free-text packet size, kept as a display fallback. Can contain unit-less garbage (e.g. `'1'`); prefer `product_quantity`+`product_quantity_unit` for anything computed. |
| `product_quantity` | real (grams/mL) | 62.3% coverage — OFF's structured, unit-normalized packet size. A parsed value of exactly `0` is treated as missing and nulled out (along with its unit) — that's an OFF data artifact, not a real packet weight. |
| `product_quantity_unit` | text | Paired with `product_quantity`; NULL whenever it is. |
| `serving_size` | text | 28.7% coverage — OFF's free-text serving size (e.g. `"4 tbsp (14 g)"`), sparsest identity field. Conceptually distinct from `quantity`: this is *per serving*, `quantity` is the *whole package*. |
| `serving_quantity` | text | 27.7% coverage — structured numeric counterpart to `serving_size`, same free-text-vs-parsed relationship as `quantity`/`product_quantity`. |
| `categories_tags` | JSON array (text) | 100% coverage. OFF category taxonomy tags, kept `en:`-prefixed in storage (matches downstream WHO NPPM / claim-keyword logic); relabel to human-friendly text in the display layer only. |
| `countries_tags` | JSON array (text) | 99.8% coverage. |
| `brand_tags` | JSON array (text) | 95.5% coverage. Renamed from `brands_tags`. Normalized (lowercased) brand name for case-insensitive brand search/dedup. |
| `image_url` | text | 94.9% coverage. Constructed from barcode+imgid, only when OFF's own `images[].key` explicitly marks a front photo (no longer falls back to an arbitrary image). Not spot-checked that URLs actually resolve — `images.openfoodfacts.org` is blocked from the build session, check a sample yourself. |
| `lang` | text | 100% coverage. Product's primary language; only used by the `image_url` build step (prefers a same-language front photo) — not consumed anywhere else. |
| `last_modified_t` | integer | 100% coverage. OFF's last-modified timestamp, Unix epoch seconds. |
| `last_modified_date` | text, ISO 8601 date | 100% coverage. New in the second rebuild — `last_modified_t` pre-converted to a readable date so the frontend's "last updated" field doesn't need to do the conversion itself. |
| `energy_kcal_100g` | real | 76.1% coverage. |
| `energy_kj_100g` | real | 67.1% coverage. Kept alongside `energy_kcal_100g` (not deduplicated) — FSANZ-style labeling conventions typically expect both units shown; whether to actually display both is a compliance call for the team, not a data decision (see `discuss-with-team.md`). |
| `protein_100g`, `fat_100g`, `saturated_fat_100g`, `carbohydrates_100g`, `sugars_100g` | real | 75.4–76.6% coverage each. All 8 core nutrients are read consistently from OFF's `"100g"` sub-field, never `"serving"`. |
| `fiber_100g` | real | 53.4% coverage — sparsest of the 8 core nutrients. |
| `sodium_mg_100g` | real | **In milligrams** (converted from OFF's native grams) — matches `reference_values.db`'s sodium unit on purpose. 66.8% coverage. |
| `sodium_source` | text: `sodium` / `salt_derived` / NULL | Provenance flag, not a redundant column. In this dataset all 4,620 sodium-bearing rows were measured directly (`'sodium'`) — the `salt_derived` (`salt_100g ÷ 2.5 × 1000`) path exists in the code but wasn't triggered by any row this time. |
| `nutrition_data_per` | text | 28.7% coverage. Whether the source nutrient values were declared per-100g or per-serving — a data-quality check field, not necessarily for display. |
| `ingredients_text` | text | 69.9% coverage. Free text; stripped of residual HTML markup (e.g. a stray `<span class="allergen">...</span>`) in the second rebuild. Case is left as-is — lowercasing would lose information (proper nouns, "GMO"-style abbreviations); build a separate lowercase search-index field later if matching needs it. |
| `ingredients_tags` | JSON array (text) | 69.9% coverage. Machine-matchable counterpart to `ingredients_text` (single ingredients as tags) — used for allergen/claim/ingredient matching, not display. Not a duplicate of `ingredients_text`. |
| `additives_tags` | JSON array (text) | 26.8% coverage. E-number food additives (e.g. `en:e322` = lecithin) — configuration transparency data, useful for "what's in this" and future additive-based claim checks. |
| `allergens_tags` | JSON array (text) | 40.1% coverage. Confirmed allergens (distinct from OFF's separate `traces_tags` for "may contain trace amounts," which we don't currently extract — see `discuss-with-team.md`). |
| `labels_tags` | JSON array (text) | 64.9% coverage. **Closest thing to a "claims" field** — see the claim-candidate note under `claim_rules.db` below. Kept `en:`-prefixed in storage for the same reason as `categories_tags`. |
| `food_groups_tags` | JSON array (text) | 76.4% coverage. A *coarser* OFF taxonomy than `categories_tags` (e.g. 2 broad tags vs. 8 fine-grained ones on the same product) — not a duplicate, intended to help reduce the 42% `unclassified` rate in `product_nppm_category_mapping.db`. |
| `minerals_tags`, `vitamins_tags` | JSON array (text) | 21.5% / 30.6% coverage. Forward-looking, for future mineral/vitamin-related features. |
| `nutriscore_grade` | text | 100% non-null, but 6,918 of 6,920 rows are the placeholder string `"not-applicable"` (only 1 `'c'`, 1 `'e'`) — no real discriminative value for this baby-food subset. Kept in the table (cheap to keep), but **should not be surfaced in the frontend** for this dataset. |
| `nova_group` | integer | 65.5% coverage. Food-processing-level classification (1=unprocessed/minimally processed … 4=ultra-processed), with a real, non-degenerate distribution across this subset — unlike `nutriscore_grade`, this one is worth surfacing. |

**Dropped in the second rebuild** (all previously present, all confirmed low-value for
this subset): `manufacturing_places_tags` (10.1% coverage, no backfill source right
now — worth reconsidering if the FSANZ Branded Food Database investigation goes
anywhere), `link` (10.3% coverage), `nucleotides_tags` (2.0% coverage, too sparse to
justify as a forward-looking placeholder).

**Not persisted as columns** (used only during the build, then discarded): `images`
(raw metadata, only needed to compute `image_url`), `obsolete` (used to exclude
discontinued products at build time — 0 excluded this run), `generic_name` (only used
as a fallback into `name`).

**Known limitation**: OFF is crowdsourced — some genuine baby products may be
under-tagged and missing from these 6,920 rows entirely (false negatives, not
fixable from our side).

---

## 2. `product_nppm_category_mapping.db` (Epic 3) — ⚠️ first pass only, not validated

**Location**: `product_data/product_nppm_category_mapping.db` — SQLite, single table
`product_nppm_category_mapping`, **7,036 rows** (was one per `products.db` row when built; **not true anymore** -- `products.db` was rebuilt 2026-08-31 and dropped 116 rows, so 116 barcodes in this table no longer exist in `products.db`. This table has not been rebuilt against the new `products.db` yet -- rebuild it before relying on the row counts matching.

**Columns**: `code` (barcode, joins to `products.db.code`), `category_code` (one of
WHO NPPM's 13 category codes below, or `out_of_scope`, or `unclassified`),
`confidence` (`high` / `medium` / `low` / `none`), `match_reason` (which rule fired).

**What it is**: a rule-based classifier that assigns each product to one of WHO
NPPM 2022's 13 promotion-eligibility categories, so `who_nppm_thresholds.db`'s
per-category thresholds can actually be applied to a real product. Category codes:
`1` dry cereals/starches, `2` dairy foods/desserts/cereals, `3.1` fruit-containing,
`3.2` vegetable-only, `4.1`-`4.5` five savoury-meal subtypes (split by how a protein
source is named in the product name), `5.1` fruit snacks, `5.2` dry/semi-dry
snacks, `6` ingredients. (`7` Confectionery and `8` Drinks also appear but WHO marks
both "not appropriate for promotion" — no numeric thresholds exist for them at all.)

**Real result counts** (not an estimate): `unclassified` 2,961 (42.1%), `out_of_scope`
1,411 (20.1% — infant formula/growth milk, see below), `4.1` 721, `3.1` 621, `1` 356,
`4.3` 326, `5.2` 233, `2` 177, `8` 158, `4.4` 23, `3.2` 22, `6` 11, `7` 10, `4.2` 6.
Confidence: 2,114 high, 1,950 medium, 11 low, 2,961 none.

**Why `out_of_scope` matters**: 1,411 products (infant formula, follow-on formula,
growth milk) are deliberately routed to `out_of_scope`, not to category `8` (Drinks).
WHO NPPM's own text excludes breastmilk substitutes from its scope entirely — these
need a "not applicable" UI state, not a red/green verdict. **`claim_rules.db` also
reuses this exact tag** to auto-fail any nutrition/health claim on formula products
(Standard 1.2.7 bans all such claims outright) — do not duplicate this product list
anywhere else; always look it up here.

**⚠️ Why this is not backend-ready**: 42% of products got no recognized category at
all — this is real, not a bug (`categories_tags` genuinely had no matching tag for
those rows). Manual spot-checking the sample output already found two concrete
misclassifications: a product named only "Le poulet" ("The chicken") was placed in
`4.4` (protein named first) when it is almost certainly `4.5` (protein is the *only*
named food — this build doesn't detect that case); a ham/pasta/parmesan dish was
placed in `3.2` (vegetable-only) purely because its tags didn't match any recognized
savoury-meal tag. **Recommended before use**: a stratified random spot-check across
`medium`/`low`/`unclassified` rows (40-ish products, checked by eye) — the same
method already used to validate the `en:baby-foods` filter on `products.db`. Full
rule list and known judgment calls are in `product_category_mapping_rules.md`.

---

## 3. `reference_values.db` (Epic 3 / 6 / 7)

**Location**: `reference_value/reference_values.db` — SQLite, single table
`reference_values`, **114 rows**.

**What it is**: official per-day nutrient intake references for children 0-4 years,
from NHMRC (Nutrient Reference Values for Australia and New Zealand) and the WHO 2015
sugars guideline. **This is not what powers the product comparison cards** — see
`who_nppm_thresholds.db` below for that. This table answers "how much should my child
eat across a whole day," which is the right basis for Epic 7 (Daily Nutrition
Context) and for citation/sourcing in Epic 6 (Evidence Transparency), not for judging
a single product's per-100g numbers.

**Columns**: `id`, `age_band` (`0-5m`/`6-11m`/`1y`/`2y`/`3y`/`4y`), `age_months`
(only populated for Energy's month-granular rows), `nutrient` (energy / protein /
total_fat / saturated_fat / carbohydrate / dietary_fibre / sodium / sugars), `sex`
(`boys`/`girls`/NULL — only Energy is sex-specific), `pal_level` + `pal_value`
(Physical Activity Level tier, Energy at 3y/4y only — **all 6 tiers are stored, the
app must choose a default to display**), `value_type` (AI/EAR/RDI/UL/EER/WHO sugars
variants/`no_value_established`), `value_min`/`value_max`, `unit`, `basis`
(`per_day_total` or `percent_energy`), `source`, `source_note`.

**Units**: energy `kJ/day` (converted from NHMRC's native MJ/day for the 3y/4y
table so the whole `energy` column is internally consistent), everything else
`g/day` except sodium (`mg/day`, matching `products.db`'s `sodium_mg_100g`) and
sugars (`%energy`, deliberately not converted to g/day — that conversion needs a
specific Energy value chosen first, which is an app-level decision).

**Honest, permanent gaps** (stored as real rows with `value_type='no_value_established'`,
not missing rows — so "checked, no value exists" is queryable): `saturated_fat` has
**zero** reference values at any age (checked three sources); `total_fat` and
`carbohydrate` only have infant-age values; `dietary_fibre` has no infant-age value;
sodium's Upper Level is not established for infants.

---

## 4. `who_nppm_thresholds.db` (Epic 3) — powers the comparison cards

**Location**: `reference_value/who_nppm_thresholds.db` — SQLite, single table
`who_nppm_thresholds`, **86 rows**.

**What it is**: WHO Europe's Nutrient and Promotion Profile Model (NPPM) 2022,
Table 1 — per-100kcal-of-product composition thresholds, broken out by 13 product
categories, for children 6-36 months. **This is the table that actually drives the
green/red "Needs attention" vs "Within reference" verdict on Epic 3's comparison
cards** — it is on the same per-100g/per-100kcal basis as a product's own nutrition
facts, unlike `reference_values.db` above.

**Columns**: `id`, `category_code` (matches `product_nppm_category_mapping.db`'s
`category_code`), `category_name`, `category_description`, `age_label`,
`eligible_for_promotion` (0/1 — `7` Confectionery and `8` Drinks are explicitly
ineligible, all-NULL thresholds), `nutrient` (`energy_density` / `sodium` /
`total_sugar_pct_energy` / `added_sugar` / `total_protein` / `total_fat` /
`fruit_content_pct_weight`), `condition` (`>=`/`<=`/`=`/`not_permitted`/`not_specified`),
`value`, `unit`, `value_note`, `high_sugar_flag_note`, `source`.

**Coverage**: only 5 of the app's 8 core nutrients (no saturated fat, carbohydrate,
or dietary fibre — WHO NPPM's own table doesn't cover them; the comparison card must
show "No reference available" for those 3, permanently, not as a bug). Units are
unified to one per nutrient except `energy_density`, which genuinely has three
source-driven variants (`kcal/100g` for most categories, `kcal/serve` for the two
dry-snack categories, `% added water` for vegetable-only purées) — each flagged in
`value_note`, not silently forced together.

**Depends on**: `product_nppm_category_mapping.db` to know which category a real
product falls into — see the validation warning above before trusting a comparison
card end-to-end.

---

## 5. `claim_rules.db` (Epic 4) — data is solid, verification logic not yet written

**Location**: `claim_data/claim_rules.db` — SQLite, **3 tables**.

**What it is**: Australia's Food Standards Code claim-eligibility rules (Standard
1.2.7 + Schedule 4 + Schedule 5 + Standard 2.9.2), structured so a backend can look
up "is this claim, on this product, actually true" and cite the exact legal
provision. Five source PDFs (in this same folder) were read in full to build it —
see `build_claim_rules.ipynb`'s markdown for the full source breakdown and how the
five documents relate to each other (short version: Standard 1.2.7 is the operative
law with no numbers in it; Schedule 4 holds the numeric tables 1.2.7 points to;
Schedule 5 holds the NPSC score calculation method that Schedule 4's pass/fail line
is checked against; Standard 2.9.2 is a narrower population-specific override for
products that meet its legal definition of "food for infants").

### Table 1: `claim_rules` — 152 rows, one per claim-eligibility rule

| Column | Meaning |
|---|---|
| `claim_category` | `nutrition_content` (76 rows) / `health_general` (52) / `health_high` (11) / `general_restriction` (13, cross-cutting rules like the infant-formula ban) |
| `property` | The nutrient/attribute being claimed, e.g. `sodium`, `protein`, `calcium` — matches `products.db` column names where the nutrient is one of our 8 core ones |
| `descriptor` | The claim word, e.g. `low`, `good_source`, `reduced_light_lite` (Schedule 4's own synonym grouping — not split into 3 duplicate rows) |
| `population_scope` | `general` (142 rows, Schedule 4) or `food_for_infants` (10 rows, Standard 2.9.2 override — **only applies to products that meet 2.9.2's narrow legal definition of "food for infants," which excludes formula, meal replacements, supplementary foods, and unprocessed produce — this is narrower than "any baby/toddler product in our database"**) |
| `rule_type` | `numeric_threshold` (63) / `cross_reference` (41, points to another row's condition) / `compound_condition` (30, an AND of multiple sub-conditions, spelled out in `notes`) / `not_permitted` (7) / `labelling_requirement` (5) / `requires_npsc` (3) / `prohibited_representation` (2) / `requires_accompanying_claim` (1) |
| `condition`, `value`, `value_max`, `unit`, `basis`, `product_form` | The actual numeric test, when `rule_type='numeric_threshold'` |
| `requires_npsc` | 1 if the food must pass the Nutrient Profiling Scoring Criterion before this claim is allowed (all health claims require this) |
| `requires_reference_food` | 1 if this is a comparative claim (reduced/light/increased) needing a named reference product — **we have no reference-food data anywhere; treat these as permanently "cannot verify"** |
| `alt_group` | Rows sharing this value (+ same property/descriptor/population_scope) are OR-alternatives — any one being satisfied is enough (e.g. the 3 paths to a "diet" energy claim) |
| `relevant_population` | e.g. "women of childbearing age", "persons 65+", "children" — for health claims with a restricted target group |
| `health_effect` | The claimed health outcome, for health claims only |
| `excluded_food_types` | Free text list of food types this claim cannot be made about, when relevant |
| `computable_with_current_data` | **0 for 93 of the 152 rows** — these reference a nutrient outside `products.db`'s current 8-nutrient scope (cholesterol, gluten, glycaemic index/load, lactose, individual fatty-acid families, most vitamins/minerals). Kept in the table for legal completeness/citation, but the backend should show "cannot verify — outside current data scope," not attempt a comparison. |
| `notes`, `source`, `source_section` | Full explanatory text and exact legal citation |

### Table 2: `npsc_scoring_reference` — 151 rows, the NPSC score calculator's lookup tables

Schedule 5's step-function tables for computing a product's Nutrient Profiling Score:
`baseline_energy` / `baseline_saturated_fat` / `baseline_sugars` / `baseline_sodium`
(Table 1 for Category 1&2 foods, Table 2 for Category 3), `v_points` (fruit/veg/nut/
legume content, Table 3), `p_points` (protein, Table 4), `f_points` (fibre, Table 5).
Each row is one scoring bracket: `points`, `operator` (`<=`/`>`/`>=`/`=`, exactly as
Schedule 5 states it), `threshold_value`, `threshold_unit`. To score a product on one
component: find the highest-points bracket whose condition the product's actual value
satisfies.

**⚠️ `v_points` cannot currently be computed** — it needs a fruit/veg/nut/legume
percentage-by-weight figure that `products.db` does not have (`categories_tags` only
approximates category membership, not the precise %). Any `requires_npsc` claim is
therefore only partially computable today.

### Table 3: `npsc_category_thresholds` — 3 rows, the pass/fail lines

Category 1 Beverages (score must be `< 1`), Category 2 general food (`< 4`),
Category 3 cheese with >320mg calcium/100g or edible oil/spread/margarine/butter
(`< 28`). **This is a different 3-category system from `product_nppm_category_mapping.db`'s
13 WHO NPPM categories above — do not conflate the two.** No classifier exists yet to
sort real products into these 3 NPSC categories — see "What's still missing" below.

### What's still missing before Epic 4 can run end-to-end

1. **The NPSC Category 1/2/3 classifier** — a small rule (beverage tag → Category 1;
   cheese >320mg calcium/100g or oil/spread/margarine/butter tags → Category 3; else
   Category 2) has not been built yet.
2. **The actual backend verification logic** — this database is reference data only.
   Someone still needs to write the code that: checks `out_of_scope` first (auto-fail);
   determines if the product meets 2.9.2's "food for infants" definition (prefer that
   population_scope's row if so); matches the claim text to a `claim_rules` row;
   pulls the product's real value from `products.db`; compares; returns a verdict with
   citation. A suggested step-by-step flow is written out in `build_claim_rules.ipynb`.
3. **A candidate claims list is already available but not extracted**: `products.db`
   has no dedicated "claims" field (confirmed — neither OFF export format has one),
   but `labels_tags` already contains real claim-like tags for a meaningful share of
   products: `en:no-added-sugar` (960 of 7,036), `en:low-or-no-salt` (230),
   `en:no-added-salt` (186), `en:low-or-no-sugar` (75), plus smaller counts for
   `en:low-salt`/`en:low-sodium`/`en:low-sugar`/`en:reduced-sugar`/`en:no-trans-fat`.
   These are OFF contributors' own tagging, not necessarily verbatim packaging text —
   treat as a starting candidate list for Epic 2's US2.4, not a guaranteed match.

---

## How the databases connect

- `products.db.code` ⟷ `product_nppm_category_mapping.db.code` — same barcode, meant to
  be one row each, but currently isn't: `product_nppm_category_mapping.db` still has 116
  rows for barcodes that no longer exist in `products.db` after the 2026-08-31 rebuild
  (see the caveat in section 2 above) -- rebuild the mapping table before treating the two
  as in sync.
- `product_nppm_category_mapping.db.category_code` ⟷ `who_nppm_thresholds.db.category_code`
  — look up a product's category, then its thresholds.
- `product_nppm_category_mapping.db`'s `out_of_scope` tag is reused directly by the
  claim-verification logic (Epic 4) to auto-fail infant-formula claims — do not
  duplicate this as a separate list anywhere.
- `claim_rules.db.claim_rules.property` is designed to match `products.db`'s column
  names for the 8 core nutrients (`sodium`→`sodium_mg_100g`, `protein`→`protein_100g`,
  etc.) so a numeric comparison is a direct lookup, not a name-mapping exercise.
- `claim_rules.db`'s `npsc_scoring_reference` + `npsc_category_thresholds` feed into
  any `claim_rules` row with `requires_npsc=1`, but need the not-yet-built Category
  1/2/3 classifier (see above) plus a fruit/veg/nut/legume % field we don't currently
  have, to actually run.
- `reference_values.db` does not join to anything else by key — it's used for Epic 6/7
  display, keyed by `age_band`/`nutrient` only.

## Reproducing a build

Every `.db` file has a matching `.ipynb` in the same folder with the real,
executed build code and its actual output. If a database ever needs to be rebuilt
(a source PDF is updated, a design decision changes), open that notebook — it is the
single source of truth for exactly how each number was derived, not this guide.
