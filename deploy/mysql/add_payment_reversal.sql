-- Production migration: reverse farmer payments, vendor payments, and stock corrections.
-- Adds reversal columns + allocation table used to un-apply khata receipts from invoices.
--
-- Idempotent. Safe to re-run. Does not change existing payment / GRN / stock amounts.
-- Run this on the prod database BEFORE (or with) deploying the new API/UI.
--
-- Prod Docker (from the deploy/ folder on the droplet):
--   docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
--     mysql -u skac -p"$MYSQL_PASSWORD" skac < add_payment_reversal.sql
--
-- Direct MySQL:
--   mysql -u USER -p skac < deploy/mysql/add_payment_reversal.sql

USE skac;
SET NAMES utf8mb4;

DROP PROCEDURE IF EXISTS skac_add_column_if_missing;

DELIMITER $$
CREATE PROCEDURE skac_add_column_if_missing(
  IN p_table VARCHAR(64),
  IN p_ddl TEXT
)
BEGIN
  DECLARE col_name VARCHAR(64);
  SET col_name = SUBSTRING_INDEX(p_ddl, ' ', 1);
  IF NOT EXISTS (
    SELECT 1
    FROM information_schema.COLUMNS
    WHERE TABLE_SCHEMA = DATABASE()
      AND TABLE_NAME = p_table
      AND COLUMN_NAME = col_name
  ) THEN
    SET @sql = CONCAT('ALTER TABLE `', p_table, '` ADD COLUMN ', p_ddl);
    PREPARE stmt FROM @sql;
    EXECUTE stmt;
    DEALLOCATE PREPARE stmt;
  END IF;
END$$
DELIMITER ;

CALL skac_add_column_if_missing('customer_payment', 'reversed_at DATETIME NULL');
CALL skac_add_column_if_missing('customer_payment', 'reversed_by_user_id BIGINT NULL');
CALL skac_add_column_if_missing('customer_payment', 'reversal_reason VARCHAR(255) NULL');

CALL skac_add_column_if_missing('vendor_payment', 'reversed_at DATETIME NULL');
CALL skac_add_column_if_missing('vendor_payment', 'reversed_by_user_id BIGINT NULL');
CALL skac_add_column_if_missing('vendor_payment', 'reversal_reason VARCHAR(255) NULL');

DROP PROCEDURE IF EXISTS skac_add_column_if_missing;

CREATE TABLE IF NOT EXISTS customer_payment_allocation (
	payment_id BIGINT NOT NULL,
	invoice_id BIGINT NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	KEY ix_customer_payment_allocation_payment_id (payment_id),
	KEY ix_customer_payment_allocation_invoice_id (invoice_id),
	FOREIGN KEY(payment_id) REFERENCES customer_payment (id),
	FOREIGN KEY(invoice_id) REFERENCES invoice (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verify (expect 6 reversal columns + the new table).
SELECT table_name, column_name, column_type, is_nullable
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND (
    (table_name IN ('customer_payment', 'vendor_payment')
     AND column_name IN ('reversed_at', 'reversed_by_user_id', 'reversal_reason'))
    OR table_name = 'customer_payment_allocation'
  )
ORDER BY table_name, ordinal_position;
