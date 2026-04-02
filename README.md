# eve-sde-db

Converts the [EVE Online Static Data Export](https://developers.eveonline.com/docs/services/static-data-export/) (SDE) from its published JSONL format into a single queryable SQLite database.

A pre-built database is published automatically on each new SDE release — see [Releases](../../releases).

---

## Download the pre-built database

```bash
# Compressed (~100 MB download, ~280 MB on disk)
curl -L https://github.com/USER/REPO/releases/latest/download/sde_db.db.gz | gunzip > sde_db.db

# Or uncompressed (~280 MB)
curl -LO https://github.com/USER/REPO/releases/latest/download/sde_db.db
```

Verify with the provided `sha256sums.txt` in each release.

---

## Build it yourself

**Requirements:** Python 3.11+ (stdlib only — no pip installs needed)

```bash
# 1. Download and extract the SDE JSONL files
curl -fsSL https://developers.eveonline.com/static-data/eve-online-static-data-latest-jsonl.zip -o sde.zip
mkdir -p sde
unzip -q sde.zip -d sde_raw
find sde_raw -name "*.jsonl" -exec mv {} sde/ \;
rm -rf sde_raw sde.zip

# 2. Build the database
python3 main.py ./sde ./db/sde_db.db
```

Re-running `main.py` on an existing database is incremental: each source file is SHA-256 hashed and only reloaded if its content has changed.

---

## Schema overview

### Core item hierarchy

```
categories → groups → types
```

| Table | Rows | Description |
|-------|-----:|-------------|
| `categories` | 48 | Top-level item categories |
| `groups` | 1,590 | Item groups (`category_id` FK) |
| `types` | 51,672 | All items; names stored per-language (`name_en`, `name_de`, …) |

### Dogma (attributes & effects)

| Table | Rows | Description |
|-------|-----:|-------------|
| `dogma_attributes` | 2,829 | Attribute definitions (HP, CPU, range, …) |
| `dogma_effects` | 3,366 | Effect definitions |
| `dogma_units` | 60 | Unit labels (MW, m³, s, …) |
| `dogma_attribute_categories` | 37 | Attribute groupings |
| `type_dogma_attributes` | 630,390 | Per-type attribute values |
| `type_dogma_effects` | 52,860 | Per-type effect bindings |

### Blueprints

| Table | Rows | Description |
|-------|-----:|-------------|
| `blueprints` | 5,063 | Blueprint type and production limit |
| `blueprint_activities` | 19,102 | Activities per blueprint (manufacturing, invention, …) |
| `blueprint_activity_materials` | 36,364 | Input materials per activity |
| `blueprint_activity_products` | 6,306 | Output products per activity |
| `blueprint_activity_skills` | 22,345 | Required skills per activity |

### Market

| Table | Rows | Description |
|-------|-----:|-------------|
| `market_groups` | 2,095 | Market browser hierarchy |

### Map

```
map_regions → map_constellations → map_solar_systems
                                         ↓
                           map_planets / map_moons / map_stars
                           map_stargates / map_asteroid_belts
```

| Table | Rows | Description |
|-------|-----:|-------------|
| `map_regions` | 114 | Regions |
| `map_constellations` | 1,184 | Constellations |
| `map_solar_systems` | 8,490 | Solar systems with security status and 3D position |
| `map_planets` | 68,407 | Planets |
| `map_moons` | 344,457 | Moons |
| `map_asteroid_belts` | 40,928 | Asteroid belts |
| `map_stargates` | 13,968 | Stargates with destination |
| `map_stars` | 8,089 | Stars |

### Other notable tables

`races`, `bloodlines`, `ancestries`, `factions`, `npc_corporations`, `npc_characters`, `npc_stations`, `skins`, `skin_licenses`, `planet_schematics`, `certificates`, `masteries`, `meta_groups`, `clone_grades`, `contraband_types`, `compressible_types`, `sovereignty_upgrades`, `dynamic_item_attributes`

### Metadata

| Table | Description |
|-------|-------------|
| `sde_meta` | SDE build number and release date |
| `sde_file_hashes` | SHA-256 of each source file (used for incremental updates) |
| `translation_languages` | Language codes present in the data (`en`, `de`, `es`, `fr`, `ja`, `ko`, `ru`, `zh`) |

---

## Example queries

**Items with market listings:**
```sql
SELECT t.id, t.name_en, g.name_en AS group_name, c.name_en AS category
FROM types t
JOIN groups g ON t.group_id = g.id
JOIN categories c ON g.category_id = c.id
WHERE t.published = 1 AND t.market_group_id IS NOT NULL
ORDER BY t.name_en;
```

**Manufacturing inputs for a blueprint:**
```sql
SELECT mat.name_en AS material, bam.quantity
FROM blueprints bp
JOIN types bp_t ON bp.type_id = bp_t.id
JOIN blueprint_activities ba ON bp.type_id = ba.type_id AND ba.activity = 'manufacturing'
JOIN blueprint_activity_materials bam ON bp.type_id = bam.type_id AND bam.activity = 'manufacturing'
JOIN types mat ON bam.material_type_id = mat.id
WHERE bp_t.name_en = 'Stabber Blueprint';
-- Tritanium 540000 | Pyerite 180000 | Mexallon 36000 | …
```

**Dogma attributes for a ship:**
```sql
SELECT da.name, tda.value, du.name AS unit
FROM type_dogma_attributes tda
JOIN types t    ON tda.type_id    = t.id
JOIN dogma_attributes da ON tda.attribute_id = da.id
LEFT JOIN dogma_units du ON da.unit_id = du.id
WHERE t.name_en = 'Rifter';
```

**High-sec solar systems:**
```sql
SELECT ss.name_en, ROUND(ss.security_status, 1) AS sec, r.name_en AS region
FROM map_solar_systems ss
JOIN map_regions r ON ss.region_id = r.id
WHERE ss.security_status >= 0.45
ORDER BY ss.security_status DESC;
```

---

## Multilingual names

Most entity names are stored in eight columns — one per supported language:

```
name_en  name_de  name_es  name_fr  name_ja  name_ko  name_ru  name_zh
```

Tables with only one name column (e.g. `agent_types`, `corporation_activities`) use `name` and store the English string only, as that is all the source data provides.

---

## Automation

A GitHub Actions workflow (`.github/workflows/publish.yml`) runs weekly and on every manual trigger:

1. Downloads the latest SDE JSONL zip from CCP's servers
2. Builds the SQLite database
3. Publishes a new release tagged `build-{buildNumber}` with:
   - `sde_db.db` — uncompressed database
   - `sde_db.db.gz` — gzip-compressed database
   - `sha256sums.txt` — checksums for both files

Releases are skipped if the current SDE build number already has a release tag, so the workflow is safe to run on any schedule.

---

## Data source

EVE Online game data is © 2014 CCP hf. All rights reserved. "EVE", "EVE Online", and the EVE logo are registered trademarks of CCP hf. This project is not affiliated with or endorsed by CCP hf.

SDE source: <https://developers.eveonline.com/docs/services/static-data-export/>
