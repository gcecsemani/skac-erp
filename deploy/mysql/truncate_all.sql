-- Wipe all SKAC data (keeps table structure).
-- Child tables first, then parents, so FK order is safe even if you switch
-- these statements to DELETE. MySQL TRUNCATE still needs FOREIGN_KEY_CHECKS=0
-- because InnoDB refuses TRUNCATE on any table that is referenced by an FK.
--
--   mysql -u root -p skac < deploy/mysql/truncate_all.sql
--
-- After this, AUTO_INCREMENT is reset on every table. Re-seed with:
--   python -m app.seed

USE skac_new;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Line / photo / join tables (deepest children)
TRUNCATE TABLE field_visit_photo;
TRUNCATE TABLE purchase_return_item;
TRUNCATE TABLE credit_note_item;
TRUNCATE TABLE invoice_item;
TRUNCATE TABLE stock_transfer_item;
TRUNCATE TABLE purchase_order_item;
TRUNCATE TABLE journal_line;
TRUNCATE TABLE product_unit;
TRUNCATE TABLE user_branch;
TRUNCATE TABLE stock_movement;
TRUNCATE TABLE stock;

-- 2. Documents that reference GRN / invoice lines
TRUNCATE TABLE purchase_return;
TRUNCATE TABLE grn_item;
TRUNCATE TABLE credit_note;
TRUNCATE TABLE field_visit;

-- 3. Headers and other transaction tables
TRUNCATE TABLE invoice;
TRUNCATE TABLE grn;
TRUNCATE TABLE purchase_order;
TRUNCATE TABLE vendor_payment;
TRUNCATE TABLE customer_payment_allocation;
TRUNCATE TABLE customer_payment;
TRUNCATE TABLE expense;
TRUNCATE TABLE journal_entry;
TRUNCATE TABLE stock_transfer;
TRUNCATE TABLE audit_log;

-- 4. Inventory batches (referenced by stock / items above)
TRUNCATE TABLE batch;

-- 5. Org masters (config_item is self-referencing via parent_id)
TRUNCATE TABLE config_item;
TRUNCATE TABLE customer;
TRUNCATE TABLE vendor;
TRUNCATE TABLE product;
TRUNCATE TABLE ledger_account;

-- 6. Users, branches, tenant
-- TRUNCATE TABLE `user`;
-- TRUNCATE TABLE branch;
-- TRUNCATE TABLE organization;

-- 7. Roles last
-- TRUNCATE TABLE `role`;

SET FOREIGN_KEY_CHECKS = 1;

-- App expects these two roles. Org, branches, and users come from seed.
-- INSERT INTO `role` (`key`, name, description)
-- VALUES
--  ('owner', 'Owner', 'Full access, all branches'),
--  ('cashier', 'Cashier', 'POS, invoices, returns, farmers and expenses for assigned branch');
