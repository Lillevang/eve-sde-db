#!/usr/bin/env python3
"""Build EVE SDE SQLite database from JSONL source files."""

import hashlib
import json
import sqlite3
import sys
from pathlib import Path

LANGS = ['en', 'de', 'es', 'fr', 'ja', 'ko', 'ru', 'zh']
SDE_DIR = Path('sde')
DB_PATH = Path('db/sde_db.db')
BATCH_SIZE = 500


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def ml(obj, key):
    """Return list of per-language values for a multilingual field."""
    d = obj.get(key)
    if not d:
        return [None] * len(LANGS)
    if isinstance(d, str):
        return [d] + [None] * (len(LANGS) - 1)
    return [d.get(lang) for lang in LANGS]


def _en(v):
    """Return the English string from a multilingual dict, or the value as-is."""
    return v.get('en') if isinstance(v, dict) else v


def pos(obj):
    """Return (x, y, z) from the 'position' sub-object."""
    p = obj.get('position') or {}
    return p.get('x'), p.get('y'), p.get('z')


def stats(obj, *fields):
    """Return a list of values from the 'statistics' sub-object."""
    s = obj.get('statistics') or {}
    return [s.get(f) for f in fields]


def attrs(obj, *fields):
    """Return a list of values from the 'attributes' sub-object."""
    a = obj.get('attributes') or {}
    return [a.get(f) for f in fields]


def load_jsonl(path):
    """Yield parsed JSON objects from a JSONL file."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def bulk_insert(conn, sql, iterable):
    """Execute many inserts from an iterable in batches."""
    batch = []
    for row in iterable:
        batch.append(row)
        if len(batch) >= BATCH_SIZE:
            conn.executemany(sql, batch)
            batch.clear()
    if batch:
        conn.executemany(sql, batch)


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

SCHEMA = """
-- Build metadata
CREATE TABLE sde_meta (
    build_number  INTEGER NOT NULL,
    release_date  TEXT    NOT NULL
);

-- -------------------------------------------------------------------------
-- Reference / lookup tables (no external FKs)
-- -------------------------------------------------------------------------

CREATE TABLE icons (
    id          INTEGER PRIMARY KEY,
    icon_file   TEXT
);

CREATE TABLE graphics (
    id               INTEGER PRIMARY KEY,
    graphic_file     TEXT,
    icon_folder      TEXT,
    sof_faction_name TEXT,
    sof_hull_name    TEXT,
    sof_race_name    TEXT
);

CREATE TABLE translation_languages (
    id   TEXT PRIMARY KEY,
    name TEXT
);

CREATE TABLE dogma_attribute_categories (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    description TEXT
);

CREATE TABLE dogma_units (
    id           INTEGER PRIMARY KEY,
    name         TEXT,
    description  TEXT,
    display_name TEXT
);

CREATE TABLE agent_types (
    id   INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE corporation_activities (
    id   INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE npc_corporation_division_types (
    id               INTEGER PRIMARY KEY,
    name             TEXT,
    display_name     TEXT,
    description      TEXT,
    internal_name    TEXT,
    leader_type_name TEXT
);

CREATE TABLE station_services (
    id           INTEGER PRIMARY KEY,
    service_name TEXT,
    description  TEXT
);

CREATE TABLE clone_grades (
    id   INTEGER PRIMARY KEY,
    name TEXT
);

CREATE TABLE clone_grade_skills (
    grade_id      INTEGER NOT NULL REFERENCES clone_grades(id),
    skill_type_id INTEGER NOT NULL,
    level         INTEGER NOT NULL
);

-- -------------------------------------------------------------------------
-- Item hierarchy
-- -------------------------------------------------------------------------

CREATE TABLE categories (
    id         INTEGER PRIMARY KEY,
    published  INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT
);

CREATE TABLE groups (
    id                    INTEGER PRIMARY KEY,
    category_id           INTEGER REFERENCES categories(id),
    anchorable            INTEGER,
    anchored              INTEGER,
    fittable_non_singleton INTEGER,
    published             INTEGER,
    use_base_price        INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT
);

CREATE INDEX groups_category_id ON groups(category_id);

CREATE TABLE meta_groups (
    id          INTEGER PRIMARY KEY,
    color       TEXT,
    icon_id     INTEGER REFERENCES icons(id),
    icon_suffix TEXT,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE market_groups (
    id              INTEGER PRIMARY KEY,
    parent_group_id INTEGER REFERENCES market_groups(id),
    has_types       INTEGER,
    icon_id         INTEGER REFERENCES icons(id),
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE types (
    id                      INTEGER PRIMARY KEY,
    group_id                INTEGER REFERENCES groups(id),
    mass                    REAL,
    portion_size            INTEGER,
    published               INTEGER,
    volume                  REAL,
    capacity                REAL,
    base_price              REAL,
    market_group_id         INTEGER REFERENCES market_groups(id),
    meta_group_id           INTEGER REFERENCES meta_groups(id),
    meta_level              INTEGER,
    icon_id                 INTEGER REFERENCES icons(id),
    graphic_id              INTEGER REFERENCES graphics(id),
    sound_id                INTEGER,
    race_id                 INTEGER,
    radius                  REAL,
    variation_parent_type_id INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE INDEX types_group_id        ON types(group_id);
CREATE INDEX types_market_group_id ON types(market_group_id);

-- -------------------------------------------------------------------------
-- Dogma
-- -------------------------------------------------------------------------

CREATE TABLE dogma_attributes (
    id                   INTEGER PRIMARY KEY,
    attribute_category_id INTEGER REFERENCES dogma_attribute_categories(id),
    data_type            INTEGER,
    default_value        REAL,
    description          TEXT,
    display_when_zero    INTEGER,
    high_is_good         INTEGER,
    icon_id              INTEGER REFERENCES icons(id),
    name                 TEXT,
    published            INTEGER,
    stackable            INTEGER,
    unit_id              INTEGER REFERENCES dogma_units(id),
    display_name_en TEXT, display_name_de TEXT, display_name_es TEXT, display_name_fr TEXT,
    display_name_ja TEXT, display_name_ko TEXT, display_name_ru TEXT, display_name_zh TEXT,
    tooltip_description_en TEXT, tooltip_description_de TEXT, tooltip_description_es TEXT, tooltip_description_fr TEXT,
    tooltip_description_ja TEXT, tooltip_description_ko TEXT, tooltip_description_ru TEXT, tooltip_description_zh TEXT,
    tooltip_title_en TEXT, tooltip_title_de TEXT, tooltip_title_es TEXT, tooltip_title_fr TEXT,
    tooltip_title_ja TEXT, tooltip_title_ko TEXT, tooltip_title_ru TEXT, tooltip_title_zh TEXT
);

CREATE TABLE dogma_effects (
    id                        INTEGER PRIMARY KEY,
    disallow_auto_repeat      INTEGER,
    discharge_attribute_id    INTEGER REFERENCES dogma_attributes(id),
    distribution              INTEGER,
    duration_attribute_id     INTEGER REFERENCES dogma_attributes(id),
    effect_category_id        INTEGER,
    electronic_chance         INTEGER,
    falloff_attribute_id      INTEGER REFERENCES dogma_attributes(id),
    guid                      TEXT,
    is_assistance             INTEGER,
    is_offensive              INTEGER,
    is_warp_safe              INTEGER,
    name                      TEXT,
    propulsion_chance         INTEGER,
    published                 INTEGER,
    range_attribute_id        INTEGER REFERENCES dogma_attributes(id),
    range_chance              INTEGER,
    tracking_speed_attribute_id INTEGER REFERENCES dogma_attributes(id)
);

CREATE TABLE type_dogma_attributes (
    type_id      INTEGER NOT NULL REFERENCES types(id),
    attribute_id INTEGER NOT NULL REFERENCES dogma_attributes(id),
    value        REAL,
    PRIMARY KEY (type_id, attribute_id)
);

CREATE INDEX tda_attribute_id ON type_dogma_attributes(attribute_id);

CREATE TABLE type_dogma_effects (
    type_id    INTEGER NOT NULL REFERENCES types(id),
    effect_id  INTEGER NOT NULL REFERENCES dogma_effects(id),
    is_default INTEGER,
    PRIMARY KEY (type_id, effect_id)
);

-- -------------------------------------------------------------------------
-- Type relations
-- -------------------------------------------------------------------------

CREATE TABLE type_materials (
    type_id          INTEGER NOT NULL REFERENCES types(id),
    material_type_id INTEGER NOT NULL REFERENCES types(id),
    quantity         INTEGER NOT NULL,
    PRIMARY KEY (type_id, material_type_id)
);

-- roleBonuses: flat bonuses on the hull (no skill requirement)
CREATE TABLE type_role_bonuses (
    id          INTEGER PRIMARY KEY,
    type_id     INTEGER NOT NULL REFERENCES types(id),
    bonus       REAL,
    unit_id     INTEGER REFERENCES dogma_units(id),
    importance  INTEGER,
    bonus_text_en TEXT, bonus_text_de TEXT, bonus_text_es TEXT, bonus_text_fr TEXT,
    bonus_text_ja TEXT, bonus_text_ko TEXT, bonus_text_ru TEXT, bonus_text_zh TEXT
);

CREATE INDEX type_role_bonuses_type_id ON type_role_bonuses(type_id);

-- per-skill bonuses shown in the type info panel
CREATE TABLE type_skill_bonuses (
    id            INTEGER PRIMARY KEY,
    type_id       INTEGER NOT NULL REFERENCES types(id),
    skill_type_id INTEGER NOT NULL REFERENCES types(id),
    bonus         REAL,
    unit_id       INTEGER REFERENCES dogma_units(id),
    importance    INTEGER,
    bonus_text_en TEXT, bonus_text_de TEXT, bonus_text_es TEXT, bonus_text_fr TEXT,
    bonus_text_ja TEXT, bonus_text_ko TEXT, bonus_text_ru TEXT, bonus_text_zh TEXT
);

CREATE INDEX type_skill_bonuses_type_id ON type_skill_bonuses(type_id);

-- -------------------------------------------------------------------------
-- Blueprints
-- -------------------------------------------------------------------------

CREATE TABLE blueprints (
    type_id              INTEGER PRIMARY KEY REFERENCES types(id),
    max_production_limit INTEGER
);

-- One row per (blueprint, activity) pair; activity values:
--   manufacturing, copying, invention, research_material, research_time, reaction
CREATE TABLE blueprint_activities (
    type_id  INTEGER NOT NULL REFERENCES blueprints(type_id),
    activity TEXT    NOT NULL,
    time     INTEGER,
    PRIMARY KEY (type_id, activity)
);

CREATE TABLE blueprint_activity_materials (
    type_id          INTEGER NOT NULL,
    activity         TEXT    NOT NULL,
    material_type_id INTEGER NOT NULL REFERENCES types(id),
    quantity         INTEGER NOT NULL,
    FOREIGN KEY (type_id, activity) REFERENCES blueprint_activities(type_id, activity)
);

CREATE INDEX bam_type_activity ON blueprint_activity_materials(type_id, activity);

CREATE TABLE blueprint_activity_products (
    type_id         INTEGER NOT NULL,
    activity        TEXT    NOT NULL,
    product_type_id INTEGER NOT NULL REFERENCES types(id),
    quantity        INTEGER,
    probability     REAL,
    FOREIGN KEY (type_id, activity) REFERENCES blueprint_activities(type_id, activity)
);

CREATE INDEX bap_type_activity ON blueprint_activity_products(type_id, activity);

CREATE TABLE blueprint_activity_skills (
    type_id       INTEGER NOT NULL,
    activity      TEXT    NOT NULL,
    skill_type_id INTEGER NOT NULL REFERENCES types(id),
    level         INTEGER NOT NULL,
    FOREIGN KEY (type_id, activity) REFERENCES blueprint_activities(type_id, activity)
);

CREATE INDEX bas_type_activity ON blueprint_activity_skills(type_id, activity);

-- -------------------------------------------------------------------------
-- Character / race / social
-- -------------------------------------------------------------------------

CREATE TABLE races (
    id          INTEGER PRIMARY KEY,
    icon_id     INTEGER REFERENCES icons(id),
    ship_type_id INTEGER REFERENCES types(id),
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE race_skills (
    race_id       INTEGER NOT NULL REFERENCES races(id),
    skill_type_id INTEGER NOT NULL,
    level         INTEGER NOT NULL,
    PRIMARY KEY (race_id, skill_type_id)
);

CREATE TABLE bloodlines (
    id             INTEGER PRIMARY KEY,
    race_id        INTEGER REFERENCES races(id),
    corporation_id INTEGER,
    icon_id        INTEGER REFERENCES icons(id),
    charisma       INTEGER,
    intelligence   INTEGER,
    memory         INTEGER,
    perception     INTEGER,
    willpower      INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE ancestries (
    id           INTEGER PRIMARY KEY,
    bloodline_id INTEGER REFERENCES bloodlines(id),
    icon_id      INTEGER REFERENCES icons(id),
    charisma     INTEGER,
    intelligence INTEGER,
    memory       INTEGER,
    perception   INTEGER,
    willpower    INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT,
    short_description_en TEXT, short_description_de TEXT, short_description_es TEXT, short_description_fr TEXT,
    short_description_ja TEXT, short_description_ko TEXT, short_description_ru TEXT, short_description_zh TEXT
);

CREATE TABLE character_attributes (
    id                INTEGER PRIMARY KEY,
    icon_id           INTEGER REFERENCES icons(id),
    name              TEXT,
    description       TEXT,
    notes             TEXT,
    short_description TEXT
);

CREATE TABLE factions (
    id                    INTEGER PRIMARY KEY,
    corporation_id        INTEGER,
    militia_corporation_id INTEGER,
    solar_system_id       INTEGER,
    icon_id               INTEGER REFERENCES icons(id),
    size_factor           REAL,
    flat_logo             TEXT,
    flat_logo_with_name   TEXT,
    unique_name           INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT,
    short_description_en TEXT, short_description_de TEXT, short_description_es TEXT, short_description_fr TEXT,
    short_description_ja TEXT, short_description_ko TEXT, short_description_ru TEXT, short_description_zh TEXT
);

CREATE TABLE faction_member_races (
    faction_id INTEGER NOT NULL REFERENCES factions(id),
    race_id    INTEGER NOT NULL REFERENCES races(id),
    PRIMARY KEY (faction_id, race_id)
);

-- -------------------------------------------------------------------------
-- Skins
-- -------------------------------------------------------------------------

CREATE TABLE skin_materials (
    id              INTEGER PRIMARY KEY,
    material_set_id INTEGER,
    display_name_en TEXT, display_name_de TEXT, display_name_es TEXT, display_name_fr TEXT,
    display_name_ja TEXT, display_name_ko TEXT, display_name_ru TEXT, display_name_zh TEXT
);

CREATE TABLE skins (
    id                 INTEGER PRIMARY KEY,
    allow_ccp_devs     INTEGER,
    internal_name      TEXT,
    skin_material_id   INTEGER REFERENCES skin_materials(id),
    visible_serenity   INTEGER,
    visible_tranquility INTEGER
);

CREATE TABLE skin_types (
    skin_id INTEGER NOT NULL REFERENCES skins(id),
    type_id INTEGER NOT NULL REFERENCES types(id),
    PRIMARY KEY (skin_id, type_id)
);

CREATE TABLE skin_licenses (
    id              INTEGER PRIMARY KEY,
    license_type_id INTEGER REFERENCES types(id),
    skin_id         INTEGER REFERENCES skins(id),
    duration        INTEGER
);

-- -------------------------------------------------------------------------
-- Planetary interaction
-- -------------------------------------------------------------------------

CREATE TABLE planet_schematics (
    id         INTEGER PRIMARY KEY,
    cycle_time INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT
);

-- Pins are the factory/extractor building types that can run this schematic
CREATE TABLE planet_schematic_pins (
    schematic_id INTEGER NOT NULL REFERENCES planet_schematics(id),
    pin_type_id  INTEGER NOT NULL REFERENCES types(id),
    PRIMARY KEY (schematic_id, pin_type_id)
);

CREATE TABLE planet_schematic_types (
    schematic_id INTEGER NOT NULL REFERENCES planet_schematics(id),
    type_id      INTEGER NOT NULL REFERENCES types(id),
    is_input     INTEGER NOT NULL,
    quantity     INTEGER NOT NULL,
    PRIMARY KEY (schematic_id, type_id)
);

-- Keyed on celestial body ID (planet/moon); optional fields per body
CREATE TABLE planet_resources (
    planet_id INTEGER PRIMARY KEY,
    power     INTEGER,
    workforce INTEGER,
    reagent   TEXT
);

-- -------------------------------------------------------------------------
-- Certificates and masteries
-- -------------------------------------------------------------------------

CREATE TABLE certificates (
    id       INTEGER PRIMARY KEY,
    group_id INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE certificate_recommended_for (
    certificate_id INTEGER NOT NULL REFERENCES certificates(id),
    type_id        INTEGER NOT NULL REFERENCES types(id),
    PRIMARY KEY (certificate_id, type_id)
);

-- Required skill levels per certificate grade (basic/standard/improved/advanced/elite)
CREATE TABLE certificate_skill_types (
    certificate_id INTEGER NOT NULL REFERENCES certificates(id),
    skill_type_id  INTEGER NOT NULL,
    basic          INTEGER,
    standard       INTEGER,
    improved       INTEGER,
    advanced       INTEGER,
    elite          INTEGER,
    PRIMARY KEY (certificate_id, skill_type_id)
);

-- Maps a type (ship/module) → mastery level → required certificates
CREATE TABLE masteries (
    type_id        INTEGER NOT NULL REFERENCES types(id),
    mastery_level  INTEGER NOT NULL,
    certificate_id INTEGER NOT NULL REFERENCES certificates(id),
    PRIMARY KEY (type_id, mastery_level, certificate_id)
);

-- -------------------------------------------------------------------------
-- Map
-- -------------------------------------------------------------------------

CREATE TABLE map_regions (
    id               INTEGER PRIMARY KEY,
    faction_id       INTEGER REFERENCES factions(id),
    nebula_id        INTEGER,
    wormhole_class_id INTEGER,
    pos_x REAL, pos_y REAL, pos_z REAL,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE map_constellations (
    id                INTEGER PRIMARY KEY,
    region_id         INTEGER REFERENCES map_regions(id),
    faction_id        INTEGER REFERENCES factions(id),
    wormhole_class_id INTEGER,
    pos_x REAL, pos_y REAL, pos_z REAL,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT
);

CREATE INDEX map_constellations_region_id ON map_constellations(region_id);

CREATE TABLE map_solar_systems (
    id                INTEGER PRIMARY KEY,
    constellation_id  INTEGER REFERENCES map_constellations(id),
    region_id         INTEGER REFERENCES map_regions(id),
    star_id           INTEGER,
    border            INTEGER,
    corridor          INTEGER,
    fringe            INTEGER,
    hub               INTEGER,
    international     INTEGER,
    regional          INTEGER,
    luminosity        REAL,
    radius            REAL,
    security_status   REAL,
    security_class    TEXT,
    wormhole_class_id INTEGER,
    pos_x REAL, pos_y REAL, pos_z REAL,
    pos2d_x REAL, pos2d_y REAL,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT
);

CREATE INDEX map_solar_systems_constellation_id ON map_solar_systems(constellation_id);
CREATE INDEX map_solar_systems_region_id        ON map_solar_systems(region_id);

CREATE TABLE map_stars (
    id              INTEGER PRIMARY KEY,
    solar_system_id INTEGER REFERENCES map_solar_systems(id),
    type_id         INTEGER REFERENCES types(id),
    radius          REAL,
    stat_age            REAL,
    stat_life           REAL,
    stat_luminosity     REAL,
    stat_spectral_class TEXT,
    stat_temperature    REAL
);

CREATE TABLE map_planets (
    id              INTEGER PRIMARY KEY,
    solar_system_id INTEGER REFERENCES map_solar_systems(id),
    type_id         INTEGER REFERENCES types(id),
    celestial_index INTEGER,
    orbit_id        INTEGER,
    radius          REAL,
    pos_x REAL, pos_y REAL, pos_z REAL,
    attr_height_map_1  INTEGER,
    attr_height_map_2  INTEGER,
    attr_population    INTEGER,
    attr_shader_preset INTEGER,
    stat_density         REAL,
    stat_eccentricity    REAL,
    stat_escape_velocity REAL,
    stat_locked          INTEGER,
    stat_mass_dust       REAL,
    stat_mass_gas        REAL,
    stat_orbit_period    REAL,
    stat_orbit_radius    REAL,
    stat_pressure        REAL,
    stat_rotation_rate   REAL,
    stat_spectral_class  TEXT,
    stat_surface_gravity REAL,
    stat_temperature     REAL
);

CREATE INDEX map_planets_solar_system_id ON map_planets(solar_system_id);

CREATE TABLE map_moons (
    id              INTEGER PRIMARY KEY,
    solar_system_id INTEGER REFERENCES map_solar_systems(id),
    type_id         INTEGER REFERENCES types(id),
    celestial_index INTEGER,
    orbit_id        INTEGER,
    orbit_index     INTEGER,
    radius          REAL,
    pos_x REAL, pos_y REAL, pos_z REAL,
    attr_height_map_1  INTEGER,
    attr_height_map_2  INTEGER,
    attr_population    INTEGER,
    attr_shader_preset INTEGER,
    stat_density         REAL,
    stat_eccentricity    REAL,
    stat_escape_velocity REAL,
    stat_locked          INTEGER,
    stat_mass_dust       REAL,
    stat_mass_gas        REAL,
    stat_orbit_period    REAL,
    stat_orbit_radius    REAL,
    stat_pressure        REAL,
    stat_rotation_rate   REAL,
    stat_spectral_class  TEXT,
    stat_surface_gravity REAL,
    stat_temperature     REAL
);

CREATE INDEX map_moons_solar_system_id ON map_moons(solar_system_id);

CREATE TABLE map_asteroid_belts (
    id              INTEGER PRIMARY KEY,
    solar_system_id INTEGER REFERENCES map_solar_systems(id),
    type_id         INTEGER REFERENCES types(id),
    celestial_index INTEGER,
    orbit_id        INTEGER,
    orbit_index     INTEGER,
    radius          REAL,
    pos_x REAL, pos_y REAL, pos_z REAL,
    stat_density         REAL,
    stat_eccentricity    REAL,
    stat_escape_velocity REAL,
    stat_locked          INTEGER,
    stat_mass_dust       REAL,
    stat_mass_gas        REAL,
    stat_orbit_period    REAL,
    stat_orbit_radius    REAL,
    stat_pressure        REAL,
    stat_rotation_rate   REAL,
    stat_spectral_class  TEXT,
    stat_surface_gravity REAL,
    stat_temperature     REAL
);

CREATE INDEX map_asteroid_belts_solar_system_id ON map_asteroid_belts(solar_system_id);

CREATE TABLE map_stargates (
    id                        INTEGER PRIMARY KEY,
    solar_system_id           INTEGER REFERENCES map_solar_systems(id),
    type_id                   INTEGER REFERENCES types(id),
    destination_solar_system_id INTEGER REFERENCES map_solar_systems(id),
    destination_stargate_id   INTEGER,
    pos_x REAL, pos_y REAL, pos_z REAL
);

CREATE INDEX map_stargates_solar_system_id ON map_stargates(solar_system_id);

CREATE TABLE map_secondary_suns (
    id                  INTEGER PRIMARY KEY,
    solar_system_id     INTEGER REFERENCES map_solar_systems(id),
    type_id             INTEGER REFERENCES types(id),
    effect_beacon_type_id INTEGER REFERENCES types(id),
    pos_x REAL, pos_y REAL, pos_z REAL
);

-- -------------------------------------------------------------------------
-- Stations
-- -------------------------------------------------------------------------

CREATE TABLE station_operations (
    id                  INTEGER PRIMARY KEY,
    activity_id         INTEGER,
    border              REAL,
    corridor            REAL,
    fringe              REAL,
    hub                 REAL,
    manufacturing_factor REAL,
    ratio               REAL,
    research_factor     REAL,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE station_operation_services (
    operation_id INTEGER NOT NULL REFERENCES station_operations(id),
    service_id   INTEGER NOT NULL REFERENCES station_services(id),
    PRIMARY KEY (operation_id, service_id)
);

-- station type to use per race (race bitmask key → station typeID)
CREATE TABLE station_operation_station_types (
    operation_id     INTEGER NOT NULL REFERENCES station_operations(id),
    race_id          INTEGER NOT NULL,
    station_type_id  INTEGER NOT NULL REFERENCES types(id),
    PRIMARY KEY (operation_id, race_id)
);

CREATE TABLE npc_stations (
    id                         INTEGER PRIMARY KEY,
    solar_system_id            INTEGER REFERENCES map_solar_systems(id),
    type_id                    INTEGER REFERENCES types(id),
    owner_id                   INTEGER,
    operation_id               INTEGER REFERENCES station_operations(id),
    orbit_id                   INTEGER,
    orbit_index                INTEGER,
    celestial_index            INTEGER,
    reprocessing_efficiency    REAL,
    reprocessing_hangar_flag   INTEGER,
    reprocessing_stations_take REAL,
    use_operation_name         INTEGER,
    pos_x REAL, pos_y REAL, pos_z REAL
);

CREATE INDEX npc_stations_solar_system_id ON npc_stations(solar_system_id);

-- -------------------------------------------------------------------------
-- NPC entities
-- -------------------------------------------------------------------------

CREATE TABLE npc_characters (
    id             INTEGER PRIMARY KEY,
    corporation_id INTEGER,
    ancestry_id    INTEGER REFERENCES ancestries(id),
    bloodline_id   INTEGER REFERENCES bloodlines(id),
    career_id      INTEGER,
    ceo            INTEGER,
    gender         INTEGER,
    location_id    INTEGER,
    race_id        INTEGER REFERENCES races(id),
    school_id      INTEGER,
    speciality_id  INTEGER,
    start_date     TEXT,
    unique_name    INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT
);

CREATE TABLE npc_character_skills (
    character_id  INTEGER NOT NULL REFERENCES npc_characters(id),
    skill_type_id INTEGER NOT NULL,
    level         INTEGER,
    PRIMARY KEY (character_id, skill_type_id)
);

CREATE TABLE npc_corporations (
    id                          INTEGER PRIMARY KEY,
    ceo_id                      INTEGER REFERENCES npc_characters(id),
    deleted                     INTEGER,
    extent                      TEXT,
    faction_id                  INTEGER REFERENCES factions(id),
    enemy_id                    INTEGER,
    friend_id                   INTEGER,
    icon_id                     INTEGER REFERENCES icons(id),
    main_activity_id            INTEGER REFERENCES corporation_activities(id),
    member_limit                INTEGER,
    min_security                REAL,
    minimum_join_standing       INTEGER,
    race_id                     INTEGER REFERENCES races(id),
    shares                      INTEGER,
    size                        TEXT,
    size_factor                 REAL,
    solar_system_id             INTEGER REFERENCES map_solar_systems(id),
    station_id                  INTEGER REFERENCES npc_stations(id),
    tax_rate                    REAL,
    ticker_name                 TEXT,
    unique_name                 INTEGER,
    send_char_termination_message INTEGER,
    has_player_personnel_manager  INTEGER,
    initial_price               INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

-- NPC standing trade table: typeID → effective standing value
CREATE TABLE npc_corporation_trades (
    corporation_id INTEGER NOT NULL REFERENCES npc_corporations(id),
    type_id        INTEGER NOT NULL REFERENCES types(id),
    value          REAL,
    PRIMARY KEY (corporation_id, type_id)
);

CREATE TABLE npc_corporation_divisions (
    corporation_id   INTEGER NOT NULL REFERENCES npc_corporations(id),
    division_type_id INTEGER NOT NULL REFERENCES npc_corporation_division_types(id),
    division_number  INTEGER,
    leader_id        INTEGER REFERENCES npc_characters(id),
    size             INTEGER,
    PRIMARY KEY (corporation_id, division_type_id)
);

CREATE TABLE npc_corporation_investors (
    corporation_id INTEGER NOT NULL REFERENCES npc_corporations(id),
    investor_id    INTEGER NOT NULL,
    shares         INTEGER,
    PRIMARY KEY (corporation_id, investor_id)
);

CREATE TABLE npc_corporation_lp_tables (
    corporation_id INTEGER NOT NULL REFERENCES npc_corporations(id),
    table_id       INTEGER NOT NULL,
    PRIMARY KEY (corporation_id, table_id)
);

CREATE TABLE npc_corporation_allowed_races (
    corporation_id INTEGER NOT NULL REFERENCES npc_corporations(id),
    race_id        INTEGER NOT NULL REFERENCES races(id),
    PRIMARY KEY (corporation_id, race_id)
);

-- -------------------------------------------------------------------------
-- Misc
-- -------------------------------------------------------------------------

CREATE TABLE sovereignty_upgrades (
    type_id                  INTEGER PRIMARY KEY REFERENCES types(id),
    fuel                     TEXT,
    mutually_exclusive_group INTEGER,
    power_allocation         INTEGER,
    workforce_allocation     INTEGER
);

CREATE TABLE control_tower_resources (
    tower_type_id    INTEGER NOT NULL REFERENCES types(id),
    resource_type_id INTEGER NOT NULL REFERENCES types(id),
    purpose          INTEGER,
    quantity         INTEGER,
    PRIMARY KEY (tower_type_id, resource_type_id)
);

CREATE TABLE contraband_types (
    type_id             INTEGER NOT NULL REFERENCES types(id),
    faction_id          INTEGER NOT NULL REFERENCES factions(id),
    attack_min_sec      REAL,
    confiscate_min_sec  REAL,
    fine_by_value       REAL,
    standing_loss       REAL,
    PRIMARY KEY (type_id, faction_id)
);

CREATE TABLE compressible_types (
    type_id          INTEGER PRIMARY KEY REFERENCES types(id),
    compressed_type_id INTEGER REFERENCES types(id)
);

CREATE TABLE agents_in_space (
    id              INTEGER PRIMARY KEY,
    dungeon_id      INTEGER,
    solar_system_id INTEGER REFERENCES map_solar_systems(id),
    spawn_point_id  INTEGER,
    type_id         INTEGER REFERENCES types(id)
);

CREATE TABLE landmarks (
    id      INTEGER PRIMARY KEY,
    icon_id INTEGER REFERENCES icons(id),
    pos_x REAL, pos_y REAL, pos_z REAL,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

-- Dynamic item (mutaplasmid) attribute ranges
CREATE TABLE dynamic_item_attributes (
    type_id      INTEGER NOT NULL REFERENCES types(id),
    attribute_id INTEGER NOT NULL REFERENCES dogma_attributes(id),
    min_modifier REAL,
    max_modifier REAL,
    PRIMARY KEY (type_id, attribute_id)
);

-- Maps mutaplasmid + applicable base type → resulting abyssal type
CREATE TABLE dynamic_item_output_mapping (
    type_id            INTEGER NOT NULL REFERENCES types(id),
    applicable_type_id INTEGER NOT NULL REFERENCES types(id),
    resulting_type_id  INTEGER NOT NULL REFERENCES types(id),
    PRIMARY KEY (type_id, applicable_type_id)
);

CREATE TABLE mercenary_tactical_operations (
    id                 INTEGER PRIMARY KEY,
    anarchy_impact     INTEGER,
    development_impact INTEGER,
    infomorph_bonus    INTEGER,
    name_en TEXT, name_de TEXT, name_es TEXT, name_fr TEXT,
    name_ja TEXT, name_ko TEXT, name_ru TEXT, name_zh TEXT,
    description_en TEXT, description_de TEXT, description_es TEXT, description_fr TEXT,
    description_ja TEXT, description_ko TEXT, description_ru TEXT, description_zh TEXT
);

CREATE TABLE dbuff_collections (
    id                    INTEGER PRIMARY KEY,
    aggregate_mode        TEXT,
    developer_description TEXT,
    display_name          TEXT,
    operation_name        TEXT,
    show_output_value_in_ui TEXT
);

CREATE TABLE dbuff_item_modifiers (
    dbuff_id         INTEGER NOT NULL REFERENCES dbuff_collections(id),
    dogma_attribute_id INTEGER NOT NULL REFERENCES dogma_attributes(id),
    PRIMARY KEY (dbuff_id, dogma_attribute_id)
);

CREATE TABLE dbuff_location_modifiers (
    dbuff_id           INTEGER NOT NULL REFERENCES dbuff_collections(id),
    dogma_attribute_id INTEGER NOT NULL REFERENCES dogma_attributes(id),
    PRIMARY KEY (dbuff_id, dogma_attribute_id)
);

CREATE TABLE dbuff_location_group_modifiers (
    dbuff_id           INTEGER NOT NULL REFERENCES dbuff_collections(id),
    dogma_attribute_id INTEGER NOT NULL REFERENCES dogma_attributes(id),
    group_id           INTEGER NOT NULL REFERENCES groups(id),
    PRIMARY KEY (dbuff_id, dogma_attribute_id, group_id)
);

CREATE TABLE dbuff_location_skill_modifiers (
    dbuff_id           INTEGER NOT NULL REFERENCES dbuff_collections(id),
    dogma_attribute_id INTEGER NOT NULL REFERENCES dogma_attributes(id),
    skill_id           INTEGER NOT NULL REFERENCES types(id),
    PRIMARY KEY (dbuff_id, dogma_attribute_id, skill_id)
);

-- Stored as JSON blob due to deeply nested, schema-like structure
CREATE TABLE freelance_job_schemas (
    id   INTEGER PRIMARY KEY,
    data TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sde_file_hashes (
    filename TEXT PRIMARY KEY,
    sha256   TEXT NOT NULL
);
"""


# ---------------------------------------------------------------------------
# Loaders (one per JSONL file)
# ---------------------------------------------------------------------------

def load_sde_meta(conn, path):
    rows = [(o['buildNumber'], o['releaseDate']) for o in load_jsonl(path)]
    conn.executemany('INSERT INTO sde_meta VALUES (?, ?)', rows)


def load_icons(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('iconFile'))
    bulk_insert(conn, 'INSERT INTO icons VALUES (?, ?)', gen())


def load_graphics(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('graphicFile'), o.get('iconFolder'),
                   o.get('sofFactionName'), o.get('sofHullName'), o.get('sofRaceName'))
    bulk_insert(conn, 'INSERT INTO graphics VALUES (?, ?, ?, ?, ?, ?)', gen())


def load_translation_languages(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('name'))
    bulk_insert(conn, 'INSERT INTO translation_languages VALUES (?, ?)', gen())


def load_dogma_attribute_categories(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('name'), o.get('description'))
    bulk_insert(conn, 'INSERT INTO dogma_attribute_categories VALUES (?, ?, ?)', gen())


def load_dogma_units(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('name'), _en(o.get('description')), _en(o.get('displayName')))
    bulk_insert(conn, 'INSERT INTO dogma_units VALUES (?, ?, ?, ?)', gen())


def load_agent_types(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('name'))
    bulk_insert(conn, 'INSERT INTO agent_types VALUES (?, ?)', gen())


def load_corporation_activities(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], _en(o.get('name')))
    bulk_insert(conn, 'INSERT INTO corporation_activities VALUES (?, ?)', gen())


def load_npc_corporation_division_types(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], _en(o.get('name')), o.get('displayName'),
                   _en(o.get('description')), o.get('internalName'), _en(o.get('leaderTypeName')))
    bulk_insert(conn,
        'INSERT INTO npc_corporation_division_types VALUES (?, ?, ?, ?, ?, ?)', gen())


def load_station_services(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], _en(o.get('serviceName')), _en(o.get('description')))
    bulk_insert(conn, 'INSERT INTO station_services VALUES (?, ?, ?)', gen())


def load_clone_grades(conn, path):
    grades, skills = [], []
    for o in load_jsonl(path):
        grades.append((o['_key'], o.get('name')))
        for s in o.get('skills', []):
            skills.append((o['_key'], s['typeID'], s['level']))
    conn.executemany('INSERT INTO clone_grades VALUES (?, ?)', grades)
    bulk_insert(conn, 'INSERT INTO clone_grade_skills VALUES (?, ?, ?)', iter(skills))


def load_categories(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('published'), *ml(o, 'name'))
    bulk_insert(conn,
        'INSERT INTO categories VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_groups(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('categoryID'), o.get('anchorable'),
                   o.get('anchored'), o.get('fittableNonSingleton'),
                   o.get('published'), o.get('useBasePrice'), *ml(o, 'name'))
    bulk_insert(conn,
        'INSERT INTO groups VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_meta_groups(conn, path):
    def gen():
        for o in load_jsonl(path):
            color = o.get('color')
            yield (o['_key'], json.dumps(color) if color else None, o.get('iconID'), o.get('iconSuffix'),
                   *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO meta_groups VALUES (?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_market_groups(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('parentGroupID'), o.get('hasTypes'),
                   o.get('iconID'), *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO market_groups VALUES (?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_dogma_attributes(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('attributeCategoryID'), o.get('dataType'),
                   o.get('defaultValue'), o.get('description'), o.get('displayWhenZero'),
                   o.get('highIsGood'), o.get('iconID'), o.get('name'),
                   o.get('published'), o.get('stackable'), o.get('unitID'),
                   *ml(o, 'displayName'),
                   *ml(o, 'tooltipDescription'),
                   *ml(o, 'tooltipTitle'))
    bulk_insert(conn,
        'INSERT INTO dogma_attributes VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_dogma_effects(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('disallowAutoRepeat'), o.get('dischargeAttributeID'),
                   o.get('distribution'), o.get('durationAttributeID'),
                   o.get('effectCategoryID'), o.get('electronicChance'),
                   o.get('falloffAttributeID'), o.get('guid'),
                   o.get('isAssistance'), o.get('isOffensive'), o.get('isWarpSafe'),
                   o.get('name'), o.get('propulsionChance'), o.get('published'),
                   o.get('rangeAttributeID'), o.get('rangeChance'),
                   o.get('trackingSpeedAttributeID'))
    bulk_insert(conn,
        'INSERT INTO dogma_effects VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        gen())


def load_types(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('groupID'), o.get('mass'), o.get('portionSize'),
                   o.get('published'), o.get('volume'), o.get('capacity'),
                   o.get('basePrice'), o.get('marketGroupID'), o.get('metaGroupID'),
                   o.get('metaLevel'), o.get('iconID'), o.get('graphicID'),
                   o.get('soundID'), o.get('raceID'), o.get('radius'),
                   o.get('variationParentTypeID'),
                   *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO types VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_type_dogma(conn, path):
    def gen_attrs():
        for o in load_jsonl(path):
            type_id = o['_key']
            for a in o.get('dogmaAttributes', []):
                yield (type_id, a['attributeID'], a.get('value'))

    def gen_effects():
        for o in load_jsonl(path):
            type_id = o['_key']
            for e in o.get('dogmaEffects', []):
                yield (type_id, e['effectID'], e.get('isDefault'))

    bulk_insert(conn,
        'INSERT INTO type_dogma_attributes VALUES (?, ?, ?)', gen_attrs())
    bulk_insert(conn,
        'INSERT INTO type_dogma_effects VALUES (?, ?, ?)', gen_effects())


def load_type_materials(conn, path):
    def gen():
        for o in load_jsonl(path):
            type_id = o['_key']
            for m in o.get('materials', []):
                yield (type_id, m['materialTypeID'], m['quantity'])
    bulk_insert(conn, 'INSERT INTO type_materials VALUES (?, ?, ?)', gen())


def load_type_bonus(conn, path):
    role_rows, skill_rows = [], []
    for o in load_jsonl(path):
        type_id = o['_key']
        for b in o.get('roleBonuses', []):
            role_rows.append((
                None, type_id, b.get('bonus'), b.get('unitID'), b.get('importance'),
                *ml(b, 'bonusText')
            ))
        for entry in o.get('types', []):
            skill_id = entry['_key']
            for b in entry.get('_value', []):
                skill_rows.append((
                    None, type_id, skill_id, b.get('bonus'), b.get('unitID'),
                    b.get('importance'), *ml(b, 'bonusText')
                ))
    bulk_insert(conn,
        'INSERT INTO type_role_bonuses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        iter(role_rows))
    bulk_insert(conn,
        'INSERT INTO type_skill_bonuses VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        iter(skill_rows))


def load_blueprints(conn, path):
    bps, activities, materials, products, skills = [], [], [], [], []
    for o in load_jsonl(path):
        tid = o['_key']
        bps.append((tid, o.get('maxProductionLimit')))
        for act_name, act in o.get('activities', {}).items():
            activities.append((tid, act_name, act.get('time')))
            for m in act.get('materials', []):
                materials.append((tid, act_name, m['typeID'], m['quantity']))
            for p in act.get('products', []):
                products.append((tid, act_name, p['typeID'],
                                 p.get('quantity'), p.get('probability')))
            for s in act.get('skills', []):
                skills.append((tid, act_name, s['typeID'], s['level']))
    conn.executemany('INSERT INTO blueprints VALUES (?, ?)', bps)
    bulk_insert(conn,
        'INSERT INTO blueprint_activities VALUES (?, ?, ?)', iter(activities))
    bulk_insert(conn,
        'INSERT INTO blueprint_activity_materials VALUES (?, ?, ?, ?)', iter(materials))
    bulk_insert(conn,
        'INSERT INTO blueprint_activity_products VALUES (?, ?, ?, ?, ?)', iter(products))
    bulk_insert(conn,
        'INSERT INTO blueprint_activity_skills VALUES (?, ?, ?, ?)', iter(skills))


def load_races(conn, path):
    rows, skill_rows = [], []
    for o in load_jsonl(path):
        rows.append((o['_key'], o.get('iconID'), o.get('shipTypeID'),
                     *ml(o, 'name'), *ml(o, 'description')))
        for s in o.get('skills', []):
            skill_rows.append((o['_key'], s['_key'], s['_value']))
    conn.executemany(
        'INSERT INTO races VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        rows)
    bulk_insert(conn, 'INSERT INTO race_skills VALUES (?, ?, ?)', iter(skill_rows))


def load_bloodlines(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('raceID'), o.get('corporationID'), o.get('iconID'),
                   o.get('charisma'), o.get('intelligence'), o.get('memory'),
                   o.get('perception'), o.get('willpower'),
                   *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO bloodlines VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_ancestries(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('bloodlineID'), o.get('iconID'),
                   o.get('charisma'), o.get('intelligence'), o.get('memory'),
                   o.get('perception'), o.get('willpower'),
                   *ml(o, 'name'), *ml(o, 'description'), *ml(o, 'shortDescription'))
    bulk_insert(conn,
        'INSERT INTO ancestries VALUES (?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_character_attributes(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('iconID'), _en(o.get('name')),
                   o.get('description'), o.get('notes'), o.get('shortDescription'))
    bulk_insert(conn,
        'INSERT INTO character_attributes VALUES (?, ?, ?, ?, ?, ?)', gen())


def load_factions(conn, path):
    rows, member_rows = [], []
    for o in load_jsonl(path):
        rows.append((
            o['_key'], o.get('corporationID'), o.get('militiaCorporationID'),
            o.get('solarSystemID'), o.get('iconID'), o.get('sizeFactor'),
            o.get('flatLogo'), o.get('flatLogoWithName'), o.get('uniqueName'),
            *ml(o, 'name'), *ml(o, 'description'), *ml(o, 'shortDescription')
        ))
        for race_id in o.get('memberRaces', []):
            member_rows.append((o['_key'], race_id))
    conn.executemany(
        'INSERT INTO factions VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)',
        rows)
    bulk_insert(conn, 'INSERT INTO faction_member_races VALUES (?, ?)', iter(member_rows))


def load_skin_materials(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('materialSetID'), *ml(o, 'displayName'))
    bulk_insert(conn,
        'INSERT INTO skin_materials VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_skins(conn, path):
    skin_rows, type_rows = [], []
    for o in load_jsonl(path):
        skin_rows.append((o['_key'], o.get('allowCCPDevs'), o.get('internalName'),
                          o.get('skinMaterialID'), o.get('visibleSerenity'),
                          o.get('visibleTranquility')))
        for type_id in o.get('types', []):
            type_rows.append((o['_key'], type_id))
    conn.executemany('INSERT INTO skins VALUES (?, ?, ?, ?, ?, ?)', skin_rows)
    bulk_insert(conn, 'INSERT INTO skin_types VALUES (?, ?)', iter(type_rows))


def load_skin_licenses(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('licenseTypeID'), o.get('skinID'), o.get('duration'))
    bulk_insert(conn, 'INSERT INTO skin_licenses VALUES (?, ?, ?, ?)', gen())


def load_planet_schematics(conn, path):
    schematic_rows, pin_rows, type_rows = [], [], []
    for o in load_jsonl(path):
        sid = o['_key']
        schematic_rows.append((sid, o.get('cycleTime'), *ml(o, 'name')))
        for pin_id in o.get('pins', []):
            pin_rows.append((sid, pin_id))
        for t in o.get('types', []):
            type_rows.append((sid, t['_key'], t.get('isInput'), t.get('quantity')))
    conn.executemany(
        'INSERT INTO planet_schematics VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        schematic_rows)
    bulk_insert(conn, 'INSERT INTO planet_schematic_pins VALUES (?, ?)', iter(pin_rows))
    bulk_insert(conn,
        'INSERT INTO planet_schematic_types VALUES (?, ?, ?, ?)', iter(type_rows))


def load_planet_resources(conn, path):
    def gen():
        for o in load_jsonl(path):
            r = o.get('reagent')
            yield (o['_key'], o.get('power'), o.get('workforce'), json.dumps(r) if r else None)
    bulk_insert(conn, 'INSERT INTO planet_resources VALUES (?, ?, ?, ?)', gen())


def load_certificates(conn, path):
    cert_rows, rec_rows, skill_rows = [], [], []
    for o in load_jsonl(path):
        cid = o['_key']
        cert_rows.append((cid, o.get('groupID'), *ml(o, 'name'), *ml(o, 'description')))
        for type_id in o.get('recommendedFor', []):
            rec_rows.append((cid, type_id))
        for s in o.get('skillTypes', []):
            skill_rows.append((cid, s['_key'], s.get('basic'), s.get('standard'),
                                s.get('improved'), s.get('advanced'), s.get('elite')))
    conn.executemany(
        'INSERT INTO certificates VALUES (?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)',
        cert_rows)
    bulk_insert(conn,
        'INSERT INTO certificate_recommended_for VALUES (?, ?)', iter(rec_rows))
    bulk_insert(conn,
        'INSERT INTO certificate_skill_types VALUES (?, ?, ?, ?, ?, ?, ?)', iter(skill_rows))


def load_masteries(conn, path):
    def gen():
        for o in load_jsonl(path):
            type_id = o['_key']
            for level_entry in o.get('_value', []):
                level = level_entry['_key']
                for cert_id in level_entry.get('_value', []):
                    yield (type_id, level, cert_id)
    bulk_insert(conn, 'INSERT INTO masteries VALUES (?, ?, ?)', gen())


def load_map_regions(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            yield (o['_key'], o.get('factionID'), o.get('nebulaID'),
                   o.get('wormholeClassID'), x, y, z,
                   *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO map_regions VALUES (?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_map_constellations(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            yield (o['_key'], o.get('regionID'), o.get('factionID'),
                   o.get('wormholeClassID'), x, y, z, *ml(o, 'name'))
    bulk_insert(conn,
        'INSERT INTO map_constellations VALUES (?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_map_solar_systems(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            p2d = o.get('position2D') or {}
            yield (o['_key'], o.get('constellationID'), o.get('regionID'),
                   o.get('starID'), o.get('border'), o.get('corridor'),
                   o.get('fringe'), o.get('hub'), o.get('international'),
                   o.get('regional'), o.get('luminosity'), o.get('radius'),
                   o.get('securityStatus'), o.get('securityClass'),
                   o.get('wormholeClassID'), x, y, z,
                   p2d.get('x'), p2d.get('y'), *ml(o, 'name'))
    bulk_insert(conn,
        'INSERT INTO map_solar_systems VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_map_stars(conn, path):
    def gen():
        for o in load_jsonl(path):
            s = o.get('statistics') or {}
            yield (o['_key'], o.get('solarSystemID'), o.get('typeID'), o.get('radius'),
                   s.get('age'), s.get('life'), s.get('luminosity'),
                   s.get('spectralClass'), s.get('temperature'))
    bulk_insert(conn,
        'INSERT INTO map_stars VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)', gen())


def _planet_moon_row(o):
    x, y, z = pos(o)
    a = o.get('attributes') or {}
    s = o.get('statistics') or {}
    return (
        o['_key'], o.get('solarSystemID'), o.get('typeID'),
        o.get('celestialIndex'), o.get('orbitID'), o.get('radius'), x, y, z,
        a.get('heightMap1'), a.get('heightMap2'), a.get('population'), a.get('shaderPreset'),
        s.get('density'), s.get('eccentricity'), s.get('escapeVelocity'), s.get('locked'),
        s.get('massDust'), s.get('massGas'), s.get('orbitPeriod'), s.get('orbitRadius'),
        s.get('pressure'), s.get('rotationRate'), s.get('spectralClass'),
        s.get('surfaceGravity'), s.get('temperature'),
    )


def load_map_planets(conn, path):
    bulk_insert(conn,
        'INSERT INTO map_planets VALUES ('
        '?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        (_planet_moon_row(o) for o in load_jsonl(path)))


def load_map_moons(conn, path):
    def gen():
        for o in load_jsonl(path):
            r = _planet_moon_row(o)
            # insert orbitIndex after orbitID (index 4)
            return r[:5] + (o.get('orbitIndex'),) + r[5:]

    def gen2():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            a = o.get('attributes') or {}
            s = o.get('statistics') or {}
            yield (
                o['_key'], o.get('solarSystemID'), o.get('typeID'),
                o.get('celestialIndex'), o.get('orbitID'), o.get('orbitIndex'),
                o.get('radius'), x, y, z,
                a.get('heightMap1'), a.get('heightMap2'), a.get('population'), a.get('shaderPreset'),
                s.get('density'), s.get('eccentricity'), s.get('escapeVelocity'), s.get('locked'),
                s.get('massDust'), s.get('massGas'), s.get('orbitPeriod'), s.get('orbitRadius'),
                s.get('pressure'), s.get('rotationRate'), s.get('spectralClass'),
                s.get('surfaceGravity'), s.get('temperature'),
            )

    bulk_insert(conn,
        'INSERT INTO map_moons VALUES ('
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        gen2())


def load_map_asteroid_belts(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            s = o.get('statistics') or {}
            yield (
                o['_key'], o.get('solarSystemID'), o.get('typeID'),
                o.get('celestialIndex'), o.get('orbitID'), o.get('orbitIndex'),
                o.get('radius'), x, y, z,
                s.get('density'), s.get('eccentricity'), s.get('escapeVelocity'), s.get('locked'),
                s.get('massDust'), s.get('massGas'), s.get('orbitPeriod'), s.get('orbitRadius'),
                s.get('pressure'), s.get('rotationRate'), s.get('spectralClass'),
                s.get('surfaceGravity'), s.get('temperature'),
            )
    bulk_insert(conn,
        'INSERT INTO map_asteroid_belts VALUES ('
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        gen())


def load_map_stargates(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            dest = o.get('destination') or {}
            yield (o['_key'], o.get('solarSystemID'), o.get('typeID'),
                   dest.get('solarSystemID'), dest.get('stargateID'), x, y, z)
    bulk_insert(conn,
        'INSERT INTO map_stargates VALUES (?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_map_secondary_suns(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            yield (o['_key'], o.get('solarSystemID'), o.get('typeID'),
                   o.get('effectBeaconTypeID'), x, y, z)
    bulk_insert(conn,
        'INSERT INTO map_secondary_suns VALUES (?, ?, ?, ?, ?, ?, ?)', gen())


def load_station_operations(conn, path):
    op_rows, svc_rows, stype_rows = [], [], []
    for o in load_jsonl(path):
        oid = o['_key']
        op_rows.append((
            oid, o.get('activityID'), o.get('border'), o.get('corridor'),
            o.get('fringe'), o.get('hub'), o.get('manufacturingFactor'),
            o.get('ratio'), o.get('researchFactor'),
            *ml(o, 'operationName'), *ml(o, 'description')
        ))
        for svc_id in o.get('services', []):
            svc_rows.append((oid, svc_id))
        for entry in o.get('stationTypes', []):
            stype_rows.append((oid, entry['_key'], entry['_value']))
    conn.executemany(
        'INSERT INTO station_operations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)',
        op_rows)
    bulk_insert(conn,
        'INSERT INTO station_operation_services VALUES (?, ?)', iter(svc_rows))
    bulk_insert(conn,
        'INSERT INTO station_operation_station_types VALUES (?, ?, ?)', iter(stype_rows))


def load_npc_stations(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            yield (o['_key'], o.get('solarSystemID'), o.get('typeID'),
                   o.get('ownerID'), o.get('operationID'),
                   o.get('orbitID'), o.get('orbitIndex'), o.get('celestialIndex'),
                   o.get('reprocessingEfficiency'), o.get('reprocessingHangarFlag'),
                   o.get('reprocessingStationsTake'), o.get('useOperationName'),
                   x, y, z)
    bulk_insert(conn,
        'INSERT INTO npc_stations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
        gen())


def load_npc_characters(conn, path):
    char_rows, skill_rows = [], []
    for o in load_jsonl(path):
        char_rows.append((
            o['_key'], o.get('corporationID'), o.get('ancestryID'),
            o.get('bloodlineID'), o.get('careerID'), o.get('ceo'),
            o.get('gender'), o.get('locationID'), o.get('raceID'),
            o.get('schoolID'), o.get('specialityID'), o.get('startDate'),
            o.get('uniqueName'), *ml(o, 'name')
        ))
        for s in o.get('skills', []):
            skill_rows.append((o['_key'], s['typeID'], s.get('level')))
    conn.executemany(
        'INSERT INTO npc_characters VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)',
        char_rows)
    bulk_insert(conn,
        'INSERT INTO npc_character_skills VALUES (?, ?, ?)', iter(skill_rows))


def load_npc_corporations(conn, path):
    corp_rows, trade_rows, div_rows, inv_rows, lp_rows, race_rows = \
        [], [], [], [], [], []

    for o in load_jsonl(path):
        cid = o['_key']
        corp_rows.append((
            cid, o.get('ceoID'), o.get('deleted'), o.get('extent'),
            o.get('factionID'), o.get('enemyID'), o.get('friendID'),
            o.get('iconID'), o.get('mainActivityID'), o.get('memberLimit'),
            o.get('minSecurity'), o.get('minimumJoinStanding'), o.get('raceID'),
            o.get('shares'), o.get('size'), o.get('sizeFactor'),
            o.get('solarSystemID'), o.get('stationID'), o.get('taxRate'),
            o.get('tickerName'), o.get('uniqueName'),
            o.get('sendCharTerminationMessage'), o.get('hasPlayerPersonnelManager'),
            o.get('initialPrice'),
            *ml(o, 'name'), *ml(o, 'description')
        ))
        for entry in o.get('corporationTrades', []):
            trade_rows.append((cid, entry['_key'], entry['_value']))
        for div in o.get('divisions', []):
            div_rows.append((cid, div['_key'], div.get('divisionNumber'),
                             div.get('leaderID'), div.get('size')))
        for inv in o.get('investors', []):
            inv_rows.append((cid, inv['_key'], inv['_value']))
        for tbl_id in o.get('lpOfferTables', []):
            lp_rows.append((cid, tbl_id))
        for race_id in o.get('allowedMemberRaces', []):
            race_rows.append((cid, race_id))

    conn.executemany(
        'INSERT INTO npc_corporations VALUES ('
        '?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)',
        corp_rows)
    bulk_insert(conn,
        'INSERT INTO npc_corporation_trades VALUES (?, ?, ?)', iter(trade_rows))
    bulk_insert(conn,
        'INSERT INTO npc_corporation_divisions VALUES (?, ?, ?, ?, ?)', iter(div_rows))
    bulk_insert(conn,
        'INSERT INTO npc_corporation_investors VALUES (?, ?, ?)', iter(inv_rows))
    bulk_insert(conn,
        'INSERT INTO npc_corporation_lp_tables VALUES (?, ?)', iter(lp_rows))
    bulk_insert(conn,
        'INSERT INTO npc_corporation_allowed_races VALUES (?, ?)', iter(race_rows))


def load_sovereignty_upgrades(conn, path):
    def gen():
        for o in load_jsonl(path):
            f = o.get('fuel')
            yield (o['_key'], json.dumps(f) if f else None, o.get('mutually_exclusive_group'),
                   o.get('power_allocation'), o.get('workforce_allocation'))
    bulk_insert(conn,
        'INSERT INTO sovereignty_upgrades VALUES (?, ?, ?, ?, ?)', gen())


def load_control_tower_resources(conn, path):
    def gen():
        for o in load_jsonl(path):
            for r in o.get('resources', []):
                yield (o['_key'], r['resourceTypeID'], r.get('purpose'), r.get('quantity'))
    bulk_insert(conn,
        'INSERT INTO control_tower_resources VALUES (?, ?, ?, ?)', gen())


def load_contraband_types(conn, path):
    def gen():
        for o in load_jsonl(path):
            for f in o.get('factions', []):
                yield (o['_key'], f['_key'], f.get('attackMinSec'),
                       f.get('confiscateMinSec'), f.get('fineByValue'), f.get('standingLoss'))
    bulk_insert(conn,
        'INSERT INTO contraband_types VALUES (?, ?, ?, ?, ?, ?)', gen())


def load_compressible_types(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('compressedTypeID'))
    bulk_insert(conn, 'INSERT INTO compressible_types VALUES (?, ?)', gen())


def load_agents_in_space(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('dungeonID'), o.get('solarSystemID'),
                   o.get('spawnPointID'), o.get('typeID'))
    bulk_insert(conn,
        'INSERT INTO agents_in_space VALUES (?, ?, ?, ?, ?)', gen())


def load_landmarks(conn, path):
    def gen():
        for o in load_jsonl(path):
            x, y, z = pos(o)
            yield (o['_key'], o.get('iconID'), x, y, z,
                   *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO landmarks VALUES (?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_dynamic_item_attributes(conn, path):
    attr_rows, mapping_rows = [], []
    for o in load_jsonl(path):
        tid = o['_key']
        for a in o.get('attributeIDs', []):
            attr_rows.append((tid, a['_key'], a.get('min'), a.get('max')))
        for mapping in o.get('inputOutputMapping', []):
            result_type = mapping.get('resultingType')
            for app_type in mapping.get('applicableTypes', []):
                mapping_rows.append((tid, app_type, result_type))
    bulk_insert(conn,
        'INSERT INTO dynamic_item_attributes VALUES (?, ?, ?, ?)', iter(attr_rows))
    bulk_insert(conn,
        'INSERT INTO dynamic_item_output_mapping VALUES (?, ?, ?)', iter(mapping_rows))


def load_mercenary_tactical_operations(conn, path):
    def gen():
        for o in load_jsonl(path):
            yield (o['_key'], o.get('anarchy_impact'), o.get('development_impact'),
                   o.get('infomorph_bonus'), *ml(o, 'name'), *ml(o, 'description'))
    bulk_insert(conn,
        'INSERT INTO mercenary_tactical_operations VALUES (?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?, '
        '?, ?, ?, ?, ?, ?, ?, ?)', gen())


def load_dbuff_collections(conn, path):
    coll_rows, item_rows, loc_rows, loc_grp_rows, loc_skill_rows = \
        [], [], [], [], []

    for o in load_jsonl(path):
        did = o['_key']
        coll_rows.append((did, o.get('aggregateMode'), o.get('developerDescription'),
                          _en(o.get('displayName')), o.get('operationName'),
                          o.get('showOutputValueInUI')))
        for m in o.get('itemModifiers', []):
            item_rows.append((did, m['dogmaAttributeID']))
        for m in o.get('locationModifiers', []):
            loc_rows.append((did, m['dogmaAttributeID']))
        for m in o.get('locationGroupModifiers', []):
            loc_grp_rows.append((did, m['dogmaAttributeID'], m['groupID']))
        for m in o.get('locationRequiredSkillModifiers', []):
            loc_skill_rows.append((did, m['dogmaAttributeID'], m['skillID']))

    conn.executemany(
        'INSERT INTO dbuff_collections VALUES (?, ?, ?, ?, ?, ?)', coll_rows)
    bulk_insert(conn,
        'INSERT INTO dbuff_item_modifiers VALUES (?, ?)', iter(item_rows))
    bulk_insert(conn,
        'INSERT INTO dbuff_location_modifiers VALUES (?, ?)', iter(loc_rows))
    bulk_insert(conn,
        'INSERT INTO dbuff_location_group_modifiers VALUES (?, ?, ?)', iter(loc_grp_rows))
    bulk_insert(conn,
        'INSERT INTO dbuff_location_skill_modifiers VALUES (?, ?, ?)', iter(loc_skill_rows))


def load_freelance_job_schemas(conn, path):
    rows = []
    for o in load_jsonl(path):
        rows.append((o['_key'], json.dumps(o.get('_value'))))
    conn.executemany('INSERT INTO freelance_job_schemas VALUES (?, ?)', rows)


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

LOADERS = [
    # (JSONL stem, loader function, [owned tables]) — dependency order
    ('_sde',                      load_sde_meta,                     ['sde_meta']),
    ('icons',                     load_icons,                        ['icons']),
    ('graphics',                  load_graphics,                     ['graphics']),
    ('translationLanguages',      load_translation_languages,        ['translation_languages']),
    ('dogmaAttributeCategories',  load_dogma_attribute_categories,   ['dogma_attribute_categories']),
    ('dogmaUnits',                load_dogma_units,                  ['dogma_units']),
    ('agentTypes',                load_agent_types,                  ['agent_types']),
    ('corporationActivities',     load_corporation_activities,       ['corporation_activities']),
    ('npcCorporationDivisions',   load_npc_corporation_division_types, ['npc_corporation_division_types']),
    ('stationServices',           load_station_services,             ['station_services']),
    ('cloneGrades',               load_clone_grades,                 ['clone_grades', 'clone_grade_skills']),
    ('categories',                load_categories,                   ['categories']),
    ('groups',                    load_groups,                       ['groups']),
    ('metaGroups',                load_meta_groups,                  ['meta_groups']),
    ('marketGroups',              load_market_groups,                ['market_groups']),
    ('dogmaAttributes',           load_dogma_attributes,             ['dogma_attributes']),
    ('dogmaEffects',              load_dogma_effects,                ['dogma_effects']),
    ('types',                     load_types,                        ['types']),
    ('typeDogma',                 load_type_dogma,                   ['type_dogma_attributes', 'type_dogma_effects']),
    ('typeMaterials',             load_type_materials,               ['type_materials']),
    ('typeBonus',                 load_type_bonus,                   ['type_role_bonuses', 'type_skill_bonuses']),
    ('blueprints',                load_blueprints,                   ['blueprints', 'blueprint_activities',
                                                                      'blueprint_activity_materials',
                                                                      'blueprint_activity_products',
                                                                      'blueprint_activity_skills']),
    ('races',                     load_races,                        ['races', 'race_skills']),
    ('bloodlines',                load_bloodlines,                   ['bloodlines']),
    ('ancestries',                load_ancestries,                   ['ancestries']),
    ('characterAttributes',       load_character_attributes,         ['character_attributes']),
    ('factions',                  load_factions,                     ['factions', 'faction_member_races']),
    ('skinMaterials',             load_skin_materials,               ['skin_materials']),
    ('skins',                     load_skins,                        ['skins', 'skin_types']),
    ('skinLicenses',              load_skin_licenses,                ['skin_licenses']),
    ('planetSchematics',          load_planet_schematics,            ['planet_schematics', 'planet_schematic_pins',
                                                                      'planet_schematic_types']),
    ('planetResources',           load_planet_resources,             ['planet_resources']),
    ('certificates',              load_certificates,                 ['certificates', 'certificate_recommended_for',
                                                                      'certificate_skill_types']),
    ('masteries',                 load_masteries,                    ['masteries']),
    ('map_regions',               load_map_regions,                  ['map_regions']),       # file: mapRegions.jsonl
    ('map_constellations',        load_map_constellations,           ['map_constellations']),
    ('map_solar_systems',         load_map_solar_systems,            ['map_solar_systems']),
    ('map_stars',                 load_map_stars,                    ['map_stars']),
    ('map_planets',               load_map_planets,                  ['map_planets']),
    ('map_moons',                 load_map_moons,                    ['map_moons']),
    ('map_asteroid_belts',        load_map_asteroid_belts,           ['map_asteroid_belts']),
    ('map_stargates',             load_map_stargates,                ['map_stargates']),
    ('map_secondary_suns',        load_map_secondary_suns,           ['map_secondary_suns']),
    ('stationOperations',         load_station_operations,           ['station_operations',
                                                                      'station_operation_services',
                                                                      'station_operation_station_types']),
    ('npcStations',               load_npc_stations,                 ['npc_stations']),
    ('npcCharacters',             load_npc_characters,               ['npc_characters', 'npc_character_skills']),
    ('npcCorporations',           load_npc_corporations,             ['npc_corporations', 'npc_corporation_trades',
                                                                      'npc_corporation_divisions',
                                                                      'npc_corporation_investors',
                                                                      'npc_corporation_lp_tables',
                                                                      'npc_corporation_allowed_races']),
    ('sovereigntyUpgrades',       load_sovereignty_upgrades,         ['sovereignty_upgrades']),
    ('controlTowerResources',     load_control_tower_resources,      ['control_tower_resources']),
    ('contrabandTypes',           load_contraband_types,             ['contraband_types']),
    ('compressibleTypes',         load_compressible_types,           ['compressible_types']),
    ('agentsInSpace',             load_agents_in_space,              ['agents_in_space']),
    ('landmarks',                 load_landmarks,                    ['landmarks']),
    ('dynamicItemAttributes',     load_dynamic_item_attributes,      ['dynamic_item_attributes',
                                                                      'dynamic_item_output_mapping']),
    ('mercenaryTacticalOperations', load_mercenary_tactical_operations, ['mercenary_tactical_operations']),
    ('dbuffCollections',          load_dbuff_collections,            ['dbuff_collections', 'dbuff_item_modifiers',
                                                                      'dbuff_location_modifiers',
                                                                      'dbuff_location_group_modifiers',
                                                                      'dbuff_location_skill_modifiers']),
    ('freelanceJobSchemas',       load_freelance_job_schemas,         ['freelance_job_schemas']),
]

# Map of canonical stem names → actual JSONL file stems (where they differ)
_FILE_ALIASES = {
    'map_regions':        'mapRegions',
    'map_constellations': 'mapConstellations',
    'map_solar_systems':  'mapSolarSystems',
    'map_stars':          'mapStars',
    'map_planets':        'mapPlanets',
    'map_moons':          'mapMoons',
    'map_asteroid_belts': 'mapAsteroidBelts',
    'map_stargates':      'mapStargates',
    'map_secondary_suns': 'mapSecondarySuns',
}


def _sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()


def load_all(conn, sde_dir):
    files = {p.stem: p for p in Path(sde_dir).glob('*.jsonl')}
    stored = dict(conn.execute('SELECT filename, sha256 FROM sde_file_hashes'))

    for name, loader, tables in LOADERS:
        file_stem = _FILE_ALIASES.get(name, name)
        if file_stem not in files:
            print(f'  skip  {file_stem}.jsonl (not found)')
            continue
        path = files[file_stem]
        digest = _sha256(path)
        if stored.get(file_stem) == digest:
            print(f'  skip  {file_stem}.jsonl (unchanged)')
            continue
        print(f'  load  {file_stem}.jsonl')
        with conn:
            for table in tables:
                conn.execute(f'DELETE FROM {table}')
            loader(conn, path)
            conn.execute(
                'INSERT OR REPLACE INTO sde_file_hashes VALUES (?, ?)',
                (file_stem, digest),
            )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    sde_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else SDE_DIR
    db_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DB_PATH

    fresh = not db_path.exists()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Remove stale WAL/SHM files — a fresh main DB with leftover companions
    # causes "database disk image is malformed" on the first connection.
    for suffix in ('-wal', '-shm'):
        sidecar = db_path.with_name(db_path.name + suffix)
        if sidecar.exists():
            sidecar.unlink()

    conn = sqlite3.connect(db_path)
    try:
        # Disable FK enforcement during bulk load to avoid circular-ref issues
        # (e.g. npc_corporations.ceo_id ↔ npc_characters.corporation_id).
        # Use DELETE journal during load (simpler, no WAL sidecars); switch to
        # WAL after the final commit so readers get concurrent-read benefits.
        conn.execute('PRAGMA foreign_keys = OFF')
        conn.execute('PRAGMA synchronous = NORMAL')
        if fresh:
            conn.executescript(SCHEMA)
            print('Schema created.')
        else:
            conn.execute('PRAGMA journal_mode = WAL')
            # Ensure the hashes table exists (handles DBs built before this feature)
            conn.execute(
                'CREATE TABLE IF NOT EXISTS sde_file_hashes '
                '(filename TEXT PRIMARY KEY, sha256 TEXT NOT NULL)'
            )
            print('Database exists — incremental update.')
        load_all(conn, sde_dir)
        conn.commit()
        if fresh:
            conn.execute('PRAGMA journal_mode = WAL')
            conn.commit()
        print('Done.')
    except Exception:
        conn.close()
        if fresh:
            for p in [db_path,
                      db_path.with_name(db_path.name + '-wal'),
                      db_path.with_name(db_path.name + '-shm')]:
                if p.exists():
                    p.unlink()
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    main()
