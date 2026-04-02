# EVE SDE Data Model

The SDE is distributed as JSONL files under `sde/`. Each file contains one entity per line; every entity has a `_key` field that is the integer primary key.

## Build Metadata

**`_sde.jsonl`** — one record with key `"sde"`.

| Field | Type | Description |
|---|---|---|
| `buildNumber` | int | SDE build number |
| `releaseDate` | string (ISO 8601) | Release timestamp |

## Core Item Hierarchy

Items are organized in a three-level hierarchy:

```
categories → groups → types
```

### `categories.jsonl`

Top-level classification of all in-game objects (Ships, Modules, Drones, etc.).

| Field | Type | Description |
|---|---|---|
| `_key` | int | `categoryID` |
| `name` | i18n | Category name |
| `published` | bool | Visible to players; `false` entries are internal/placeholder |

### `groups.jsonl`

Subdivisions within a category (e.g. category "Ship" → group "Battleship").

| Field | Type | Description |
|---|---|---|
| `_key` | int | `groupID` |
| `categoryID` | int | FK → `categories._key` |
| `name` | i18n | Group name |
| `published` | bool | |
| `anchorable` | bool | Items in this group can be anchored in space |
| `anchored` | bool | Items start anchored |
| `fittableNonSingleton` | bool | Can fit non-singleton items |
| `useBasePrice` | bool | |

### `types.jsonl`

Individual item types — the central entity that most other tables reference via `typeID`.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `typeID` |
| `groupID` | int | FK → `groups._key` |
| `name` | i18n | Item name |
| `published` | bool | |
| `mass` | float | Mass in kg |
| `portionSize` | int | Stack size for manufacturing |
| `volume` | float | Volume in m³ (when present) |
| `basePrice` | float | Base market price (when present) |
| `marketGroupID` | int | FK → `marketGroups._key` (when present) |

## Dogma System

The Dogma system defines all numerical attributes and effects that govern item behaviour.

### `dogmaAttributeCategories.jsonl`

Organizes attributes into logical groups (e.g. "Fitting", "Shield").

| Field | Type | Description |
|---|---|---|
| `_key` | int | `attributeCategoryID` |
| `name` | string | Category name |

### `dogmaAttributes.jsonl`

Definitions of all numerical properties an item can have (CPU, shield HP, damage, etc.).

| Field | Type | Description |
|---|---|---|
| `_key` | int | `attributeID` |
| `name` | string | Internal attribute name |
| `attributeCategoryID` | int | FK → `dogmaAttributeCategories._key` |
| `dataType` | int | Storage type (0=float, 1=int, etc.) |
| `defaultValue` | float | Value used when not overridden per-type |
| `highIsGood` | bool | Whether a higher value is beneficial |
| `stackable` | bool | Whether stacking penalties apply |
| `published` | bool | |
| `description` | string | Human-readable description |
| `displayWhenZero` | bool | Show in info panel even when value is 0 |

### `dogmaEffects.jsonl`

Named effects that can be active on a type (e.g. "shieldBoosting", "moduleBonusEnergyWeapon").

| Field | Type | Description |
|---|---|---|
| `_key` | int | `effectID` |
| `name` | string | Internal effect name |
| `guid` | string | Fully-qualified effect identifier |
| `effectCategoryID` | int | When the effect is active (passive, active, etc.) |
| `dischargeAttributeID` | int | Attribute for capacitor drain |
| `durationAttributeID` | int | Attribute for cycle time |
| `isAssistance` | bool | |
| `isOffensive` | bool | |
| `isWarpSafe` | bool | |
| `published` | bool | |

### `dogmaUnits.jsonl`

Units used to display attribute values (m/s, m³, HP, etc.).

| Field | Type | Description |
|---|---|---|
| `_key` | int | `unitID` |
| `name` | string | |
| `displayName` | string | |

### `typeDogma.jsonl`

Attribute and effect bindings per type. Keyed by `typeID`.

```json
{
  "_key": 18,
  "dogmaAttributes": [
    { "attributeID": 182, "value": 3386.0 }
  ],
  "dogmaEffects": [
    { "effectID": 11, "isDefault": true }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `_key` | int | `typeID` — FK → `types._key` |
| `dogmaAttributes` | array | `{attributeID, value}` pairs |
| `dogmaEffects` | array | `{effectID, isDefault}` pairs |

## Industry

### `blueprints.jsonl`

Manufacturing, copying, invention, and research recipes. Keyed by `blueprintTypeID`.

```json
{
  "_key": 681,
  "blueprintTypeID": 681,
  "maxProductionLimit": 300,
  "activities": {
    "manufacturing": {
      "time": 600,
      "materials": [{ "typeID": 38, "quantity": 86 }],
      "products":  [{ "typeID": 165, "quantity": 1 }]
    },
    "copying":           { "time": 480 },
    "research_material": { "time": 210 },
    "research_time":     { "time": 210 },
    "invention": {
      "time": 840,
      "materials": [...],
      "products":  [...],
      "skills":    [{ "typeID": 3408, "level": 1 }]
    }
  }
}
```

| Field | Type | Description |
|---|---|---|
| `_key` | int | `blueprintTypeID` — FK → `types._key` |
| `maxProductionLimit` | int | Max runs per job |
| `activities` | object | Keyed by activity name; each has `time` (seconds) and optionally `materials`, `products`, `skills` |

Activity names: `manufacturing`, `copying`, `research_material`, `research_time`, `invention`, `reaction`.

### `typeMaterials.jsonl`

Reprocessing / material composition per type.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `typeID` — FK → `types._key` |
| `materials` | array | `{materialTypeID, quantity}` |

### `planetSchematics.jsonl`

Planetary Industry (PI) processing recipes.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `schematicID` |
| `name` | i18n | |
| `cycleTime` | int | Processing cycle in seconds |
| `pins` | array | `typeID`s of PI structures that can run this schematic |
| `types` | array | `{_key: typeID, isInput, quantity}` — inputs (`isInput: true`) and the single output |

## Market

### `marketGroups.jsonl`

Hierarchical market browser categories. Groups can nest via `parentGroupID`.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `marketGroupID` |
| `name` | i18n | |
| `description` | i18n | |
| `parentGroupID` | int | FK → `marketGroups._key` (absent for root groups) |
| `hasTypes` | bool | Whether this group directly contains types |
| `iconID` | int | FK → `icons._key` |

## Map Hierarchy

```
mapRegions → mapConstellations → mapSolarSystems
    → mapPlanets / mapMoons / mapStars / mapStargates / mapAsteroidBelts
```

### `mapRegions.jsonl`

| Field | Type | Description |
|---|---|---|
| `_key` | int | `regionID` |
| `name` | i18n | |
| `description` | i18n | |
| `constellationIDs` | array | Child constellation IDs |
| `factionID` | int | Sovereign faction (when present) |
| `wormholeClassID` | int | For wormhole regions |
| `position` | `{x,y,z}` | 3D position in meters |

### `mapConstellations.jsonl`

| Field | Type | Description |
|---|---|---|
| `_key` | int | `constellationID` |
| `regionID` | int | FK → `mapRegions._key` |
| `name` | i18n | |
| `solarSystemIDs` | array | Child solar system IDs |
| `position` | `{x,y,z}` | |

### `mapSolarSystems.jsonl`

| Field | Type | Description |
|---|---|---|
| `_key` | int | `solarSystemID` |
| `constellationID` | int | FK → `mapConstellations._key` |
| `regionID` | int | FK → `mapRegions._key` |
| `name` | i18n | |
| `securityStatus` | float | -1.0 to 1.0 |
| `securityClass` | string | Letter code (A–F, null for wormholes) |
| `starID` | int | FK → `mapStars._key` |
| `planetIDs` | array | FKs → `mapPlanets._key` |
| `stargateIDs` | array | FKs → `mapStargates._key` |
| `position` | `{x,y,z}` | |
| `radius` | float | |
| `luminosity` | float | |
| `border` | bool | Region border system |
| `hub` | bool | Major trade/logistics hub |
| `international` | bool | Connected to another region |
| `regional` | bool | |

### `mapPlanets.jsonl` / `mapMoons.jsonl` / `mapStars.jsonl` / `mapStargates.jsonl` / `mapAsteroidBelts.jsonl`

All celestial objects. Each has a `solarSystemID` FK and a `position {x,y,z}`. Stargates additionally have a `destinationID` pointing to the gate in the connected system.

## Lore / Political Entities

### `races.jsonl`

The four playable races (Caldari, Amarr, Gallente, Minmatar).

| Field | Type | Description |
|---|---|---|
| `_key` | int | `raceID` |
| `name` | i18n | |
| `description` | i18n | |
| `iconID` | int | |
| `shipTypeID` | int | Starter ship type |
| `skills` | array | `{_key: typeID, _value: level}` default skill set |

### `factions.jsonl`

Player-joinable and NPC factions (Caldari State, Guristas Pirates, etc.).

| Field | Type | Description |
|---|---|---|
| `_key` | int | `factionID` |
| `name` | i18n | |
| `description` | i18n | |
| `corporationID` | int | Faction's main corporation |
| `militiaCorporationID` | int | FW militia corporation (when present) |
| `memberRaces` | array | `raceID`s that belong to this faction |
| `solarSystemID` | int | Faction headquarters |
| `sizeFactor` | float | Relative size indicator |

### `npcCorporations.jsonl`

NPC corporations.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `corporationID` |
| `name` | i18n | |
| `description` | i18n | |
| `ceoID` | int | NPC character ID |
| `stationID` | int | HQ station |
| `taxRate` | float | |
| `tickerName` | string | |

### `npcStations.jsonl`

NPC-owned stations.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `stationID` |
| `solarSystemID` | int | FK → `mapSolarSystems._key` |
| `ownerID` | int | FK → `npcCorporations._key` |
| `typeID` | int | Station type |
| `operationID` | int | FK → `stationOperations._key` |
| `position` | `{x,y,z}` | |
| `reprocessingEfficiency` | float | |

## Cosmetics

### `skins.jsonl`

Ship paint/skin definitions.

| Field | Type | Description |
|---|---|---|
| `_key` | int | `skinID` |
| `internalName` | string | |
| `skinMaterialID` | int | FK → `skinMaterials._key` |
| `types` | array | `typeID`s this skin applies to |
| `visibleSerenity` | bool | Available on CN server |
| `visibleTranquility` | bool | Available on TQ (main) server |

### `skinLicenses.jsonl`

Licenses that grant a skin to a character. Keyed by `licenseTypeID` (same as the license item's `typeID`).

| Field | Type | Description |
|---|---|---|
| `_key` | int | `licenseTypeID` |
| `skinID` | int | FK → `skins._key` |
| `duration` | int | License duration in seconds; `-1` = permanent |

## Item Info Panel

### `typeBonus.jsonl`

Role and skill bonuses shown in the item info panel. Keyed by `typeID` (the ship or structure).

```json
{
  "_key": 582,
  "roleBonuses": [
    { "bonus": 300.0, "bonusText": {...}, "importance": 1, "unitID": 105 }
  ],
  "types": [
    {
      "_key": 3330,
      "_value": [
        { "bonus": 10.0, "bonusText": {...}, "importance": 1, "unitID": 105 }
      ]
    }
  ]
}
```

| Field | Type | Description |
|---|---|---|
| `_key` | int | `typeID` — FK → `types._key` |
| `roleBonuses` | array | Unconditional bonuses; each has `bonus`, `bonusText` (i18n), `importance`, `unitID` |
| `types` | array | Per-skill bonuses; `_key` is the skill `typeID`, `_value` is an array of bonus objects |

## Other Tables

| File | Description |
|---|---|
| `metaGroups.jsonl` | Tech tiers (Tech I, Tech II, Faction, Officer, etc.) with display color |
| `certificates.jsonl` | Certificate definitions for the certificate planner |
| `masteries.jsonl` | Ship mastery level requirements |
| `characterAttributes.jsonl` | Charisma, Intelligence, Memory, Perception, Willpower |
| `ancestries.jsonl` / `bloodlines.jsonl` | Character creation background options |
| `icons.jsonl` | Icon file references used across many entities |
| `graphics.jsonl` | 3D model/graphic references |
| `agentTypes.jsonl` / `agentsInSpace.jsonl` | Agent definitions |
| `controlTowerResources.jsonl` | POS fuel/resource requirements |
| `compressibleTypes.jsonl` | Ore compression mappings |
| `contrabandTypes.jsonl` | Contraband rules per faction |
| `dynamicItemAttributes.jsonl` | Abyssal/mutated item attribute ranges |
| `dbuffCollections.jsonl` | Delayed buff (weather effect) definitions |
| `planetResources.jsonl` | PI resource distribution per planet type |
| `sovereigntyUpgrades.jsonl` | Sovereignty upgrade structure definitions |
| `stationOperations.jsonl` / `stationServices.jsonl` | Station operation/service definitions |
| `translationLanguages.jsonl` | Supported localization languages |
| `freelanceJobSchemas.jsonl` / `mercenaryTacticalOperations.jsonl` | Mercenary contract system |
| `landmarks.jsonl` | Named in-space landmarks |
| `mapSecondarySuns.jsonl` | Binary/trinary star system secondary suns |
| `npcCharacters.jsonl` / `npcCorporationDivisions.jsonl` | NPC agent/corp division data |
| `cloneGrades.jsonl` | Alpha/Omega clone state definitions |
| `corporationActivities.jsonl` | Corporation activity type definitions |

## Shared Conventions

### Multilingual names (`i18n`)

Any field documented as `i18n` is a JSON object keyed by language code:

```json
{ "en": "Tritanium", "de": "Tritanium", "es": "Tritanium", "fr": "Tritanium", "ja": "トリタニウム", "ko": "트리타늄", "ru": "Tritanium", "zh": "三钛合金" }
```

Languages: `en`, `de`, `es`, `fr`, `ja`, `ko`, `ru`, `zh`. When indexing or displaying, default to `name.en`.

### `published` flag

Records with `published: false` are internal, placeholder, or legacy entries not visible in the game client. Typically filter these out for player-facing queries.

### Primary keys

All `_key` values are integers (except `_sde.jsonl` which uses the string `"sde"`). Cross-references use `*ID` suffix conventions (`typeID`, `groupID`, `regionID`, etc.).
