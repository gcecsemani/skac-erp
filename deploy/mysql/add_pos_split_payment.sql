-- Production migration: split POS payments and sales-return settlement.
--
-- 1. invoice.payment_mode gains 'mixed' for a bill paid with more than one mode.
-- 2. invoice_tender stores each amount received now (cash / upi / card).
--    The unpaid remainder stays on the farmer's khata.
-- 3. credit_note records how much of a return reduced khata vs how much
--    was refunded from the till. Existing notes are left at 0/0 so the
--    app still treats them as the old full-khata reduction.
--
-- Idempotent. Safe to re-run. Does not change invoice or outstanding amounts.
-- Run this on the prod database BEFORE deploying the new API/UI.
--
-- Prod Docker (from the deploy/ folder on the droplet):
--   docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
--     mysql -u skac -p"$MYSQL_PASSWORD" skac < add_pos_split_payment.sql
--
-- Direct MySQL:
--   mysql -u USER -p skac < deploy/mysql/add_pos_split_payment.sql

USE skac;
SET NAMES utf8mb4;

-- 'mixed' must exist before the API writes a split bill.
ALTER TABLE invoice
  MODIFY COLUMN payment_mode ENUM('cash','credit','upi','card','mixed') NOT NULL;

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

CALL skac_add_column_if_missing('credit_note', 'khata_amount NUMERIC(14, 2) NOT NULL DEFAULT 0');
CALL skac_add_column_if_missing('credit_note', 'refund_amount NUMERIC(14, 2) NOT NULL DEFAULT 0');
CALL skac_add_column_if_missing('credit_note', 'refund_mode VARCHAR(20) NULL');

DROP PROCEDURE IF EXISTS skac_add_column_if_missing;

CREATE TABLE IF NOT EXISTS invoice_tender (
	invoice_id BIGINT NOT NULL,
	mode VARCHAR(20) NOT NULL,
	amount NUMERIC(14, 2) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	KEY ix_invoice_tender_invoice_id (invoice_id),
	FOREIGN KEY(invoice_id) REFERENCES invoice (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Verify: mixed is in the enum, three credit_note columns, and invoice_tender exists.
SELECT column_type
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'invoice'
  AND column_name = 'payment_mode';

SELECT table_name, column_name, column_type, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND (
    (table_name = 'credit_note' AND column_name IN ('khata_amount', 'refund_amount', 'refund_mode'))
    OR table_name = 'invoice_tender'
  )
ORDER BY table_name, ordinal_position;
