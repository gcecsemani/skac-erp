-- Optional data backfill for the Reports / Day-close / loose-billing release.
-- No schema change. Safe to skip: day close already infers branch at read time.
--
-- Why run it: older khata receipts were saved with branch_id NULL. Owner day
-- close and "Money collected" then missed them when filtering by shop.
-- This stamps the farmer's latest billed shop onto those rows.
--
-- Idempotent. Does not touch receipts that already have a branch.
-- Does not change amounts, dates, or farmer outstanding.
--
--   mysql -u USER -p skac < deploy/mysql/backfill_customer_payment_branch.sql
--
-- Docker prod:
--   docker compose -f docker-compose.prod.yml --env-file .env.prod exec -T db \
--     mysql -u skac -p"$MYSQL_PASSWORD" skac < deploy/mysql/backfill_customer_payment_branch.sql

USE skac;
SET NAMES utf8mb4;

-- Preview first (optional):
--   SELECT COUNT(*) FROM customer_payment WHERE branch_id IS NULL;

UPDATE customer_payment cp
JOIN (
  SELECT i.customer_id, i.organization_id, i.branch_id
  FROM invoice i
  INNER JOIN (
    SELECT customer_id, organization_id, MAX(id) AS max_id
    FROM invoice
    WHERE customer_id IS NOT NULL
      AND status = 'finalized'
    GROUP BY customer_id, organization_id
  ) last_inv
    ON last_inv.max_id = i.id
) inv
  ON inv.customer_id = cp.customer_id
 AND inv.organization_id = cp.organization_id
SET cp.branch_id = inv.branch_id
WHERE cp.branch_id IS NULL;

-- If an org has only one shop, fill anything still blank.
UPDATE customer_payment cp
JOIN (
  SELECT organization_id, MIN(id) AS only_branch_id
  FROM branch
  WHERE is_deleted = 0
  GROUP BY organization_id
  HAVING COUNT(*) = 1
) b ON b.organization_id = cp.organization_id
SET cp.branch_id = b.only_branch_id
WHERE cp.branch_id IS NULL;
