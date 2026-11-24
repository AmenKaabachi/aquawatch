-- ============================================================
-- AquaWatch Grand Tunis — Données initiales (seed)
-- Sprint 1
-- ============================================================
-- INSERT OR IGNORE garantit l'idempotence : exécuter ce script
-- plusieurs fois ne duplique jamais les enregistrements.

-- ── Gouvernorats du Grand Tunis ─────────────────────────────
-- Population approximative — Source : INS Tunisie, recensement 2024.
-- Ces chiffres sont des valeurs de référence ; consulter
-- https://www.ins.tn/enquetes/population-and-housing-census-2024
-- pour les données officielles actualisées.

INSERT OR IGNORE INTO governorates (id, name, population)
VALUES (1, 'Tunis',     1056247);
INSERT OR IGNORE INTO governorates (id, name, population)
VALUES (2, 'Ariana',     621762);
INSERT OR IGNORE INTO governorates (id, name, population)
VALUES (3, 'Ben Arous',  707284);
INSERT OR IGNORE INTO governorates (id, name, population)
VALUES (4, 'Manouba',    420418);

-- ── Zones de surveillance hypothétiques (2 par gouvernorat) ─
-- Ces zones sont des emplacements de DÉMONSTRATION.
-- Elles ne correspondent pas à des installations vérifiées
-- du réseau SONEDE.

INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (1, 'TUN-Z1', 1, 'Tunis Centre',
        'Zone hypothétique — Centre-ville de Tunis', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (2, 'TUN-Z2', 1, 'Tunis Sud',
        'Zone hypothétique — Sud de Tunis', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (3, 'ARI-Z1', 2, 'Ariana Ville',
        'Zone hypothétique — Centre d''Ariana', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (4, 'ARI-Z2', 2, 'La Soukra',
        'Zone hypothétique — La Soukra', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (5, 'BEN-Z1', 3, 'Ben Arous Centre',
        'Zone hypothétique — Centre de Ben Arous', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (6, 'BEN-Z2', 3, 'Hammam Lif',
        'Zone hypothétique — Hammam Lif', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (7, 'MAN-Z1', 4, 'Manouba Ville',
        'Zone hypothétique — Centre de Manouba', 1);
INSERT OR IGNORE INTO monitoring_zones (id, code, governorate_id, name, description, is_active)
VALUES (8, 'MAN-Z2', 4, 'Douar Hicher',
        'Zone hypothétique — Douar Hicher', 1);

-- ── Capteurs virtuels (3 par zone = 24 capteurs) ───────────
-- Types : pressure (pression), flow (débit), combined (combiné)
-- Convention de nommage : CAP-{ZONE}-{TYPE}{NUMÉRO}
--   P = pressure, D = débit (flow), C = combiné

-- Gouvernorat de Tunis
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 1, 1, 'CAP-TUN1-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 2, 1, 'CAP-TUN1-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 3, 1, 'CAP-TUN1-C01', 'combined', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 4, 2, 'CAP-TUN2-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 5, 2, 'CAP-TUN2-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 6, 2, 'CAP-TUN2-C01', 'combined', 1);

-- Gouvernorat d'Ariana
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 7, 3, 'CAP-ARI1-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 8, 3, 'CAP-ARI1-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES ( 9, 3, 'CAP-ARI1-C01', 'combined', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (10, 4, 'CAP-ARI2-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (11, 4, 'CAP-ARI2-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (12, 4, 'CAP-ARI2-C01', 'combined', 1);

-- Gouvernorat de Ben Arous
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (13, 5, 'CAP-BEN1-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (14, 5, 'CAP-BEN1-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (15, 5, 'CAP-BEN1-C01', 'combined', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (16, 6, 'CAP-BEN2-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (17, 6, 'CAP-BEN2-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (18, 6, 'CAP-BEN2-C01', 'combined', 1);

-- Gouvernorat de Manouba
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (19, 7, 'CAP-MAN1-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (20, 7, 'CAP-MAN1-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (21, 7, 'CAP-MAN1-C01', 'combined', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (22, 8, 'CAP-MAN2-P01', 'pressure', 1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (23, 8, 'CAP-MAN2-D01', 'flow',     1);
INSERT OR IGNORE INTO sensors (id, zone_id, name, sensor_type, is_active)
VALUES (24, 8, 'CAP-MAN2-C01', 'combined', 1);
