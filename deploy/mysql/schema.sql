-- SKAC MySQL schema
-- Run:
--   mysql -u root -p < deploy/mysql/schema.sql
-- Then point backend/.env DATABASE_URL at this database, start the API,
-- and optionally load demo data with:  python -m app.seed

CREATE DATABASE IF NOT EXISTS skac
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE skac;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS organization (
	name VARCHAR(200) NOT NULL, 
	legal_name VARCHAR(200), 
	pan VARCHAR(20), 
	contact_email VARCHAR(200), 
	contact_phone VARCHAR(20), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	is_deleted TINYINT(1) NOT NULL DEFAULT 0, 
	deleted_at DATETIME, 
	PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `role` (
	`key` VARCHAR(40) NOT NULL, 
	name VARCHAR(80) NOT NULL, 
	description VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	UNIQUE (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS branch (
	organization_id BIGINT NOT NULL, 
	code VARCHAR(20) NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	address_line1 VARCHAR(200), 
	address_line2 VARCHAR(200), 
	city VARCHAR(100), 
	district VARCHAR(100), 
	state VARCHAR(100), 
	state_code VARCHAR(4), 
	pincode VARCHAR(10), 
	phone VARCHAR(20), 
	gstin VARCHAR(20), 
	fco_license_no VARCHAR(60), 
	fco_license_valid_to DATE, 
	pesticide_license_no VARCHAR(60), 
	pesticide_license_valid_to DATE, 
	seed_license_no VARCHAR(60), 
	seed_license_valid_to DATE, 
	printer_name VARCHAR(120), 
	printer_type VARCHAR(20) NOT NULL DEFAULT 'thermal', 
	thermal_paper_mm INTEGER NOT NULL DEFAULT 80, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	is_deleted TINYINT(1) NOT NULL DEFAULT 0, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customer (
	organization_id BIGINT NOT NULL, 
	name VARCHAR(150) NOT NULL, 
	phone VARCHAR(20), 
	aadhaar_no VARCHAR(12), 
	village VARCHAR(120), 
	district VARCHAR(120), 
	land_holding_acres NUMERIC(10, 2), 
	gstin VARCHAR(20), 
	credit_allowed TINYINT(1) NOT NULL DEFAULT 0, 
	credit_limit NUMERIC(14, 2) NOT NULL, 
	outstanding_balance NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	is_deleted TINYINT(1) NOT NULL DEFAULT 0, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_customer_org_phone UNIQUE (organization_id, phone), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS ledger_account (
	organization_id BIGINT NOT NULL, 
	code VARCHAR(30) NOT NULL, 
	name VARCHAR(120) NOT NULL, 
	type ENUM('asset','liability','income','expense','equity') NOT NULL, 
	is_system TINYINT(1) NOT NULL DEFAULT 0, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_account_org_code UNIQUE (organization_id, code), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product (
	organization_id BIGINT NOT NULL, 
	sku VARCHAR(40) NOT NULL, 
	barcode VARCHAR(64), 
	name VARCHAR(200) NOT NULL, 
	category ENUM('fertilizer','pesticide','seed') NOT NULL, 
	brand VARCHAR(120), 
	manufacturer VARCHAR(160), 
	hsn_code VARCHAR(12), 
	gst_rate NUMERIC(5, 2) NOT NULL, 
	base_unit VARCHAR(20) NOT NULL, 
	mrp NUMERIC(12, 2) NOT NULL, 
	purchase_price NUMERIC(12, 2) NOT NULL, 
	sale_price NUMERIC(12, 2) NOT NULL, 
	reorder_level NUMERIC(12, 3) NOT NULL, 
	is_active TINYINT(1) NOT NULL DEFAULT 0, 
	is_favorite TINYINT(1) NOT NULL DEFAULT 0, 
	npk_n NUMERIC(5, 2), 
	npk_p NUMERIC(5, 2), 
	npk_k NUMERIC(5, 2), 
	toxicity_class VARCHAR(40), 
	germination_pct NUMERIC(5, 2), 
	seed_lot VARCHAR(60), 
	attributes JSON, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	is_deleted TINYINT(1) NOT NULL DEFAULT 0, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_product_org_sku UNIQUE (organization_id, sku), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `user` (
	organization_id BIGINT NOT NULL, 
	role_id BIGINT NOT NULL, 
	full_name VARCHAR(150) NOT NULL, 
	email VARCHAR(200) NOT NULL, 
	phone VARCHAR(20), 
	hashed_password VARCHAR(255) NOT NULL, 
	is_active TINYINT(1) NOT NULL DEFAULT 0, 
	totp_secret VARCHAR(64), 
	totp_enabled TINYINT(1) NOT NULL DEFAULT 0, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	is_deleted TINYINT(1) NOT NULL DEFAULT 0, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_user_org_email UNIQUE (organization_id, email), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(role_id) REFERENCES `role` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vendor (
	organization_id BIGINT NOT NULL, 
	name VARCHAR(200) NOT NULL, 
	gstin VARCHAR(20), 
	phone VARCHAR(20), 
	email VARCHAR(200), 
	address VARCHAR(400), 
	outstanding_balance NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	is_deleted TINYINT(1) NOT NULL DEFAULT 0, 
	deleted_at DATETIME, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS audit_log (
	organization_id INTEGER, 
	branch_id INTEGER, 
	actor_user_id BIGINT, 
	action VARCHAR(20) NOT NULL, 
	entity_type VARCHAR(60) NOT NULL, 
	entity_id VARCHAR(40), 
	changes JSON, 
	ip_address VARCHAR(64), 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(actor_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS batch (
	organization_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_no VARCHAR(80) NOT NULL, 
	mfg_date DATE, 
	expiry_date DATE, 
	purchase_price NUMERIC(12, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_batch_product_no UNIQUE (product_id, batch_no), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(product_id) REFERENCES product (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS customer_payment (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT, 
	customer_id BIGINT NOT NULL, 
	paid_at DATETIME NOT NULL, 
	amount NUMERIC(14, 2) NOT NULL, 
	mode VARCHAR(20) NOT NULL, 
	note VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS expense (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	created_by_user_id BIGINT, 
	expense_date DATE NOT NULL, 
	category VARCHAR(40) NOT NULL, 
	payee VARCHAR(150), 
	amount NUMERIC(14, 2) NOT NULL, 
	mode VARCHAR(20) NOT NULL, 
	note VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS invoice (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	customer_id BIGINT, 
	created_by_user_id BIGINT, 
	client_uuid VARCHAR(36), 
	invoice_no VARCHAR(40), 
	invoice_date DATE NOT NULL, 
	status ENUM('draft','finalized','cancelled') NOT NULL, 
	tax_type ENUM('intra','inter') NOT NULL, 
	payment_mode ENUM('cash','credit','upi','card') NOT NULL, 
	subtotal NUMERIC(14, 2) NOT NULL, 
	discount_total NUMERIC(14, 2) NOT NULL, 
	tax_total NUMERIC(14, 2) NOT NULL, 
	grand_total NUMERIC(14, 2) NOT NULL, 
	amount_paid NUMERIC(14, 2) NOT NULL, 
	finalized_at DATETIME, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_invoice_client_uuid UNIQUE (client_uuid), 
	CONSTRAINT uq_invoice_branch_no UNIQUE (branch_id, invoice_no), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS journal_entry (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT, 
	entry_date DATE NOT NULL, 
	narration VARCHAR(255), 
	ref_type VARCHAR(40), 
	ref_id INTEGER, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS product_unit (
	product_id BIGINT NOT NULL, 
	unit VARCHAR(20) NOT NULL, 
	factor_to_base NUMERIC(12, 4) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_product_unit UNIQUE (product_id, unit), 
	FOREIGN KEY(product_id) REFERENCES product (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS purchase_order (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	vendor_id BIGINT NOT NULL, 
	created_by_user_id BIGINT, 
	po_no VARCHAR(40), 
	order_date DATE NOT NULL, 
	status ENUM('draft','placed','partially_received','received','cancelled') NOT NULL, 
	expected_total NUMERIC(14, 2) NOT NULL, 
	notes VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(vendor_id) REFERENCES vendor (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock_transfer (
	organization_id BIGINT NOT NULL, 
	from_branch_id BIGINT NOT NULL, 
	to_branch_id BIGINT NOT NULL, 
	requested_by_user_id BIGINT, 
	approved_by_user_id BIGINT, 
	transfer_no VARCHAR(40), 
	transfer_date DATE NOT NULL, 
	status ENUM('requested','approved','dispatched','received','rejected') NOT NULL, 
	notes VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(from_branch_id) REFERENCES branch (id), 
	FOREIGN KEY(to_branch_id) REFERENCES branch (id), 
	FOREIGN KEY(requested_by_user_id) REFERENCES `user` (id), 
	FOREIGN KEY(approved_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS user_branch (
	user_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	PRIMARY KEY (user_id, branch_id), 
	FOREIGN KEY(user_id) REFERENCES `user` (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS vendor_payment (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT, 
	vendor_id BIGINT NOT NULL, 
	paid_at DATETIME NOT NULL, 
	amount NUMERIC(14, 2) NOT NULL, 
	mode VARCHAR(20) NOT NULL, 
	note VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(vendor_id) REFERENCES vendor (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS credit_note (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	invoice_id BIGINT NOT NULL, 
	customer_id BIGINT, 
	created_by_user_id BIGINT, 
	note_no VARCHAR(40), 
	note_date DATE NOT NULL, 
	reason VARCHAR(255), 
	total NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoice (id), 
	FOREIGN KEY(customer_id) REFERENCES customer (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grn (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	vendor_id BIGINT NOT NULL, 
	purchase_order_id BIGINT, 
	created_by_user_id BIGINT, 
	grn_no VARCHAR(40), 
	received_date DATE NOT NULL, 
	vendor_invoice_no VARCHAR(60), 
	total_value NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(vendor_id) REFERENCES vendor (id), 
	FOREIGN KEY(purchase_order_id) REFERENCES purchase_order (id), 
	FOREIGN KEY(created_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS purchase_return (
	organization_id BIGINT NOT NULL,
	branch_id BIGINT NOT NULL,
	vendor_id BIGINT NOT NULL,
	grn_id BIGINT NOT NULL,
	created_by_user_id BIGINT,
	note_no VARCHAR(40),
	note_date DATE NOT NULL,
	reason VARCHAR(255),
	total NUMERIC(14, 2) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES organization (id),
	FOREIGN KEY(branch_id) REFERENCES branch (id),
	FOREIGN KEY(vendor_id) REFERENCES vendor (id),
	FOREIGN KEY(grn_id) REFERENCES grn (id),
	FOREIGN KEY(created_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS invoice_item (
	invoice_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_id BIGINT, 
	product_name VARCHAR(200) NOT NULL, 
	hsn_code VARCHAR(12), 
	batch_no VARCHAR(80), 
	mfg_date DATE, 
	expiry_date DATE, 
	unit VARCHAR(20) NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	discount NUMERIC(12, 2) NOT NULL, 
	gst_rate NUMERIC(5, 2) NOT NULL, 
	taxable_value NUMERIC(14, 2) NOT NULL, 
	tax_amount NUMERIC(14, 2) NOT NULL, 
	line_total NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(invoice_id) REFERENCES invoice (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS journal_line (
	entry_id BIGINT NOT NULL, 
	account_id BIGINT NOT NULL, 
	debit NUMERIC(14, 2) NOT NULL, 
	credit NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(entry_id) REFERENCES journal_entry (id), 
	FOREIGN KEY(account_id) REFERENCES ledger_account (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS purchase_order_item (
	order_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	product_name VARCHAR(200) NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	received_quantity NUMERIC(14, 3) NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(order_id) REFERENCES purchase_order (id), 
	FOREIGN KEY(product_id) REFERENCES product (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_id BIGINT NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	CONSTRAINT uq_stock_branch_batch UNIQUE (branch_id, batch_id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock_movement (
	organization_id BIGINT NOT NULL, 
	branch_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_id BIGINT NOT NULL, 
	movement_type ENUM('grn','sale','sale_return','purchase_return','transfer_out','transfer_in','adjustment') NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	ref_type VARCHAR(40), 
	ref_id INTEGER, 
	occurred_at DATETIME NOT NULL, 
	note VARCHAR(255), 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(organization_id) REFERENCES organization (id), 
	FOREIGN KEY(branch_id) REFERENCES branch (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS stock_transfer_item (
	transfer_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_id BIGINT, 
	product_name VARCHAR(200) NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(transfer_id) REFERENCES stock_transfer (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS credit_note_item (
	credit_note_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_id BIGINT, 
	product_name VARCHAR(200) NOT NULL, 
	quantity NUMERIC(14, 3) NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	tax_amount NUMERIC(14, 2) NOT NULL, 
	line_total NUMERIC(14, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(credit_note_id) REFERENCES credit_note (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS grn_item (
	grn_id BIGINT NOT NULL, 
	product_id BIGINT NOT NULL, 
	batch_id BIGINT, 
	batch_no VARCHAR(80) NOT NULL, 
	mfg_date DATE, 
	expiry_date DATE, 
	quantity NUMERIC(14, 3) NOT NULL, 
	unit_price NUMERIC(12, 2) NOT NULL, 
	id BIGINT NOT NULL AUTO_INCREMENT, 
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP, 
	PRIMARY KEY (id), 
	FOREIGN KEY(grn_id) REFERENCES grn (id), 
	FOREIGN KEY(product_id) REFERENCES product (id), 
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS purchase_return_item (
	purchase_return_id BIGINT NOT NULL,
	grn_item_id BIGINT NOT NULL,
	product_id BIGINT NOT NULL,
	batch_id BIGINT,
	product_name VARCHAR(200) NOT NULL,
	batch_no VARCHAR(80),
	hsn_code VARCHAR(12),
	packing VARCHAR(20),
	quantity NUMERIC(14, 3) NOT NULL,
	unit_price NUMERIC(12, 2) NOT NULL,
	gst_rate NUMERIC(5, 2) NOT NULL DEFAULT 0,
	taxable_value NUMERIC(14, 2) NOT NULL DEFAULT 0,
	tax_amount NUMERIC(14, 2) NOT NULL DEFAULT 0,
	line_total NUMERIC(14, 2) NOT NULL,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(purchase_return_id) REFERENCES purchase_return (id),
	FOREIGN KEY(grn_item_id) REFERENCES grn_item (id),
	FOREIGN KEY(product_id) REFERENCES product (id),
	FOREIGN KEY(batch_id) REFERENCES batch (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS field_visit (
	organization_id BIGINT NOT NULL,
	branch_id BIGINT NOT NULL,
	visited_by_user_id BIGINT NOT NULL,
	customer_id BIGINT,
	visit_no VARCHAR(40),
	visit_date DATE NOT NULL,
	farmer_name VARCHAR(150) NOT NULL,
	farmer_phone VARCHAR(20),
	village VARCHAR(120),
	latitude DOUBLE,
	longitude DOUBLE,
	gps_accuracy DOUBLE,
	gps_captured_at DATETIME,
	complaint_notes TEXT,
	prescription_notes TEXT,
	status ENUM('open','completed','cancelled') NOT NULL,
	resolution_note VARCHAR(255),
	resolved_by_user_id BIGINT,
	resolved_at DATETIME,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES organization (id),
	FOREIGN KEY(branch_id) REFERENCES branch (id),
	FOREIGN KEY(visited_by_user_id) REFERENCES `user` (id),
	FOREIGN KEY(customer_id) REFERENCES customer (id),
	FOREIGN KEY(resolved_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS field_visit_photo (
	visit_id BIGINT NOT NULL,
	stored_name VARCHAR(200) NOT NULL,
	original_name VARCHAR(200),
	content_type VARCHAR(80),
	size_bytes INTEGER NOT NULL DEFAULT 0,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	PRIMARY KEY (id),
	FOREIGN KEY(visit_id) REFERENCES field_visit (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Helpful indexes (IF NOT EXISTS is MySQL 8+)
CREATE INDEX IF NOT EXISTS ix_branch_organization_id ON branch (organization_id);
CREATE INDEX IF NOT EXISTS ix_customer_organization_id ON customer (organization_id);
CREATE INDEX IF NOT EXISTS ix_customer_phone ON customer (phone);
CREATE INDEX IF NOT EXISTS ix_customer_aadhaar_no ON customer (aadhaar_no);
CREATE INDEX IF NOT EXISTS ix_product_organization_id ON product (organization_id);
CREATE INDEX IF NOT EXISTS ix_product_sku ON product (sku);
CREATE INDEX IF NOT EXISTS ix_invoice_organization_id ON invoice (organization_id);
CREATE INDEX IF NOT EXISTS ix_invoice_branch_id ON invoice (branch_id);
CREATE INDEX IF NOT EXISTS ix_invoice_invoice_date ON invoice (invoice_date);
CREATE INDEX IF NOT EXISTS ix_expense_organization_id ON expense (organization_id);
CREATE INDEX IF NOT EXISTS ix_expense_branch_id ON expense (branch_id);
CREATE INDEX IF NOT EXISTS ix_expense_expense_date ON expense (expense_date);
CREATE INDEX IF NOT EXISTS ix_expense_category ON expense (category);
CREATE INDEX IF NOT EXISTS ix_stock_branch_id ON stock (branch_id);
CREATE INDEX IF NOT EXISTS ix_batch_expiry_date ON batch (expiry_date);
CREATE INDEX IF NOT EXISTS ix_purchase_return_organization_id ON purchase_return (organization_id);
CREATE INDEX IF NOT EXISTS ix_purchase_return_branch_id ON purchase_return (branch_id);
CREATE INDEX IF NOT EXISTS ix_purchase_return_vendor_id ON purchase_return (vendor_id);
CREATE INDEX IF NOT EXISTS ix_purchase_return_grn_id ON purchase_return (grn_id);
CREATE INDEX IF NOT EXISTS ix_purchase_return_item_purchase_return_id ON purchase_return_item (purchase_return_id);
CREATE INDEX IF NOT EXISTS ix_purchase_return_item_grn_item_id ON purchase_return_item (grn_item_id);
CREATE INDEX IF NOT EXISTS ix_field_visit_organization_id ON field_visit (organization_id);
CREATE INDEX IF NOT EXISTS ix_field_visit_branch_id ON field_visit (branch_id);
CREATE INDEX IF NOT EXISTS ix_field_visit_visited_by_user_id ON field_visit (visited_by_user_id);
CREATE INDEX IF NOT EXISTS ix_field_visit_customer_id ON field_visit (customer_id);
CREATE INDEX IF NOT EXISTS ix_field_visit_status ON field_visit (status);
CREATE INDEX IF NOT EXISTS ix_field_visit_photo_visit_id ON field_visit_photo (visit_id);

CREATE TABLE IF NOT EXISTS config_item (
	organization_id BIGINT NOT NULL,
	kind VARCHAR(40) NOT NULL,
	parent_id BIGINT,
	code VARCHAR(80) NOT NULL,
	name VARCHAR(160) NOT NULL,
	extra JSON,
	is_active TINYINT(1) NOT NULL DEFAULT 1,
	sort_order INTEGER NOT NULL DEFAULT 0,
	id BIGINT NOT NULL AUTO_INCREMENT,
	created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
	is_deleted TINYINT(1) NOT NULL DEFAULT 0,
	deleted_at DATETIME,
	PRIMARY KEY (id),
	FOREIGN KEY(organization_id) REFERENCES organization (id),
	FOREIGN KEY(parent_id) REFERENCES config_item (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE INDEX IF NOT EXISTS ix_config_item_organization_id ON config_item (organization_id);
CREATE INDEX IF NOT EXISTS ix_config_item_kind ON config_item (kind);
CREATE INDEX IF NOT EXISTS ix_config_item_parent_id ON config_item (parent_id);
CREATE INDEX IF NOT EXISTS ix_config_org_kind ON config_item (organization_id, kind);

SET FOREIGN_KEY_CHECKS = 1;

-- Keep only the two supported roles.
INSERT INTO `role` (`key`, name, description)
VALUES
  ('owner', 'Owner', 'Full access, all branches'),
  ('cashier', 'Cashier', 'POS, invoices, returns, farmers and expenses for assigned branch')
ON DUPLICATE KEY UPDATE
  name = VALUES(name),
  description = VALUES(description);

-- Remap leftover roles from older installs, then drop them.
UPDATE `user` u
JOIN `role` r ON r.id = u.role_id
JOIN `role` owner ON owner.`key` = 'owner'
SET u.role_id = owner.id
WHERE r.`key` IN ('admin');

UPDATE `user` u
JOIN `role` r ON r.id = u.role_id
JOIN `role` cashier ON cashier.`key` = 'cashier'
SET u.role_id = cashier.id
WHERE r.`key` NOT IN ('owner', 'cashier');

DELETE FROM `role` WHERE `key` NOT IN ('owner', 'cashier');

-- Demo users are created by: python -m app.seed
-- (owner@skac.in / owner123  and  cashier@skac.in / cashier123)
