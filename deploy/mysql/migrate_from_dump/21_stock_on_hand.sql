-- Physical stock on hand from Stock Master.xlsx (Sheet1)
-- Review before running. Safe to re-run.
--
-- Branch map:
--   Avalurpet column  →  branch 1  AVALURPET (AVL)
--   TVM Shop column   →  branch 2  TIRUVANNAMALAI (TVM)
--   Godown column     →  ignored
--
-- Skip rules: blank TVM / Avalurpet is skipped for that branch.
-- Rows with both shop columns blank are skipped. 0 is treated as counted (stock set to 0).
-- Counted qty is stored on a STOCK-ON-HAND batch looked up/created by product_id
-- (does not depend on dump batch ids, which may not exist in a live DB).
--
-- Sheet rows: 511  skipped (no qty): 219
-- Matched with qty: 236  unmatched: 56
--
-- STEP 1 zeros dump opening stock (LEGACY-OPENING) on both branches.
-- Comment out STEP 1 if you only want to overlay counted SKUs.
--
--   mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/21_stock_on_hand.sql

USE skac_new;
SET NAMES utf8mb4;

-- ---------------------------------------------------------------------------
-- STEP 0) Opening batch per counted product (id comes from live batch table)
-- ---------------------------------------------------------------------------
INSERT INTO batch (organization_id, product_id, batch_no, expiry_date, purchase_price)
SELECT p.organization_id, p.id, 'STOCK-ON-HAND', NULL, COALESCE(p.purchase_price, 0)
FROM product p
WHERE p.organization_id = 1 AND p.id IN (18, 130, 158, 184, 228, 232, 252, 253, 260, 261, 262, 299, 310, 311, 326, 327, 345, 357, 395, 429, 543, 571, 572, 573, 579, 607, 608, 613, 686, 747, 803, 810, 873, 881, 952, 991, 1018, 1019, 1020, 1037, 1038, 1042, 1045, 1067, 1081, 1119, 1159, 1198, 1283, 1315, 1343, 1386, 1396, 1454, 1502, 1536, 1541, 1542, 1576, 1595, 1655, 1669, 1687, 1690, 1708, 1710, 1724, 1731, 1783, 1784, 1793, 1835, 1912, 1970, 1987, 2006, 2010, 2011, 2072, 2074, 2119, 2133, 2135, 2165, 2179, 2204, 2225, 2226, 2261, 2322, 2344, 2361, 2403, 2448, 2449, 2470, 2490, 2492, 2507, 2538, 2544, 2576, 2589, 2616, 2617, 2619, 2620, 2622, 2623, 2636, 2663, 2670, 2671, 2676, 2690, 2714, 2720, 2721, 2734, 2735, 2745, 2779, 2791, 2807, 2810, 2811, 2836, 2858, 2908, 2916, 2920, 2927, 2960, 2961, 2970, 2973, 2974, 2980, 2995, 2996, 2997, 2998, 3004, 3012, 3014, 3023, 3024, 3025, 3026, 3046, 3053, 3086, 3104, 3105, 3116, 3125, 3126, 3152, 3172, 3193, 3216, 3217, 3233, 3241, 3243, 3246, 3247, 3268, 3298, 3312, 3325, 3326, 3327, 3331, 3360, 3370, 3371, 3398, 3416, 3424, 3435, 3444, 3448, 3449, 3464, 3473, 3499, 3520, 3522, 3526, 3554, 3573, 3595, 3605, 3632, 3645, 3671, 3672, 3674, 3675, 3704, 3717, 3722, 3729, 3732, 3734, 3737, 3760, 3764, 3766, 3769, 3775, 3777, 3797, 3806, 3808, 3811, 3816, 3817, 3827, 3829, 3850, 3852, 3874, 3875, 3876, 3880)
  AND NOT EXISTS (
    SELECT 1 FROM batch b
    WHERE b.organization_id = p.organization_id
      AND b.product_id = p.id
      AND b.batch_no = 'STOCK-ON-HAND'
  );

-- ---------------------------------------------------------------------------
-- STEP 1) Clear dump opening stock (LEGACY-OPENING) on both shops
-- ---------------------------------------------------------------------------
UPDATE stock s
JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'LEGACY-OPENING'
SET s.quantity = 0, s.updated_at = NOW()
WHERE s.organization_id = 1;

-- ---------------------------------------------------------------------------
-- STEP 2) Set counted quantities on STOCK-ON-HAND
-- ---------------------------------------------------------------------------

-- 19:19:19 VAJRA - 100 ML  (product_id=3880, match=alias)
--   sheet Vajra 19:19:19 / 100 ml   TVM=73  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3880, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3880 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3880 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3880;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3880, b.id, 73 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3880 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3880 SET s.quantity = 73, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3880;
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3880 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');

-- ABATIS - 80 ML  (product_id=3729, match=exact)
--   sheet Abatis / 80 ml   TVM=-  Avalurpet=9
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3729, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3729 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3729 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3729;
UPDATE batch SET expiry_date = '2027-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3729 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-05-01');

-- ACADEMY - 100 GMS  (product_id=3737, match=exact)
--   sheet Academy / 100 Gm   TVM=-  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3737, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3737 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3737 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3737;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3737 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- ACADEMY - 40 GMS  (product_id=3734, match=exact)
--   sheet Academy / 40 Gm   TVM=-  Avalurpet=19
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3734, b.id, 19 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3734 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3734 SET s.quantity = 19, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3734;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3734 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- ALANTO - 100MLS  (product_id=18, match=exact)
--   sheet Alanto / 100 ml   TVM=13  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 18, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 18 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 18 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 18;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 18 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- AMISTAR - 100 ML  (product_id=1454, match=exact)
--   sheet Amistar / 100 ml   TVM=10  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1454, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1454 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1454 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1454;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1454 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- AMPLIGO - 100 ML  (product_id=2927, match=exact)
--   sheet Ampligo / 100 ml   TVM=-  Avalurpet=9
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2927, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2927 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2927 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2927;
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2927 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');

-- AMPLIGO - 200 ML  (product_id=686, match=exact)
--   sheet Ampligo / 200 ml   TVM=-  Avalurpet=28
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 686, b.id, 28 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 686 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 686 SET s.quantity = 28, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 686;
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 686 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');

-- AVENGER - 250 ML  (product_id=429, match=exact)
--   sheet Avenger / 250 ml   TVM=-  Avalurpet=9
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 429, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 429 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 429 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 429;

-- AZADI - 250 ML  (product_id=1595, match=exact)
--   sheet Azadi / 250 ml   TVM=4  Avalurpet=19
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1595, b.id, 19 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1595 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1595 SET s.quantity = 19, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1595;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1595, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1595 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1595 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1595;

-- AZADI - 500 ML  (product_id=2135, match=exact)
--   sheet Azadi / 500 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2135, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2135 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2135 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2135;

-- BALORIC - 400 ML  (product_id=3243, match=exact)
--   sheet Baloric / 400 ml   TVM=-  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3243, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3243 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3243 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3243;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3243 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- BANCO - 1 LTR  (product_id=3605, match=exact)
--   sheet Banco / 1 L   TVM=10  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3605, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3605 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3605 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3605;

-- BANCO - 100 ML  (product_id=3246, match=exact)
--   sheet Banco / 100 ml   TVM=67  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3246, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3246 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3246 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3246;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3246, b.id, 67 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3246 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3246 SET s.quantity = 67, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3246;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3246 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- BANCO - 250 ML  (product_id=3247, match=exact)
--   sheet Banco / 250 Ml   TVM=37  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3247, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3247 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3247 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3247;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3247, b.id, 37 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3247 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3247 SET s.quantity = 37, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3247;
UPDATE batch SET expiry_date = '2029-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3247 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-04-01');

-- BESTMAN - 50 ML  (product_id=3554, match=compact-name)
--   sheet Best Man / 50 ml   TVM=51  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3554, b.id, 51 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3554 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3554 SET s.quantity = 51, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3554;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3554 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- BISON - 100 ML  (product_id=3104, match=exact)
--   sheet Bison / 100 ml   TVM=7  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3104, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3104 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3104 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3104;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3104, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3104 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3104 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3104;
UPDATE batch SET expiry_date = '2030-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3104 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2030-06-01');

-- BLAID EW - 600 ML  (product_id=3416, match=exact)
--   sheet Blaid EW / 600 ml   TVM=-  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3416, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3416 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3416 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3416;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3416 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- BLOOM FLOWER - 100 ML  (product_id=803, match=compact-name)
--   sheet Bloomflower / 100 ml   TVM=-  Avalurpet=13
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 803, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 803 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 803 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 803;

-- BREEZ FOLIAR - 250ML  (product_id=1710, match=packing+tokens)
--   sheet Breez / 250 ml   TVM=-  Avalurpet=42
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1710, b.id, 42 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1710 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1710 SET s.quantity = 42, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1710;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1710 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- BULLET - 1 L  (product_id=1020, match=exact)
--   sheet Bullet / 1 L   TVM=3  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1020, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1020 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1020 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1020;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1020 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- BULLET - 100 ML  (product_id=1576, match=exact)
--   sheet Bullet / 100 ml   TVM=26  Avalurpet=18
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1576, b.id, 18 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1576 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1576 SET s.quantity = 18, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1576;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1576, b.id, 26 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1576 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1576 SET s.quantity = 26, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1576;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1576 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- BULLET - 250 ML  (product_id=1018, match=exact)
--   sheet Bullet / 250 ml   TVM=17  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1018, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1018 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1018 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1018;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1018, b.id, 17 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1018 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1018 SET s.quantity = 17, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1018;
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1018 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');

-- BULLET - 500 ML  (product_id=1019, match=exact)
--   sheet Bullet / 500 ml   TVM=20  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1019, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1019 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1019 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1019;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1019 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- CALARIS XTRA - 1400ML  (product_id=1793, match=exact)
--   sheet Calaris Xtra / 1400 ml   TVM=-  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1793, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1793 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1793 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1793;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1793 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- CALARIS XTRA - 700 ML  (product_id=2589, match=exact)
--   sheet Calaris Xtra / 700 ml   TVM=-  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2589, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2589 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2589 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2589;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2589 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- CAP-X-SP - 100 GMS  (product_id=747, match=packing+tokens)
--   sheet Cap X / 100 Gm   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 747, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 747 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 747 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 747;
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 747 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');

-- CARNAGE - 500 GMS  (product_id=3722, match=exact)
--   sheet Carnage / 500 Gm   TVM=-  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3722, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3722 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3722 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3722;

-- CEASEMITE - 100 ML  (product_id=2322, match=exact)
--   sheet CeaseMite / 100 ml   TVM=-  Avalurpet=23
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2322, b.id, 23 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2322 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2322 SET s.quantity = 23, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2322;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2322 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- CEASEMITE - 250 ML  (product_id=2663, match=exact)
--   sheet CeaseMite / 250 ml   TVM=41  Avalurpet=9
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2663, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2663 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2663 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2663;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2663, b.id, 41 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2663 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2663 SET s.quantity = 41, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2663;
UPDATE batch SET expiry_date = '2027-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2663 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-02-01');

-- CEASEMITE - 50 ML  (product_id=2361, match=exact)
--   sheet CeaseMite / 50 ml   TVM=20  Avalurpet=31
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2361, b.id, 31 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2361 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2361 SET s.quantity = 31, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2361;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2361, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2361 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2361 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2361;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2361 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- COMBI PLUS - 100 GMS  (product_id=573, match=exact)
--   sheet Combi Plus / 100 Gm   TVM=32  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 573, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 573 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 573 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 573;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 573 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- COMBI PLUS - 250 GMS  (product_id=1067, match=exact)
--   sheet Combi Plus / 250 Gm   TVM=25  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1067, b.id, 25 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1067 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1067 SET s.quantity = 25, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1067;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1067 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- COMBI PLUS - 500 GMS  (product_id=1502, match=exact)
--   sheet Combi Plus / 500 Gm   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1502, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1502 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1502 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1502;
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1502 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');

-- COUNCIL ACTIV - 45 GMS  (product_id=1541, match=exact)
--   sheet Council Activ / 45 gm   TVM=-  Avalurpet=17
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1541, b.id, 17 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1541 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1541 SET s.quantity = 17, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1541;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1541 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- COUNCIL ACTIV - 90 GMS  (product_id=1542, match=exact)
--   sheet Council Activ / 90 Gm   TVM=-  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1542, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1542 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1542 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1542;
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1542 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');

-- COVER - 10 ML  (product_id=2544, match=exact)
--   sheet Cover / 10 ml   TVM=-  Avalurpet=305
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2544, b.id, 305 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2544 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2544 SET s.quantity = 305, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2544;
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2544 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');

-- COVER - 150 ML  (product_id=3522, match=exact)
--   sheet Cover / 150 ml   TVM=-  Avalurpet=32
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3522, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3522 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3522 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3522;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3522 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- COVER - 30 ML  (product_id=3520, match=exact)
--   sheet Cover / 30 ml   TVM=-  Avalurpet=200
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3520, b.id, 200 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3520 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3520 SET s.quantity = 200, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3520;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3520 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- CRAZY PRO - 1 LTR  (product_id=3674, match=exact)
--   sheet Crazy Pro / 1 L   TVM=1  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3674, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3674 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3674 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3674;
UPDATE batch SET expiry_date = '2026-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3674 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-08-01');

-- CRAZY PRO - 250 ML  (product_id=3298, match=exact)
--   sheet Crazy Pro / 250 ml   TVM=-  Avalurpet=29
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3298, b.id, 29 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3298 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3298 SET s.quantity = 29, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3298;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3298 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- CRAZY PRO - 500 ML  (product_id=3675, match=exact)
--   sheet Crazy Pro / 500 ml   TVM=5  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3675, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3675 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3675 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3675;
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3675 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');

-- DELEGATE - 100 ML  (product_id=1396, match=exact)
--   sheet Delegate / 100 ml   TVM=18  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1396, b.id, 18 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1396 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1396 SET s.quantity = 18, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1396;
UPDATE batch SET expiry_date = '2027-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1396 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-05-01');

-- DELEGATE - 20 ML  (product_id=2261, match=exact)
--   sheet Delegate / 20 ml   TVM=8  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2261, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2261 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2261 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2261;
UPDATE batch SET expiry_date = '2027-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2261 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-02-01');

-- DHANUVIT - 100 ML  (product_id=2448, match=exact)
--   sheet Dhanuvit / 100 ml   TVM=-  Avalurpet=115
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2448, b.id, 115 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2448 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2448 SET s.quantity = 115, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2448;
UPDATE batch SET expiry_date = '2031-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2448 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2031-01-01');

-- DHANUVIT - 250 ML  (product_id=2449, match=exact)
--   sheet Dhanuvit / 250 ml   TVM=16  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2449, b.id, 16 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2449 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2449 SET s.quantity = 16, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2449;
UPDATE batch SET expiry_date = '2023-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2449 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2023-10-01');

-- DRYUP GOLD - 10 ML  (product_id=1783, match=compact-name)
--   sheet Dry Up Gold / 10 ml   TVM=-  Avalurpet=47
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1783, b.id, 47 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1783 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1783 SET s.quantity = 47, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1783;
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1783 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');

-- DRYUP GOLD - 100 ML  (product_id=1724, match=compact-name)
--   sheet Dry Up Gold / 100 ml   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1724, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1724 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1724 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1724;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1724 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- DRYUP GOLD - 500 ML  (product_id=3152, match=compact-name)
--   sheet Dry Up Gold / 500 ml   TVM=5  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3152, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3152 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3152 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3152;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3152 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- DURSBAN - 100 ML  (product_id=3850, match=exact)
--   sheet Dursban / 100 ml   TVM=17  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3850, b.id, 17 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3850 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3850 SET s.quantity = 17, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3850;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3850 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- FAITA - 160 ML  (product_id=3672, match=exact)
--   sheet Faita / 160 ml   TVM=28  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3672, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3672 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3672 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3672;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3672, b.id, 28 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3672 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3672 SET s.quantity = 28, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3672;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3672 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- FAITA - 40 ML  (product_id=3760, match=exact)
--   sheet Faita / 40 ml   TVM=32  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3760, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3760 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3760 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3760;

-- FAITA - 80 ML  (product_id=3717, match=exact)
--   sheet Faita / 80 ml   TVM=2  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3717, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3717 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3717 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3717;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3717 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- FANTACPLUS - 100 ML  (product_id=2165, match=compact-name)
--   sheet Fantac Plus / 100 ml   TVM=-  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2165, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2165 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2165 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2165;
UPDATE batch SET expiry_date = '2027-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2165 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-03-01');

-- FENNY - 1 LTR  (product_id=3241, match=exact)
--   sheet Fenny / 1 L   TVM=4  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3241, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3241 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3241 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3241;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3241, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3241 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3241 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3241;

-- FENNY - 100 ML  (product_id=2960, match=exact)
--   sheet Fenny / 100 ml   TVM=201  Avalurpet=36
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2960, b.id, 36 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2960 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2960 SET s.quantity = 36, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2960;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2960, b.id, 201 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2960 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2960 SET s.quantity = 201, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2960;
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2960 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');

-- FENNY - 250 ML  (product_id=2961, match=exact)
--   sheet Fenny / 250 ml   TVM=15  Avalurpet=56
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2961, b.id, 56 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2961 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2961 SET s.quantity = 56, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2961;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2961, b.id, 15 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2961 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2961 SET s.quantity = 15, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2961;

-- FENNY - 500 ML  (product_id=3172, match=exact)
--   sheet Fenny / 500 ml   TVM=35  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3172, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3172 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3172 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3172;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3172, b.id, 35 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3172 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3172 SET s.quantity = 35, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3172;

-- FERIO - 1L  (product_id=2179, match=exact)
--   sheet Ferio / 1 L   TVM=8  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2179, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2179 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2179 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2179;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2179 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- FERTICEM - 1 LITR  (product_id=1159, match=exact)
--   sheet Ferticem / 1 L   TVM=-  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1159, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1159 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1159 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1159;
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1159 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');

-- FERTICEM - 250MLS  (product_id=130, match=exact)
--   sheet Ferticem / 250 ml   TVM=24  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 130, b.id, 24 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 130 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 130 SET s.quantity = 24, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 130;
UPDATE batch SET expiry_date = '2029-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 130 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-03-01');

-- FERTICEM - 500 ML  (product_id=1045, match=exact)
--   sheet Ferticem / 500 ml   TVM=11  Avalurpet=13
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1045, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1045 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1045 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1045;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1045, b.id, 11 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1045 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1045 SET s.quantity = 11, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1045;
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1045 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');

-- FLICK SUPER - 600 GMS  (product_id=2920, match=exact)
--   sheet Flick Super / 600 Gm   TVM=3  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2920, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2920 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2920 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2920;
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2920 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');

-- FORWARD - 250 ML  (product_id=810, match=exact)
--   sheet Forward / 250 ml   TVM=-  Avalurpet=44
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 810, b.id, 44 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 810 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 810 SET s.quantity = 44, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 810;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 810 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- FORWARD - 500 ML  (product_id=1343, match=exact)
--   sheet Forward / 500 ml   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1343, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1343 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1343 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1343;

-- GLO IT - 100 ML  (product_id=3012, match=compact-name)
--   sheet Gloit / 100 ml   TVM=6  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3012, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3012 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3012 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3012;
UPDATE batch SET expiry_date = '2028-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3012 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-08-01');

-- GRACIA - 160 ML  (product_id=1912, match=exact)
--   sheet Gracia / 160 ml   TVM=5  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1912, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1912 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1912 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1912;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1912, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1912 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1912 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1912;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1912 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- GRACIA - 40 ML  (product_id=2226, match=exact)
--   sheet Gracia / 40 ml   TVM=-  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2226, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2226 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2226 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2226;

-- GRACIA - 80 ML  (product_id=2225, match=exact)
--   sheet Gracia / 80 ml   TVM=17  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2225, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2225 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2225 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2225;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2225, b.id, 17 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2225 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2225 SET s.quantity = 17, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2225;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2225 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- GRAMOXON - 500 ML  (product_id=3732, match=exact)
--   sheet Gramoxon / 500 ml   TVM=-  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3732, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3732 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3732 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3732;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3732 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- GUBERA - 100MLS  (product_id=158, match=exact)
--   sheet Gubera / 100 ml   TVM=106  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 158, b.id, 106 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 158 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 158 SET s.quantity = 106, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 158;
UPDATE batch SET expiry_date = '2028-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 158 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-09-01');

-- HIGHLIGHT - 250 ML  (product_id=2908, match=exact)
--   sheet Highlight / 250 ml   TVM=3  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2908, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2908 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2908 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2908;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2908 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- HURRICANE PLUS - 100 ML  (product_id=1784, match=alias)
--   sheet Hurrican Plus / 100 ml   TVM=-  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1784, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1784 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1784 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1784;
UPDATE batch SET expiry_date = '2027-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1784 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-06-01');

-- IMUNIT - 120 ML  (product_id=3105, match=exact)
--   sheet Imunit / 120 ml   TVM=21  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3105, b.id, 21 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3105 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3105 SET s.quantity = 21, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3105;
UPDATE batch SET expiry_date = '2026-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3105 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-08-01');

-- INCIPIO - 120 ML  (product_id=2676, match=exact)
--   sheet Incipio / 120 ml   TVM=-  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2676, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2676 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2676 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2676;

-- INDOLIZER L - 100 ML  (product_id=2403, match=packing+tokens)
--   sheet Indolizer / 100 ml   TVM=23  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2403, b.id, 23 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2403 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2403 SET s.quantity = 23, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2403;
UPDATE batch SET expiry_date = '2029-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2403 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-06-01');

-- IRIS - 400 ML  (product_id=395, match=exact)
--   sheet Iris / 400 ml   TVM=1  Avalurpet=11
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 395, b.id, 11 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 395 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 395 SET s.quantity = 11, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 395;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 395, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 395 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 395 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 395;
UPDATE batch SET expiry_date = '2026-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 395 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-09-01');

-- ISABION - 500MLS  (product_id=184, match=exact)
--   sheet Isabion / 500 ml   TVM=-  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 184, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 184 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 184 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 184;
UPDATE batch SET expiry_date = '2031-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 184 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2031-03-01');

-- ISACARB - 100 ML  (product_id=3704, match=exact)
--   sheet Isacarb / 100 ml   TVM=5  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3704, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3704 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3704 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3704;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3704 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- IZUKA - 3.6 GMS  (product_id=3764, match=exact)
--   sheet Izuka / 3.6 g   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3764, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3764 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3764 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3764;
UPDATE batch SET expiry_date = '2027-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3764 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-06-01');

-- IZUKA - 36 GMS  (product_id=3766, match=exact)
--   sheet Izuka / 36 Gm   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3766, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3766 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3766 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3766;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3766 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- JAMINDAR - 1 LITR  (product_id=2995, match=exact)
--   sheet Jamindar / 1 L   TVM=1  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2995, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2995 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2995 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2995;

-- JAMINDAR - 1 LITR  (product_id=2995, match=exact)
--   sheet Jamindar / 1 L   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2995, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2995 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2995 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2995;

-- JAMINDAR - 100 ML  (product_id=2636, match=exact)
--   sheet Jamindar / 100 ml   TVM=14  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2636, b.id, 14 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2636 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2636 SET s.quantity = 14, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2636;
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2636 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');

-- JAMINDAR - 100 ML  (product_id=2636, match=exact)
--   sheet Jamindar / 100 ml   TVM=0  Avalurpet=70
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2636, b.id, 70 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2636 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2636 SET s.quantity = 70, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2636;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2636, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2636 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2636 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2636;
UPDATE batch SET expiry_date = '2029-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2636 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-05-01');

-- JAMINDAR - 250 ML  (product_id=2623, match=exact)
--   sheet Jamindar / 250 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2623, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2623 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2623 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2623;
UPDATE batch SET expiry_date = '2028-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2623 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-10-01');

-- JAMINDAR - 250 ML  (product_id=2623, match=exact)
--   sheet Jamindar / 250 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2623, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2623 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2623 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2623;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2623 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- JAMINDAR - 500 ML  (product_id=2974, match=exact)
--   sheet Jamindar / 500 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2974, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2974 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2974 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2974;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2974 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- JAMINDAR - 500 ML  (product_id=2974, match=exact)
--   sheet Jamindar / 500 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2974, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2974 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2974 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2974;

-- JIVORA - 500 GMS  (product_id=3769, match=exact)
--   sheet Jivora / 500 Gm   TVM=5  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3769, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3769 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3769 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3769;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3769, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3769 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3769 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3769;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3769 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- JUMP 2 GMS - 2 GMS  (product_id=608, match=packing+tokens)
--   sheet Jump / 2 gm   TVM=140  Avalurpet=240
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 608, b.id, 240 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 608 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 608 SET s.quantity = 240, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 608;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 608, b.id, 140 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 608 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 608 SET s.quantity = 140, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 608;
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 608 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');

-- KANTROL PLUSS - 100 ML  (product_id=3312, match=alias)
--   sheet Kantrol Plus / 100 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3312, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3312 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3312 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3312;

-- KAVACHAM - 100 GMS  (product_id=3371, match=exact)
--   sheet Kavacham / 100 Gms   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3371, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3371 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3371 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3371;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3371 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- KAVACHAM - 250 GMS  (product_id=3449, match=exact)
--   sheet Kavacham / 250 Gms   TVM=7  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3449, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3449 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3449 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3449;
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3449 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');

-- KAVACHAM - 500 GMS  (product_id=3499, match=exact)
--   sheet Kavacham / 500 Gms   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3499, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3499 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3499 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3499;

-- KEMLOX - 100 ML  (product_id=579, match=exact)
--   sheet Kemlox / 100 ml   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 579, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 579 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 579 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 579;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 579 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- KEMSTAR - 100 GMS  (product_id=1708, match=exact)
--   sheet Kemstar / 100 Gm   TVM=35  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1708, b.id, 35 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1708 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1708 SET s.quantity = 35, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1708;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1708 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- KEMSTAR - 5 GMS  (product_id=1081, match=exact)
--   sheet Kemstar / 5 Gm   TVM=-  Avalurpet=23
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1081, b.id, 23 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1081 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1081 SET s.quantity = 23, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1081;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1081 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- KEMSTAR EASY - 100 ML  (product_id=2714, match=exact)
--   sheet Kemstar Easy / 100 ml   TVM=-  Avalurpet=21
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2714, b.id, 21 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2714 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2714 SET s.quantity = 21, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2714;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2714 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- KEMSTAR EASY - 250 ML  (product_id=2735, match=exact)
--   sheet Kemstar Easy / 250 ml   TVM=-  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2735, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2735 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2735 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2735;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2735 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- KICKER - 100 ML  (product_id=3026, match=alias)
--   sheet Kicker Plus / 100 ml   TVM=14  Avalurpet=48
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3026, b.id, 48 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3026 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3026 SET s.quantity = 48, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3026;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3026, b.id, 14 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3026 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3026 SET s.quantity = 14, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3026;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3026 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- KINGZYME L - 100 ML  (product_id=2622, match=packing+tokens)
--   sheet Kingzyme / 100 ml   TVM=73  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2622, b.id, 73 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2622 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2622 SET s.quantity = 73, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2622;
UPDATE batch SET expiry_date = '2026-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2622 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-12-01');

-- KITE - 250 ML  (product_id=2779, match=exact)
--   sheet Kite / 250 ml   TVM=8  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2779, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2779 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2779 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2779;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2779 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- LARA - 909 - 100 ML  (product_id=952, match=exact)
--   sheet Lara 909 / 100 ml   TVM=13  Avalurpet=12
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 952, b.id, 12 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 952 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 952 SET s.quantity = 12, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 952;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 952, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 952 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 952 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 952;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 952 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- LARA - 909 - 250 ML  (product_id=1042, match=exact)
--   sheet Lara 909 / 250 ml   TVM=-  Avalurpet=9
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1042, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1042 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1042 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1042;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1042 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- LETHAL GOLD - 100 ML  (product_id=2670, match=exact)
--   sheet Lethal Gold / 100 ml   TVM=42  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2670, b.id, 42 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2670 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2670 SET s.quantity = 42, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2670;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2670 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- LETHAL GOLD - 250 ML  (product_id=2671, match=exact)
--   sheet Lethal Gold / 250 ml   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2671, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2671 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2671 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2671;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2671 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- LIGER - 100 ML  (product_id=3004, match=exact)
--   sheet Liger / 100 ml   TVM=36  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3004, b.id, 36 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3004 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3004 SET s.quantity = 36, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3004;
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3004 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');

-- LIHOCIN - 250 ML  (product_id=3331, match=exact)
--   sheet Lihocin / 250 ml   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3331, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3331 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3331 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3331;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3331 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- LUNA EXPERINACE - 250 ML  (product_id=3645, match=exact)
--   sheet Luna Experinace / 250 ml   TVM=14  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3645, b.id, 14 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3645 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3645 SET s.quantity = 14, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3645;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3645 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- LUSH - 30 ML  (product_id=3473, match=exact)
--   sheet Lush / 30 ml   TVM=-  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3473, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3473 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3473 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3473;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3473 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- LUSH - 30 ML  (product_id=3473, match=exact)
--   sheet Lush / 30 ml   TVM=5  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3473, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3473 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3473 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3473;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3473 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- M-CON - 100 ML  (product_id=1037, match=exact)
--   sheet M con / 100ml   TVM=38  Avalurpet=20
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1037, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1037 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1037 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1037;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1037, b.id, 38 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1037 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1037 SET s.quantity = 38, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1037;
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1037 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');

-- M-CON - 50 ML  (product_id=1038, match=exact)
--   sheet M con / 50 ml   TVM=60  Avalurpet=20
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1038, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1038 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1038 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1038;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1038, b.id, 60 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1038 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1038 SET s.quantity = 60, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1038;
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1038 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');

-- MAAGRO - 50 ML  (product_id=3325, match=exact)
--   sheet Maagro / 50 ml   TVM=15  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3325, b.id, 15 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3325 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3325 SET s.quantity = 15, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3325;
UPDATE batch SET expiry_date = '1931-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3325 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '1931-04-01');

-- MEDISOL OCEANIC - 100 ML  (product_id=3053, match=exact)
--   sheet Medisol Oceanic / 100 ml   TVM=17  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3053, b.id, 17 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3053 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3053 SET s.quantity = 17, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3053;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3053 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- MERITOR - 250 ML  (product_id=3671, match=exact)
--   sheet Meritor / 250 ml   TVM=26  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3671, b.id, 26 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3671 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3671 SET s.quantity = 26, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3671;
UPDATE batch SET expiry_date = '2027-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3671 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-06-01');

-- MIRACLE - 250MLS  (product_id=228, match=exact)
--   sheet Miracle / 250 ml   TVM=14  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 228, b.id, 14 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 228 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 228 SET s.quantity = 14, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 228;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 228 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- MIRACLE - 500 ML  (product_id=3126, match=exact)
--   sheet Miracle / 500 ml   TVM=9  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3126, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3126 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3126 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3126;
UPDATE batch SET expiry_date = '2026-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3126 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-08-01');

-- MIRACULAN 100 ML - 250 ML  (product_id=1987, match=packing+tokens)
--   sheet Miraculan / 250 ml   TVM=-  Avalurpet=17
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1987, b.id, 17 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1987 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1987 SET s.quantity = 17, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1987;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1987 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- MIRACULAN 100 ML - 50 ML  (product_id=2204, match=packing+tokens)
--   sheet Miraculan / 50 ml   TVM=95  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2204, b.id, 95 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2204 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2204 SET s.quantity = 95, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2204;
UPDATE batch SET expiry_date = '2027-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2204 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-03-01');

-- MITIGATE - 100MLS  (product_id=232, match=exact)
--   sheet Mitigate / 100 ml   TVM=10  Avalurpet=11
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 232, b.id, 11 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 232 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 232 SET s.quantity = 11, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 232;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 232, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 232 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 232 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 232;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 232 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- MOVENTO ENERGY - 100 ML  (product_id=873, match=exact)
--   sheet Movento Energy / 100 ml   TVM=-  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 873, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 873 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 873 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 873;
UPDATE batch SET expiry_date = '2027-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 873 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-02-01');

-- MOVENTO OD - 100 ML  (product_id=2010, match=exact)
--   sheet Movento OD / 100 ml   TVM=-  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2010, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2010 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2010 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2010;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2010 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- MOVENTO OD - 250 ML  (product_id=2011, match=exact)
--   sheet Movento OD / 250 ml   TVM=18  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2011, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2011 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2011 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2011;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2011, b.id, 18 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2011 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2011 SET s.quantity = 18, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2011;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2011 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- NANO Q - 100 ML  (product_id=2616, match=exact)
--   sheet Nano Q / 100 ml   TVM=-  Avalurpet=37
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2616, b.id, 37 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2616 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2616 SET s.quantity = 37, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2616;
UPDATE batch SET expiry_date = '2026-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2616 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-12-01');

-- NANO Q - 100 ML  (product_id=2616, match=exact)
--   sheet Nano Q / 100 ml   TVM=20  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2616, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2616 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2616 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2616;
UPDATE batch SET expiry_date = '2026-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2616 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-12-01');

-- NOVLECT - 250 ML  (product_id=3216, match=exact)
--   sheet Novlect / 250 ml   TVM=-  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3216, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3216 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3216 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3216;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3216 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- NOVLECT - 500 ML  (product_id=2490, match=exact)
--   sheet Novlect / 500 ml   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2490, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2490 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2490 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2490;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2490 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- OMITE 57 EC - 100MLS  (product_id=252, match=packing+tokens)
--   sheet Omite / 100 ml   TVM=-  Avalurpet=12
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 252, b.id, 12 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 252 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 252 SET s.quantity = 12, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 252;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 252 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- OMITE 57 EC - 250MLS  (product_id=253, match=alias)
--   sheet Omite / 250 ml   TVM=40  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 253, b.id, 40 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 253 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 253 SET s.quantity = 40, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 253;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 253 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- PASIDI-6 - 100 ML  (product_id=3268, match=exact)
--   sheet Pasidi-6 / 100 ml   TVM=26  Avalurpet=2
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3268, b.id, 2 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3268 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3268 SET s.quantity = 2, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3268;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3268, b.id, 26 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3268 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3268 SET s.quantity = 26, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3268;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3268 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- PASIDI-6 - 250 ML  (product_id=3464, match=exact)
--   sheet Pasidi-6 / 250 ml   TVM=0  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3464, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3464 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3464 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3464;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3464, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3464 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3464 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3464;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3464 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- PASIDI-6 - 30 ML  (product_id=3024, match=exact)
--   sheet Pasidi-6 / 30 ml   TVM=0  Avalurpet=63
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3024, b.id, 63 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3024 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3024 SET s.quantity = 63, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3024;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3024, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3024 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3024 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3024;
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3024 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');

-- PASIDI-6 - 50 ML  (product_id=3025, match=exact)
--   sheet Pasidi-6 / 50 ml   TVM=19  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3025, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3025 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3025 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3025;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3025, b.id, 19 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3025 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3025 SET s.quantity = 19, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3025;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3025 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- PATELA - 200 ML  (product_id=1198, match=exact)
--   sheet Patela / 200 ml   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1198, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1198 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1198 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1198;
UPDATE batch SET expiry_date = '2027-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1198 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-05-01');

-- PAUSHAK - 100 ML  (product_id=2006, match=exact)
--   sheet Paushak / 100 ml   TVM=-  Avalurpet=42
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2006, b.id, 42 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2006 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2006 SET s.quantity = 42, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2006;
UPDATE batch SET expiry_date = '2028-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2006 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-09-01');

-- PAUSHAK - 250 ML  (product_id=1119, match=exact)
--   sheet Paushak / 250 ml   TVM=-  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1119, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1119 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1119 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1119;
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1119 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');

-- PAUSHAK - 50 ML  (product_id=2133, match=exact)
--   sheet Paushak / 50 ml   TVM=165  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2133, b.id, 165 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2133 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2133 SET s.quantity = 165, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2133;
UPDATE batch SET expiry_date = '2029-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2133 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-01-01');

-- PENITRO - 50 ML  (product_id=3874, match=exact)
--   sheet Penitro / 50 ml   TVM=72  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3874, b.id, 72 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3874 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3874 SET s.quantity = 72, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3874;
UPDATE batch SET expiry_date = '2029-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3874 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-08-01');

-- PERFEKT - 100 ML  (product_id=1690, match=exact)
--   sheet Perfekt / 100 ml   TVM=4  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1690, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1690 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1690 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1690;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1690 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- PERFEKT - 100 ML  (product_id=1690, match=exact)
--   sheet Perfekt / 100 ml   TVM=8  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1690, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1690 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1690 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1690;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1690 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- PHENDAL - 1 LTR  (product_id=3014, match=exact)
--   sheet Phendal / 1 L   TVM=10  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3014, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3014 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3014 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3014;
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3014 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');

-- PHENDAL - 100MLS  (product_id=262, match=exact)
--   sheet Phendal / 100 ml   TVM=72  Avalurpet=18
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 262, b.id, 18 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 262 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 262 SET s.quantity = 18, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 262;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 262, b.id, 72 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 262 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 262 SET s.quantity = 72, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 262;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 262 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- PHENDAL - 250MLS  (product_id=260, match=exact)
--   sheet Phendal / 250 ml   TVM=15  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 260, b.id, 15 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 260 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 260 SET s.quantity = 15, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 260;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 260 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- PHENDAL - 500MLS  (product_id=261, match=exact)
--   sheet Phendal / 500 ml   TVM=9  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 261, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 261 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 261 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 261;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 261 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- PLESIVA - 125 ML  (product_id=3808, match=exact)
--   sheet Plesiva / 125 ml   TVM=56  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3808, b.id, 56 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3808 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3808 SET s.quantity = 56, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3808;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3808 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- POSHAK SEA DIAMOND - 1 LTR  (product_id=3573, match=packing+tokens)
--   sheet Sea Diamond / 1 L   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3573, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3573 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3573 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3573;

-- POSHAK SEA DIAMOND - 100 ML  (product_id=2996, match=packing+tokens)
--   sheet Sea Diamond / 100 ml   TVM=5  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2996, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2996 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2996 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2996;
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2996 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');

-- POSHAK SEA DIAMOND - 250 ML  (product_id=2997, match=packing+tokens)
--   sheet Sea Diamond / 250 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2997, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2997 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2997 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2997;

-- POSHAK SEA DIAMOND - 500 ML  (product_id=2998, match=packing+tokens)
--   sheet Sea Diamond / 500 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2998, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2998 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2998 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2998;

-- POW - 500 ML  (product_id=543, match=exact)
--   sheet Pow / 500 ml   TVM=-  Avalurpet=16
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 543, b.id, 16 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 543 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 543 SET s.quantity = 16, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 543;
UPDATE batch SET expiry_date = '2029-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 543 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-01-01');

-- POWERPULL - 100 ML  (product_id=3444, match=exact)
--   sheet PowerPull / 100 ml   TVM=86  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3444, b.id, 86 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3444 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3444 SET s.quantity = 86, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3444;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3444 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- PRELUDE PLUS - 250 ML  (product_id=2470, match=exact)
--   sheet Prelude Plus / 250 ml   TVM=-  Avalurpet=26
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2470, b.id, 26 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2470 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2470 SET s.quantity = 26, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2470;
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2470 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');

-- PRELUDE PLUS - 600 ML  (product_id=2492, match=exact)
--   sheet Prelude Plus / 600 ml   TVM=-  Avalurpet=1
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2492, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2492 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2492 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2492;
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2492 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');

-- PRETI EW - 600 ML  (product_id=3435, match=alias)
--   sheet Preti Super / 600 ml   TVM=-  Avalurpet=31
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3435, b.id, 31 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3435 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3435 SET s.quantity = 31, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3435;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3435 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- PROCLAIM XTRA - 30 ML  (product_id=3398, match=exact)
--   sheet Proclaim Xtra / 30 ml   TVM=7  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3398, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3398 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3398 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3398;
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3398 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');

-- PROFEX SUPER - 1 L  (product_id=1669, match=exact)
--   sheet Profex Super / 1 L   TVM=1  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1669, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1669 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1669 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1669;

-- PROFEX SUPER - 100 ML  (product_id=571, match=exact)
--   sheet Profex Super / 100 ml   TVM=502  Avalurpet=54
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 571, b.id, 54 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 571 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 571 SET s.quantity = 54, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 571;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 571, b.id, 502 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 571 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 571 SET s.quantity = 502, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 571;
UPDATE batch SET expiry_date = '1900-02-18', updated_at = NOW() WHERE organization_id = 1 AND product_id = 571 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '1900-02-18');

-- PROFEX SUPER - 250 ML  (product_id=572, match=exact)
--   sheet Profex Super / 250 ml   TVM=224  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 572, b.id, 224 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 572 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 572 SET s.quantity = 224, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 572;

-- PROFEX SUPER - 500 ML  (product_id=1283, match=exact)
--   sheet Profex Super / 500 ml   TVM=37  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1283, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1283 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1283 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1283;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1283, b.id, 37 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1283 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1283 SET s.quantity = 37, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1283;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1283 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- PROMITE - 500 ML  (product_id=3806, match=exact)
--   sheet Promite / 500 ml   TVM=4  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3806, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3806 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3806 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3806;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3806 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- PUTIN - 1 LTR  (product_id=2858, match=exact)
--   sheet Putin / 1 L   TVM=-  Avalurpet=8
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2858, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2858 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2858 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2858;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2858 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- QUANTIS - 100 ML  (product_id=3424, match=exact)
--   sheet Quantis / 100 ml   TVM=-  Avalurpet=12
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3424, b.id, 12 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3424 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3424 SET s.quantity = 12, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3424;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3424 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- QUANTIS - 400 ML  (product_id=1386, match=exact)
--   sheet Quantis / 400 ml   TVM=-  Avalurpet=31
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1386, b.id, 31 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1386 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1386 SET s.quantity = 31, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1386;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1386 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- QUICK - 50 GMS  (product_id=607, match=exact)
--   sheet Quick / 50 Gms   TVM=-  Avalurpet=28
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 607, b.id, 28 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 607 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 607 SET s.quantity = 28, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 607;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 607 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- RAFT - 250 ML  (product_id=3526, match=exact)
--   sheet Raft / 250 ml   TVM=20  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3526, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3526 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3526 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3526;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3526, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3526 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3526 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3526;
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3526 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');

-- RAPIGRO - 100MLS  (product_id=299, match=exact)
--   sheet Rapigro / 100 ml   TVM=47  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 299, b.id, 47 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 299 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 299 SET s.quantity = 47, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 299;
UPDATE batch SET expiry_date = '2029-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 299 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-05-01');

-- RAPIGRO - 500 ML  (product_id=3116, match=exact)
--   sheet Rapigro / 500 ml   TVM=8  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3116, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3116 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3116 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3116;
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3116 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');

-- RESULT - 1 L  (product_id=2119, match=exact)
--   sheet Result / 1 L   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2119, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2119 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2119 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2119;

-- RESULT - 100 ML  (product_id=1315, match=exact)
--   sheet Result / 100 ml   TVM=32  Avalurpet=16
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1315, b.id, 16 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1315 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1315 SET s.quantity = 16, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1315;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1315, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1315 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1315 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1315;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1315 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- RESULT - 250 ML  (product_id=613, match=exact)
--   sheet Result / 250ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 613, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 613 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 613 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 613;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 613 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- RESULT - 500 ML  (product_id=991, match=exact)
--   sheet Result / 500 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 991, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 991 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 991 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 991;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 991 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- RICH GROW - 100 ML  (product_id=2734, match=exact)
--   sheet Rich Grow / 100 ml   TVM=-  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2734, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2734 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2734 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2734;

-- RICH GROW - 250 ML  (product_id=2810, match=exact)
--   sheet Rich Grow / 250 ml   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2810, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2810 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2810 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2810;
UPDATE batch SET expiry_date = '2029-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2810 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-05-01');

-- RICH GROW - 250 ML  (product_id=2810, match=compact-name)
--   sheet Richgrow / 250 ml   TVM=-  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2810, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2810 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2810 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2810;
UPDATE batch SET expiry_date = '2029-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2810 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-03-01');

-- RICH GROW - 500 ML  (product_id=2811, match=exact)
--   sheet Rich Grow / 500 ml   TVM=6  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2811, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2811 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2811 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2811;
UPDATE batch SET expiry_date = '2029-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2811 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-09-01');

-- RONFEN - 1 LTR  (product_id=3777, match=exact)
--   sheet Ronfen / 1 L   TVM=-  Avalurpet=1
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3777, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3777 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3777 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3777;
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3777 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');

-- RONFEN - 100 ML  (product_id=2720, match=exact)
--   sheet Ronfen / 100 ML   TVM=-  Avalurpet=20
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2720, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2720 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2720 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2720;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2720 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- RONFEN - 250 ML  (product_id=2721, match=exact)
--   sheet Ronfen / 250 ML   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2721, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2721 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2721 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2721;
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2721 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');

-- RONFEN - 50 ML  (product_id=2745, match=exact)
--   sheet Ronfen / 50 ml   TVM=-  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2745, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2745 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2745 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2745;
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2745 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');

-- ROUND UP - 1LTR  (product_id=310, match=exact)
--   sheet Round Up / 1 L   TVM=-  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 310, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 310 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 310 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 310;
UPDATE batch SET expiry_date = '2027-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 310 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-06-01');

-- ROUND UP - 500 ML  (product_id=311, match=exact)
--   sheet Round Up / 500 ml   TVM=-  Avalurpet=18
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 311, b.id, 18 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 311 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 311 SET s.quantity = 18, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 311;
UPDATE batch SET expiry_date = '2027-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 311 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-05-01');

-- SAGARIGA - 500 ML  (product_id=1655, match=exact)
--   sheet Sagariga / 500 ml   TVM=4  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1655, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1655 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1655 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1655;
UPDATE batch SET expiry_date = '2029-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1655 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-01-01');

-- SAI POWER PLUS - 100 ML  (product_id=3360, match=alias)
--   sheet Sai Power / 100 ml   TVM=14  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3360, b.id, 14 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3360 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3360 SET s.quantity = 14, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3360;
UPDATE batch SET expiry_date = '2027-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3360 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-05-01');

-- SETT CORTEVA - 200 ML  (product_id=3816, match=packing+tokens)
--   sheet Sett / 200 ml   TVM=50  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3816, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3816 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3816 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3816;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3816, b.id, 50 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3816 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3816 SET s.quantity = 50, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3816;
UPDATE batch SET expiry_date = '2029-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3816 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-10-01');

-- SHINWA - 40 ML  (product_id=2507, match=exact)
--   sheet Shinwa / 40 ml   TVM=1  Avalurpet=3
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2507, b.id, 3 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2507 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2507 SET s.quantity = 3, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2507;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2507, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2507 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2507 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2507;
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2507 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');

-- SHINWA - 80 ML  (product_id=1970, match=exact)
--   sheet Shinwa / 80 ml   TVM=12  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1970, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1970 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1970 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1970;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1970, b.id, 12 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1970 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1970 SET s.quantity = 12, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1970;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1970 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- SHUKRA - 100MLS  (product_id=326, match=exact)
--   sheet Shukra / 100 ml   TVM=9  Avalurpet=34
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 326, b.id, 34 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 326 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 326 SET s.quantity = 34, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 326;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 326, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 326 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 326 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 326;
UPDATE batch SET expiry_date = '2029-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 326 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-04-01');

-- SHUKRA - 250MLS  (product_id=327, match=exact)
--   sheet Shukra / 250 ml   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 327, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 327 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 327 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 327;
UPDATE batch SET expiry_date = '2029-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 327 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-04-01');

-- SHUKRA - 500 ML  (product_id=2807, match=exact)
--   sheet Shukra / 500 ml   TVM=13  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2807, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2807 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2807 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2807;
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2807 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');

-- SIKOSA - 500 ML  (product_id=2617, match=exact)
--   sheet Sikosa / 500 ml   TVM=-  Avalurpet=7
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2617, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2617 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2617 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2617;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2617 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- SIMODIS - 48 ML  (product_id=3827, match=exact)
--   sheet Simodis / 48 ml   TVM=33  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3827, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3827 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3827 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3827;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3827, b.id, 33 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3827 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3827 SET s.quantity = 33, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3827;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3827 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- SIMODIS - 80 ML  (product_id=2538, match=exact)
--   sheet Simodis / 80 ml   TVM=25  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2538, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2538 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2538 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2538;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2538, b.id, 25 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2538 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2538 SET s.quantity = 25, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2538;
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2538 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');

-- SPEED FIPRONI IMIDA - 40 GMS  (product_id=3193, match=packing+tokens)
--   sheet Speed / 40 Gm   TVM=-  Avalurpet=20
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3193, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3193 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3193 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3193;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3193 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- SUGAR MOVER - 200 ML  (product_id=3817, match=exact)
--   sheet Sugar Mover / 200 ml   TVM=-  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3817, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3817 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3817 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3817;
UPDATE batch SET expiry_date = '2029-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3817 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-10-01');

-- SUMI MAX - 10 ML  (product_id=1536, match=exact)
--   sheet Sumi max / 10 ml   TVM=74  Avalurpet=24
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1536, b.id, 24 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1536 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1536 SET s.quantity = 24, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1536;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1536, b.id, 74 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1536 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1536 SET s.quantity = 74, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1536;
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1536 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');

-- SUPER BOOST - 10 ML  (product_id=3086, match=exact)
--   sheet Super Boost / 10 ml   TVM=-  Avalurpet=20
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3086, b.id, 20 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3086 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3086 SET s.quantity = 20, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3086;

-- SUPER RACER - 300 ML  (product_id=2074, match=exact)
--   sheet Super Racer / 300 ml   TVM=6  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2074, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2074 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2074 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2074;
UPDATE batch SET expiry_date = '2027-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2074 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-03-01');

-- SURFAFOUR - 100 ML  (product_id=2791, match=exact)
--   sheet Surfafour / 100 ml   TVM=10  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2791, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2791 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2791 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2791;

-- TARGA SUPER - 100 ML  (product_id=2980, match=exact)
--   sheet Targa Super / 100 ml   TVM=-  Avalurpet=10
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2980, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2980 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2980 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2980;
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2980 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');

-- TERMINATOR - 100 ML  (product_id=2619, match=exact)
--   sheet Terminator / 100 ml   TVM=36  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2619, b.id, 36 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2619 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2619 SET s.quantity = 36, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2619;
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2619 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');

-- TERMINATOR - 250 ML  (product_id=2970, match=exact)
--   sheet Terminator / 250 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2970, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2970 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2970 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2970;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2970 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- TERMINATOR - 50 ML  (product_id=2620, match=exact)
--   sheet Terminator / 50 ml   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2620, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2620 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2620 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2620;
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2620 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');

-- TILT - 100MLS  (product_id=345, match=exact)
--   sheet Tilt / 100 ml   TVM=-  Avalurpet=12
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 345, b.id, 12 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 345 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 345 SET s.quantity = 12, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 345;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 345 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- TOBLER - 250 ML  (product_id=2344, match=exact)
--   sheet Tobler / 250 ml   TVM=13  Avalurpet=25
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2344, b.id, 25 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2344 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2344 SET s.quantity = 25, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2344;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2344, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2344 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2344 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2344;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2344 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- TOBLER - 500 ML  (product_id=2576, match=exact)
--   sheet Tobler / 500 ml   TVM=11  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2576, b.id, 11 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2576 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2576 SET s.quantity = 11, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2576;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2576 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- TOUCHSTONE - 100 GMS  (product_id=1731, match=compact-name)
--   sheet Touch Stone / 100 Gms   TVM=-  Avalurpet=52
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1731, b.id, 52 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1731 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1731 SET s.quantity = 52, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1731;
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1731 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');

-- TOUCHSTONE - 250 GMS  (product_id=2690, match=compact-name)
--   sheet Touch Stone / 250 Gms   TVM=-  Avalurpet=69
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 2690, b.id, 69 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2690 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2690 SET s.quantity = 69, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 2690;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2690 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- TRANCE - 100 ML  (product_id=3775, match=exact)
--   sheet Trance / 100 ml   TVM=33  Avalurpet=9
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3775, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3775 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3775 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3775;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3775, b.id, 33 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3775 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3775 SET s.quantity = 33, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3775;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3775 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- TRANCE - 220 ML  (product_id=3811, match=exact)
--   sheet Trance / 220 ml   TVM=15  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3811, b.id, 15 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3811 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3811 SET s.quantity = 15, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3811;
UPDATE batch SET expiry_date = '2028-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3811 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-08-01');

-- TRANSFORM - 75 ML  (product_id=3829, match=exact)
--   sheet Transform / 75 ml   TVM=13  Avalurpet=5
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3829, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3829 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3829 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3829;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3829, b.id, 13 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3829 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3829 SET s.quantity = 13, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3829;
UPDATE batch SET expiry_date = '2027-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3829 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-05-01');

-- UNIQUAT - 1LTR  (product_id=357, match=exact)
--   sheet Uniquat / 1 L   TVM=-  Avalurpet=32
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 357, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 357 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 357 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 357;
UPDATE batch SET expiry_date = '2029-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 357 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-05-01');

-- VALAGRO MC SET - 1 LITR  (product_id=2836, match=packing+tokens)
--   sheet Mc Set / 1 L   TVM=7  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2836, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2836 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2836 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2836;

-- VALAGRO MC SET - 250 ML  (product_id=3233, match=packing+tokens)
--   sheet Mc Set / 250 ml   TVM=19  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3233, b.id, 19 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3233 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3233 SET s.quantity = 19, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3233;
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3233 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');

-- VALTRUVA - 100 ML  (product_id=3875, match=exact)
--   sheet Valtruva / 100 ml   TVM=24  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3875, b.id, 24 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3875 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3875 SET s.quantity = 24, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3875;
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3875 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');

-- VALTRUVA - 220 ML  (product_id=3852, match=exact)
--   sheet Valtruva / 220 ml   TVM=10  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3852, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3852 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3852 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3852;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3852 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- VAM GOLD - 125 GMS  (product_id=2973, match=exact)
--   sheet Vam Gold / 125 gms   TVM=1  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2973, b.id, 1 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2973 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2973 SET s.quantity = 1, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2973;
UPDATE batch SET expiry_date = '2026-11-11', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2973 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-11');

-- VAM GOLD - 65 GMS  (product_id=3023, match=exact)
--   sheet Vam Gold / 65 Gms   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3023, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3023 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3023 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3023;
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3023 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');

-- VAM GOLD GR - 4 KGS  (product_id=3448, match=packing+tokens)
--   sheet Vam Gold / 4 Kg   TVM=0  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3448, b.id, 0 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3448 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3448 SET s.quantity = 0, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3448;

-- VELZO - 500 GMS  (product_id=3632, match=exact)
--   sheet Velzo / 500 gm   TVM=5  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3632, b.id, 5 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3632 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3632 SET s.quantity = 5, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3632;
UPDATE batch SET expiry_date = '2026-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3632 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-08-01');

-- VIAGRO GOLD - 100 ML  (product_id=3046, match=exact)
--   sheet Viagro Gold / 100 ml   TVM=8  Avalurpet=6
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3046, b.id, 6 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3046 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3046 SET s.quantity = 6, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3046;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3046, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3046 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3046 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3046;
UPDATE batch SET expiry_date = '2030-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3046 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2030-06-01');

-- VIAGRO GOLD - 250 ML  (product_id=3327, match=exact)
--   sheet Viagro Gold / 250 ml   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3327, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3327 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3327 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3327;

-- VIAGRO GOLD - 50 ML  (product_id=3326, match=exact)
--   sheet Viagro Gold / 50 ml   TVM=33  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3326, b.id, 33 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3326 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3326 SET s.quantity = 33, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3326;
UPDATE batch SET expiry_date = '1931-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3326 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '1931-02-01');

-- VIPUL BOOST - 100 ML  (product_id=881, match=packing+tokens)
--   sheet Vipul / 100 ml   TVM=29  Avalurpet=32
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 881, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 881 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 881 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 881;
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 881, b.id, 29 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 881 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 881 SET s.quantity = 29, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 881;
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 881 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');

-- VIPUL BOOST - 100 ML  (product_id=881, match=packing+tokens)
--   sheet Boost / 100 ml   TVM=8  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 881, b.id, 8 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 881 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 881 SET s.quantity = 8, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 881;
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 881 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');

-- VITAGOLD - 50 GMS  (product_id=2072, match=compact-name)
--   sheet Vita Gold / 50 Gm   TVM=32  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2072, b.id, 32 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2072 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2072 SET s.quantity = 32, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2072;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2072 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- WARRIER - 100 ML  (product_id=1687, match=exact)
--   sheet Warrier / 100 ml   TVM=37  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 1687, b.id, 37 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1687 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1687 SET s.quantity = 37, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 1687;
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1687 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');

-- WELGROW - 250 ML  (product_id=3797, match=exact)
--   sheet Welgrow / 250 ml   TVM=4  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3797, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3797 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3797 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3797;
UPDATE batch SET expiry_date = '2029-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3797 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-06-01');

-- YAMRAZ - 100 ML  (product_id=3876, match=exact)
--   sheet Yamraz / 100 ml   TVM=15  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3876, b.id, 15 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3876 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3876 SET s.quantity = 15, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3876;
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3876 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');

-- YARA VITA SENIPHOS - 500 ML  (product_id=3217, match=packing+tokens)
--   sheet Yara Vita / 500 ml   TVM=9  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3217, b.id, 9 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3217 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3217 SET s.quantity = 9, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3217;

-- YES BOSS BLACK MAGIC - 1 LTR  (product_id=3370, match=packing+tokens)
--   sheet Black magic / 1 L   TVM=-  Avalurpet=4
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 3370, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3370 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3370 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 3370;
UPDATE batch SET expiry_date = '2025-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3370 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2025-10-01');

-- YES BOSS BLACK MAGIC - 100 ML  (product_id=1835, match=packing+tokens)
--   sheet Black magic / 100 ml   TVM=-  Avalurpet=36
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 1, 1835, b.id, 36 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 1835 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 1 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 1835 SET s.quantity = 36, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 1 AND s.product_id = 1835;
UPDATE batch SET expiry_date = '2029-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1835 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-07-01');

-- YUNICO FLOW - 150  ML  (product_id=3125, match=packing+tokens)
--   sheet Yunico / 150 ml   TVM=4  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3125, b.id, 4 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3125 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3125 SET s.quantity = 4, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3125;
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3125 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');

-- YUNICO FLOW - 30 ML  (product_id=2916, match=packing+tokens)
--   sheet Yunico / 30 ml   TVM=10  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 2916, b.id, 10 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 2916 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 2916 SET s.quantity = 10, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 2916;

-- ZIPPY GOLD - 100 ML  (product_id=3595, match=exact)
--   sheet Zippy Gold / 100 ml   TVM=7  Avalurpet=-
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity) SELECT 1, 2, 3595, b.id, 7 FROM batch b WHERE b.organization_id = 1 AND b.product_id = 3595 AND b.batch_no = 'STOCK-ON-HAND' AND NOT EXISTS (SELECT 1 FROM stock s WHERE s.branch_id = 2 AND s.batch_id = b.id);
UPDATE stock s JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND' AND b.product_id = 3595 SET s.quantity = 7, s.updated_at = NOW() WHERE s.organization_id = 1 AND s.branch_id = 2 AND s.product_id = 3595;
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3595 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

-- ---------------------------------------------------------------------------
-- Unmatched sheet rows (not applied). Add aliases or create the packing in product.
-- ---------------------------------------------------------------------------

-- Bison / 500 ml   TVM=11  Avalurpet=-   (unmatched)
-- Bumper / 1 L   TVM=10  Avalurpet=-   (unmatched)
-- Cap X / 250 Gm   TVM=-  Avalurpet=8   (unmatched)
-- Herbex / 150 ml   TVM=-  Avalurpet=1   (unmatched)
-- Herbex / 300 ml   TVM=-  Avalurpet=2   (unmatched)
-- Hurrican Plus / 250 ml   TVM=-  Avalurpet=13   (unmatched)
-- Hurrican Plus / 500 ml   TVM=-  Avalurpet=15   (unmatched)
-- Kantrol Plus / 250 ml   TVM=0  Avalurpet=-   (unmatched)
-- Kantrol Plus / 500 ml   TVM=0  Avalurpet=-   (unmatched)
-- Kicker Plus / 500 ml   TVM=-  Avalurpet=13   (unmatched)
-- Kicker Plus / 1 L   TVM=-  Avalurpet=3   (unmatched)
-- Kingzyme GR / 5 Kg   TVM=0  Avalurpet=-   (unmatched)
-- Onduty Plus / 50 ml   TVM=-  Avalurpet=53   (unmatched)
-- Onduty Plus / 250 ml   TVM=-  Avalurpet=12   (unmatched)
-- Pendikem Xtra / 700 mml   TVM=1  Avalurpet=-   (unmatched)
-- Preced / 250 ml   TVM=-  Avalurpet=3   (unmatched)
-- Purge / 200 ml   TVM=-  Avalurpet=1   (unmatched)
-- Pyrakil / 100 ml   TVM=50  Avalurpet=4   (unmatched)
-- Pyrakil / 250 ml   TVM=68  Avalurpet=-   (unmatched)
-- Pyrakil / 500 ml   TVM=2  Avalurpet=-   (unmatched)
-- Regen / 30 ml   TVM=-  Avalurpet=2   (unmatched)
-- Samta-Magical / 500 ml   TVM=-  Avalurpet=35   (unmatched)
-- Spic Cytoz / 250 ml   TVM=-  Avalurpet=47   (unmatched)
-- Spic Cytoz / 500 ml   TVM=-  Avalurpet=20   (unmatched)
-- Surplus / 300 Gm   TVM=-  Avalurpet=6   (unmatched)
-- Teja EW / 100 ml   TVM=15  Avalurpet=-   (unmatched)
-- Tepronil / 1 Kg   TVM=0  Avalurpet=-   (unmatched)
-- Vajra 19:19:19 / 250 ml   TVM=-  Avalurpet=32   (unmatched)
-- Vasudha / 1 Kg   TVM=0  Avalurpet=-   (unmatched)
-- Vasudha / 3 Kg   TVM=0  Avalurpet=-   (unmatched)
-- Viswajith / 100 Gms   TVM=50  Avalurpet=5   (unmatched)
-- Viswajith / 250 Gms   TVM=0  Avalurpet=-   (unmatched)
-- Weed Blaze / 250 ml   TVM=14  Avalurpet=22   (unmatched)
-- Weed Blaze / 400 ml   TVM=0  Avalurpet=8   (unmatched)
-- Weed Blaze / 1 L   TVM=7  Avalurpet=-   (unmatched)
-- weed Super / 500 ml   TVM=-  Avalurpet=41   (unmatched)
-- weed Super / 1 L   TVM=-  Avalurpet=9   (unmatched)
-- Weedrop / 1400 ml   TVM=-  Avalurpet=15   (unmatched)
-- Zoomin / 500 ml   TVM=-  Avalurpet=3   (unmatched)
-- Moksha / 250 ml   TVM=39  Avalurpet=-   (unmatched)
-- Merivon / 40 ml   TVM=6  Avalurpet=-   (unmatched)
-- Merivon / 80 ml   TVM=3  Avalurpet=-   (unmatched)
-- Indoolizer / 250 ml   TVM=17  Avalurpet=-   (unmatched)
-- Regen / 30 ml   TVM=12  Avalurpet=-   (unmatched)
-- Sirius / 12 Gm   TVM=48  Avalurpet=-   (unmatched)
-- Steller On / 365 Gm   TVM=29  Avalurpet=-   (unmatched)
-- Pendagon / 250 ml   TVM=35  Avalurpet=-   (unmatched)
-- Pendagon / 500 ml   TVM=9  Avalurpet=-   (unmatched)
-- Nemagen / 100 ml   TVM=31  Avalurpet=-   (unmatched)
-- Proclaim Xtra / 100 ml   TVM=9  Avalurpet=-   (unmatched)
-- Grow K+ / 100 ml   TVM=22  Avalurpet=-   (unmatched)
-- Lojas / 250 ml   TVM=7  Avalurpet=-   (unmatched)
-- Valum flexi / 100 ml   TVM=38  Avalurpet=-   (unmatched)
-- Avuuntis / 100 ml   TVM=10  Avalurpet=-   (unmatched)
-- Kasu B / 100 ml   TVM=14  Avalurpet=-   (unmatched)
-- Nutrax / 500 ml   TVM=4  Avalurpet=-   (unmatched)

-- Applied AVL rows: 131  qty 2791
-- Applied TVM rows: 153  qty 3914
-- Unmatched counted rows: 56

