-- Organization (single tenant)
-- Source: Dump20260912.sql  →  database skac_new

USE skac_new;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

INSERT INTO organization (id, name, legal_name, is_deleted) VALUES
  (1, 'Sri Kumaran Agri Clinic', 'SKAC', 0);

ALTER TABLE `organization` AUTO_INCREMENT = 2;

SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;
