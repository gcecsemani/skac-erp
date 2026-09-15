-- Branches
-- Source: Dump20260912.sql  →  database skac_new

USE skac_new;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

INSERT INTO branch (
  id, organization_id, code, name, city, district, state, state_code,
  printer_name, printer_type, thermal_paper_mm, is_deleted
) VALUES
  (1, 1, 'AVL', 'AVALURPET', 'Avalurpet', 'Tiruvannamalai', 'Tamil Nadu', '33', 'Samsung ML-2160 Series', 'laser', 80, 0),
  (2, 1, 'TVM', 'TIRUVANNAMALAI', 'Tiruvannamalai', 'Tiruvannamalai', 'Tamil Nadu', '33', 'TVM PRINTER', 'thermal', 80, 0);

ALTER TABLE `branch` AUTO_INCREMENT = 3;

SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;
