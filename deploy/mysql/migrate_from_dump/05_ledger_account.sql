-- Chart of accounts
-- Source: Dump20260912.sql  →  database skac_new

USE skac_new;
SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;
SET UNIQUE_CHECKS = 0;

INSERT INTO ledger_account (id, organization_id, code, name, type, is_system) VALUES
  (1, 1, '1000', 'Cash', 'asset', 1),
  (2, 1, '1010', 'Bank', 'asset', 1),
  (3, 1, '1200', 'Accounts Receivable (Debtors)', 'asset', 1),
  (4, 1, '1300', 'Inventory', 'asset', 1),
  (5, 1, '1310', 'GST Input Credit', 'asset', 1),
  (6, 1, '2000', 'Accounts Payable (Creditors)', 'liability', 1),
  (7, 1, '2100', 'GST Payable', 'liability', 1),
  (8, 1, '3000', 'Sales', 'income', 1),
  (9, 1, '4000', 'Purchases / COGS', 'expense', 1),
  (10, 1, '4100', 'Transport Charges', 'expense', 1),
  (11, 1, '4200', 'Salaries & Wages', 'expense', 1),
  (12, 1, '4300', 'Rent', 'expense', 1),
  (13, 1, '4400', 'Electricity & Utilities', 'expense', 1),
  (14, 1, '4500', 'Other Operating Expenses', 'expense', 1),
  (15, 1, '5000', 'Owner Capital', 'equity', 1);

ALTER TABLE `ledger_account` AUTO_INCREMENT = 16;

SET UNIQUE_CHECKS = 1;
SET FOREIGN_KEY_CHECKS = 1;
