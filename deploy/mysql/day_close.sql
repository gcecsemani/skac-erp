-- Incremental: end-of-day cashier checkout (cash box vs UPI/bank).
-- Safe to run on an existing SKAC MySQL database.
-- New installs also get this table from deploy/mysql/schema.sql.
--
--   mysql -u USER -p DATABASE < deploy/mysql/day_close.sql

USE skac;

CREATE TABLE IF NOT EXISTS day_close (
	organization_id BIGINT NOT NULL,
	branch_id BIGINT NOT NULL,
	closed_by_user_id BIGINT,
	close_date DATE NOT NULL,
	closed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	opening_cash NUMERIC(14, 2) NOT NULL DEFAULT 0,
	cash_in NUMERIC(14, 2) NOT NULL DEFAULT 0,
	cash_out NUMERIC(14, 2) NOT NULL DEFAULT 0,
	expected_cash NUMERIC(14, 2) NOT NULL DEFAULT 0,
	counted_cash NUMERIC(14, 2) NOT NULL DEFAULT 0,
	cash_variance NUMERIC(14, 2) NOT NULL DEFAULT 0,
	digital_in NUMERIC(14, 2) NOT NULL DEFAULT 0,
	digital_out NUMERIC(14, 2) NOT NULL DEFAULT 0,
	expected_digital NUMERIC(14, 2) NOT NULL DEFAULT 0,
	counted_digital NUMERIC(14, 2) NOT NULL DEFAULT 0,
	digital_variance NUMERIC(14, 2) NOT NULL DEFAULT 0,
	sales_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
	collected_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
	khata_new NUMERIC(14, 2) NOT NULL DEFAULT 0,
	expense_total NUMERIC(14, 2) NOT NULL DEFAULT 0,
	bill_count INT NOT NULL DEFAULT 0,
	note VARCHAR(255),
	breakdown TEXT,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	UNIQUE KEY uq_day_close_branch_date (branch_id, close_date),
	FOREIGN KEY(organization_id) REFERENCES organization (id),
	FOREIGN KEY(branch_id) REFERENCES branch (id),
	FOREIGN KEY(closed_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX IF NOT EXISTS ix_day_close_organization_id ON day_close (organization_id);
CREATE INDEX IF NOT EXISTS ix_day_close_branch_id ON day_close (branch_id);
CREATE INDEX IF NOT EXISTS ix_day_close_close_date ON day_close (close_date);
CREATE INDEX IF NOT EXISTS ix_day_close_closed_by_user_id ON day_close (closed_by_user_id);

UPDATE `role`
SET description = 'POS, invoices, returns, farmers, expenses, day close and field visits for assigned branch'
WHERE `key` = 'cashier';
