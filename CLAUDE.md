# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This project loads the EVE Online Static Data Export (SDE) from JSONL files into a SQLite database for querying. The SDE is a snapshot of game data (items, blueprints, map data, etc.) published by CCP Games.

- `sde/` — JSONL files, one per entity type. Each line is a JSON object; `_key` is the integer primary key.
- `db/sde_db.db` — SQLite database (currently empty, to be populated by `main.py`).
- `main.py` — entry point for loading SDE data into the database (currently empty).
- `sde/_sde.jsonl` — build metadata (build number, release date).

## SDE Data Model

The core entity hierarchy:

```
categories → groups → types
```

- `categories.jsonl`: top-level item categories
- `groups.jsonl`: item groups (`categoryID` FK)
- `types.jsonl`: individual item types (`groupID` FK); names are multilingual objects `{"en": ..., "de": ..., "fr": ..., "ja": ..., "ko": ..., "ru": ..., "zh": ...}`

Item metadata tables that reference `typeID`:
- `typeDogma.jsonl` — dogma attribute/effect bindings per type
- `dogmaAttributes.jsonl`, `dogmaEffects.jsonl` — attribute/effect definitions
- `typeMaterials.jsonl` — reprocessing/material composition
- `typeBonus.jsonl` — role/skill bonuses displayed in info panel
- `blueprints.jsonl` — manufacturing/invention/copying/research recipes
- `marketGroups.jsonl` — market browser hierarchy

Map hierarchy:
```
mapRegions → mapConstellations → mapSolarSystems → mapPlanets / mapMoons / mapStars / mapStargates / mapAsteroidBelts
```

Other notable tables: `races`, `factions`, `npcCorporations`, `npcStations`, `skins`, `skinLicenses`, `certificates`, `masteries`, `planetSchematics`, `planetResources`, `metaGroups`, `dogmaUnits`, `dogmaAttributeCategories`.

## Key Data Conventions

- All JSONL files use `_key` as the primary key field (integer).
- Multilingual name fields are JSON objects keyed by language code (`en`, `de`, `es`, `fr`, `ja`, `ko`, `ru`, `zh`). When indexing, typically use `name.en`.
- Boolean fields use JSON `true`/`false`.
- Cross-references use `*ID` suffixes (e.g., `groupID`, `categoryID`, `typeID`).
- `published: false` entries are internal/placeholder records.

## Running

```bash
python3 main.py
```

No dependencies beyond Python stdlib (`sqlite3`, `json`) are expected for the loader.
