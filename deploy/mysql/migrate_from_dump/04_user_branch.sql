-- User ↔ branch assignments
-- Source: Dump20260912.sql  →  database skac_new

USE skac_new;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

INSERT INTO user_branch (user_id, branch_id) VALUES
  (1, 1),
  (1, 2),
  (2, 1),
  (2, 2),
  (3, 1),
  (3, 2),
  (4, 2),
  (5, 1);

SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;
