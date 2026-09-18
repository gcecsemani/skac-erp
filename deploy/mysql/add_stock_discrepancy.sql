-- Production migration: physical count vs book qty cases for stock reconciliation.
-- Idempotent. Safe to re-run. Does not change existing stock quantities.
-- Run this on the prod database BEFORE (or with) deploying the new API/UI.
--
-- Prod Docker (from the deploy/ folder on the droplet):
--   docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
--     mysql -u skac -p"$MYSQL_PASSWORD" skac < add_stock_discrepancy.sql
--
-- Direct MySQL:
--   mysql -u USER -p skac < deploy/mysql/add_stock_discrepancy.sql

USE skac;
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS stock_discrepancy (
  organization_id BIGINT NOT NULL,
  branch_id BIGINT NOT NULL,
  product_id BIGINT NOT NULL,
  count_date DATE NOT NULL,
  book_qty NUMERIC(14, 3) NOT NULL,
  counted_qty NUMERIC(14, 3) NOT NULL,
  variance NUMERIC(14, 3) NOT NULL,
  status ENUM('open','investigating','resolved') NOT NULL DEFAULT 'open',
  note VARCHAR(255) NOT NULL,
  resolution VARCHAR(255),
  created_by_user_id BIGINT,
  resolved_by_user_id BIGINT,
  resolved_at DATETIME,
  id BIGINT NOT NULL AUTO_INCREMENT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY ix_stock_discrepancy_organization_id (organization_id),
  KEY ix_stock_discrepancy_branch_id (branch_id),
  KEY ix_stock_discrepancy_product_id (product_id),
  KEY ix_stock_discrepancy_count_date (count_date),
  KEY ix_stock_discrepancy_status (status),
  KEY ix_stock_discrepancy_org_status (organization_id, status),
  KEY ix_stock_discrepancy_org_product (organization_id, product_id, branch_id),
  CONSTRAINT fk_stock_discrepancy_org FOREIGN KEY (organization_id) REFERENCES organization (id),
  CONSTRAINT fk_stock_discrepancy_branch FOREIGN KEY (branch_id) REFERENCES branch (id),
  CONSTRAINT fk_stock_discrepancy_product FOREIGN KEY (product_id) REFERENCES product (id),
  CONSTRAINT fk_stock_discrepancy_created_by FOREIGN KEY (created_by_user_id) REFERENCES `user` (id),
  CONSTRAINT fk_stock_discrepancy_resolved_by FOREIGN KEY (resolved_by_user_id) REFERENCES `user` (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
