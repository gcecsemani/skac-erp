-- Incremental: purchase returns (debit notes) and field visits.
-- Safe to run on an existing SKAC MySQL database.
-- New installs also get these tables from deploy/mysql/schema.sql.
--
--   mysql -u root -p skac < deploy/mysql/purchase_return_field_visit.sql

USE skac;

-- Ensure purchase-return stock movements are allowed (already in fresh schema.sql).
ALTER TABLE stock_movement
  MODIFY COLUMN movement_type ENUM(
    'grn','sale','sale_return','purchase_return','transfer_out','transfer_in','adjustment'
  ) NOT NULL;

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

CREATE TABLE IF NOT EXISTS purchase_return_item (
	purchase_return_id BIGINT NOT NULL,
	grn_item_id BIGINT NOT NULL,
	product_id BIGINT NOT NULL,
	batch_id BIGINT,
	product_name VARCHAR(200) NOT NULL,
	batch_no VARCHAR(80),
	quantity NUMERIC(14, 3) NOT NULL,
	unit_price NUMERIC(12, 2) NOT NULL,
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
