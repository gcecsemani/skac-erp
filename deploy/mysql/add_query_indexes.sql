-- Production migration: query indexes used by POS farmer history, khata
-- allocation, stock trail, and field-visit lists.
--
-- No new columns or data rewrites. Idempotent. Safe to re-run.
-- The API also creates these on startup if they are missing; run this on prod
-- MySQL so large tables are indexed before traffic hits the new endpoints.
--
-- Prod Docker (from the deploy/ folder on the droplet):
--   docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
--     mysql -u skac -p"$MYSQL_PASSWORD" skac < add_query_indexes.sql
--
-- Direct MySQL:
--   mysql -u USER -p skac < deploy/mysql/add_query_indexes.sql

USE skac;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS skac_add_index_if_missing;

DELIMITER $$
CREATE PROCEDURE skac_add_index_if_missing(
  IN p_table VARCHAR(64),
  IN p_name VARCHAR(64),
  IN p_cols VARCHAR(255)
)
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.statistics
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = p_table
      AND INDEX_NAME = p_name
  ) THEN
    SET @sql = CONCAT('CREATE INDEX `', p_name, '` ON `', p_table, '` (', p_cols, ')');
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END$$
DELIMITER ;

CALL skac_add_index_if_missing(
  'stock_movement',
  'ix_stock_movement_org_branch_prod_at',
  'organization_id, branch_id, product_id, occurred_at'
);
CALL skac_add_index_if_missing(
  'invoice',
  'ix_invoice_customer_status_date',
  'customer_id, status, invoice_date'
);
CALL skac_add_index_if_missing(
  'customer',
  'ix_customer_org_outstanding',
  'organization_id, outstanding_balance'
);
CALL skac_add_index_if_missing(
  'field_visit',
  'ix_field_visit_org_date',
  'organization_id, visit_date'
);

DROP PROCEDURE IF EXISTS skac_add_index_if_missing;

-- Verify (expect 4 rows).
SELECT table_name, index_name
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND index_name IN (
    'ix_stock_movement_org_branch_prod_at',
    'ix_invoice_customer_status_date',
    'ix_customer_org_outstanding',
    'ix_field_visit_org_date'
  )
GROUP BY table_name, index_name
ORDER BY table_name, index_name;
