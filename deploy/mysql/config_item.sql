-- Incremental: org picklists (districts, villages, units, GST, HSN, expenses, payments).
-- Safe to run on an existing SKAC MySQL database. New installs also get this table
-- from deploy/mysql/schema.sql.

USE skac;

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
