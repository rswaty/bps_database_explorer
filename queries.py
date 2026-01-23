"""
Pre-built SQL queries for the BPS database.
These can be used in the Custom Query interface or imported in other scripts.
"""

# Model Information Queries
GET_MODEL_BY_ID = """
SELECT * 
FROM bps_models 
WHERE bps_model_id = ?
"""

GET_MODELS_BY_VEGETATION_TYPE = """
SELECT 
    bps_model_id,
    vegetation_type,
    map_zones,
    geographic_range
FROM bps_models
WHERE vegetation_type LIKE ?
ORDER BY bps_model_id
"""

GET_MODELS_BY_MAP_ZONE = """
SELECT 
    bps_model_id,
    vegetation_type,
    map_zones
FROM bps_models
WHERE map_zones LIKE ?
ORDER BY bps_model_id
"""

# Modeler Queries
GET_MODELERS_BY_MODEL = """
SELECT 
    m.modelers as modeler_name,
    m.modeler_email,
    mod.reviewers,
    mod.reviewer_email
FROM models mod
JOIN modelers m ON mod.modeler_id = m.modeler_id
WHERE mod.bps_model_id = ?
"""

GET_MODELS_BY_MODELER = """
SELECT DISTINCT
    bm.bps_model_id,
    bm.vegetation_type,
    bm.map_zones
FROM bps_models bm
JOIN models mod ON bm.bps_model_id = mod.bps_model_id
JOIN modelers m ON mod.modeler_id = m.modeler_id
WHERE m.modelers LIKE ? OR m.modeler_email LIKE ?
ORDER BY bm.bps_model_id
"""

# Fire Frequency Queries
GET_FIRE_FREQUENCY_BY_MODEL = """
SELECT 
    severity,
    return_interval(years) as return_interval_years,
    percent_of_all_fires as percent_of_fires
FROM fire_frequency
WHERE bps_model_id = ?
ORDER BY percent_of_all_fires DESC
"""

GET_AVERAGE_FIRE_INTERVALS = """
SELECT 
    severity,
    AVG(return_interval(years)) as avg_interval,
    MIN(return_interval(years)) as min_interval,
    MAX(return_interval(years)) as max_interval,
    COUNT(*) as model_count
FROM fire_frequency
GROUP BY severity
ORDER BY avg_interval
"""

# Species Indicator Queries
GET_SPECIES_BY_MODEL = """
SELECT 
    symbol,
    scientific_name,
    common_name
FROM bps_indicators
WHERE bps_model_id = ?
ORDER BY scientific_name
"""

GET_MODELS_BY_SPECIES = """
SELECT DISTINCT
    bi.bps_model_id,
    bm.vegetation_type,
    bi.symbol,
    bi.scientific_name,
    bi.common_name
FROM bps_indicators bi
JOIN bps_models bm ON bi.bps_model_id = bm.bps_model_id
WHERE bi.scientific_name LIKE ? OR bi.common_name LIKE ?
ORDER BY bi.scientific_name, bi.bps_model_id
"""

# Reference Condition Queries
GET_REF_CONDITION_LONG = """
SELECT 
    ref_label,
    ref_percent,
    bps_name
FROM ref_con_long
WHERE bps_model_id = ?
ORDER BY ref_label
"""

GET_REF_CONDITION_MODIFIED = """
SELECT *
FROM ref_con_modified
WHERE Model_Code = ?
"""

# Transition Queries
GET_DETERMINISTIC_TRANSITIONS = """
SELECT 
    state_class_source,
    state_class_to,
    agemin,
    agemax
FROM deterministic
WHERE bps_model_id = ?
ORDER BY state_class_source, agemin
"""

GET_PROBABILISTIC_TRANSITIONS = """
SELECT 
    state_class_source,
    state_class_to,
    transition_type_id,
    probability,
    return_interval(years) as return_interval_years,
    age_reset,
    tst_min
FROM probabilistic
WHERE bps_model_id = ?
ORDER BY state_class_source, probability DESC
"""

# Succession Class Queries
GET_SUCCESSION_CLASSES = """
SELECT 
    ref_label,
    state_class_id,
    description
FROM scls_descriptions
WHERE bps_model_id = ?
ORDER BY ref_label
"""

# Summary Statistics Queries
GET_MODEL_SUMMARY = """
SELECT 
    bm.bps_model_id,
    bm.vegetation_type,
    bm.map_zones,
    COUNT(DISTINCT mod.modeler_id) as num_modelers,
    COUNT(DISTINCT bi.symbol) as num_species,
    COUNT(DISTINCT ff.severity) as num_fire_severities
FROM bps_models bm
LEFT JOIN models mod ON bm.bps_model_id = mod.bps_model_id
LEFT JOIN bps_indicators bi ON bm.bps_model_id = bi.bps_model_id
LEFT JOIN fire_frequency ff ON bm.bps_model_id = ff.bps_model_id
GROUP BY bm.bps_model_id, bm.vegetation_type, bm.map_zones
ORDER BY bm.bps_model_id
"""

GET_VEGETATION_TYPE_STATS = """
SELECT 
    vegetation_type,
    COUNT(*) as model_count,
    COUNT(DISTINCT map_zones) as unique_map_zones
FROM bps_models
WHERE vegetation_type IS NOT NULL
GROUP BY vegetation_type
ORDER BY model_count DESC
"""

# Complex Join Queries
GET_COMPLETE_MODEL_INFO = """
SELECT 
    bm.bps_model_id,
    bm.vegetation_type,
    bm.map_zones,
    bm.geographic_range,
    GROUP_CONCAT(DISTINCT m.modelers) as modelers,
    COUNT(DISTINCT bi.symbol) as species_count,
    AVG(ff.return_interval(years)) as avg_fire_interval
FROM bps_models bm
LEFT JOIN models mod ON bm.bps_model_id = mod.bps_model_id
LEFT JOIN modelers m ON mod.modeler_id = m.modeler_id
LEFT JOIN bps_indicators bi ON bm.bps_model_id = bi.bps_model_id
LEFT JOIN fire_frequency ff ON bm.bps_model_id = ff.bps_model_id
WHERE bm.bps_model_id = ?
GROUP BY bm.bps_model_id, bm.vegetation_type, bm.map_zones, bm.geographic_range
"""
