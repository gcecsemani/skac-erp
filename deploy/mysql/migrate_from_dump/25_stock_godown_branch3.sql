-- Godown physical stock from Stock Master 16-09-2026.xlsx (Sheet1)
-- Products matched against Dump20260916.sql
-- Review before running. Safe to re-run (upserts branch 3 STOCK-ON-HAND only).
--
-- Target: organization_id = 1, branch_id = 3
-- Branch 3 must already exist. This script does not create the branch
-- and does not change stock on branch 1 (AVL) or branch 2 (TVM).
--
-- Skip rules: blank Godown is skipped. 0 is treated as counted (stock set to 0).
-- Blank product names inherit the previous row (merged packing variants).
-- Counted qty is stored on a STOCK-ON-HAND batch looked up/created by product_id.
--
-- Sheet rows: 518  skipped (no qty): 255
-- Matched with qty: 236  unique products: 227  unmatched: 27
-- Duplicate sheet→product mappings (last row wins): 9
--
--   mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/25_stock_godown_branch3.sql

USE skac_new;
SET NAMES utf8mb4;

START TRANSACTION;

-- ---------------------------------------------------------------------------
-- STEP 0) STOCK-ON-HAND batch per counted product
-- ---------------------------------------------------------------------------
INSERT INTO batch (organization_id, product_id, batch_no, expiry_date, purchase_price)
SELECT p.organization_id, p.id, 'STOCK-ON-HAND', NULL, COALESCE(p.purchase_price, 0)
FROM product p
WHERE p.organization_id = 1 AND p.id IN (76, 122, 158, 159, 224, 227, 320, 333, 345, 346, 357, 447, 518, 523, 527, 535, 542, 565, 568, 573, 579, 613, 630, 729, 747, 795, 803, 804, 822, 834, 991, 1018, 1019, 1020, 1024, 1067, 1081, 1098, 1112, 1153, 1159, 1197, 1283, 1294, 1315, 1347, 1386, 1423, 1502, 1532, 1557, 1576, 1595, 1655, 1669, 1693, 1708, 1724, 1725, 1783, 1785, 1834, 1945, 2119, 2135, 2179, 2218, 2243, 2270, 2301, 2343, 2344, 2457, 2458, 2470, 2517, 2551, 2576, 2619, 2620, 2623, 2636, 2658, 2697, 2700, 2701, 2714, 2720, 2731, 2734, 2745, 2747, 2748, 2749, 2778, 2791, 2798, 2806, 2810, 2811, 2834, 2842, 2960, 2961, 2962, 2970, 2973, 2974, 2995, 2996, 2997, 2998, 3004, 3016, 3023, 3024, 3025, 3046, 3053, 3061, 3120, 3129, 3133, 3152, 3153, 3161, 3172, 3176, 3177, 3181, 3197, 3209, 3216, 3237, 3238, 3241, 3246, 3247, 3248, 3268, 3274, 3283, 3312, 3313, 3316, 3317, 3325, 3326, 3327, 3334, 3371, 3393, 3394, 3405, 3412, 3416, 3424, 3428, 3430, 3431, 3435, 3448, 3449, 3463, 3464, 3493, 3494, 3495, 3499, 3505, 3509, 3517, 3519, 3547, 3552, 3553, 3554, 3555, 3556, 3557, 3563, 3566, 3567, 3569, 3572, 3573, 3595, 3596, 3598, 3602, 3604, 3606, 3628, 3636, 3643, 3653, 3665, 3672, 3681, 3683, 3717, 3726, 3728, 3746, 3758, 3760, 3777, 3781, 3782, 3783, 3790, 3791, 3805, 3828, 3847, 3848, 3849, 3850, 3853, 3856, 3857, 3858, 3876, 3877, 3880, 3886, 3887)
  AND NOT EXISTS (
    SELECT 1 FROM batch b
    WHERE b.organization_id = p.organization_id
      AND b.product_id = p.id
      AND b.batch_no = 'STOCK-ON-HAND'
  );

-- ---------------------------------------------------------------------------
-- STEP 1) Counted Godown qty (insert missing rows, then set quantities)
-- ---------------------------------------------------------------------------
INSERT INTO stock (organization_id, branch_id, product_id, batch_id, quantity)
SELECT x.organization_id, x.branch_id, x.product_id, b.id, x.qty
FROM (
  SELECT 1 AS organization_id, 3 AS branch_id, 3880 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- 19:19:19 VAJRA - 100 ML  sheet Vajra 19:19:19 / 100 ml  qty=100  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3237 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- ADORA - 100 ML  sheet Adora / 100 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3238 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- ADORA - 200 ML  sheet Adora / 200 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3129 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- AGRO BUMPER - 100 ML  sheet Bumper / 100 ml  qty=200  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3726 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- AGRO BUMPER - 250 ML  sheet Bumper / 250 ml  qty=120  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3858 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- AGRO SATVA PLUS - 250 ML  sheet Samta Agro Satva / 250 ml  qty=120  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 834 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- AGZACT - 25 GMS  sheet Agzact / 25 Gms  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3209 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- AKEMI - 250 ML  sheet Akemi / 250 Ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 523 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- ALPHASAKTHI - 250 ML  sheet Alphasakthi / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1532 AS product_id, CAST(153 AS DECIMAL(14,3)) AS qty  -- ANTRACOL - 250 GMS  sheet Antracol / 250 Gm  qty=153  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3758 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- AQUACAL - 500 ML  sheet Aquacol / 500 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3636 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- ARIES BORON - 250 GMS  sheet Aries Boron / 250 Gm  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1024 AS product_id, CAST(12 AS DECIMAL(14,3)) AS qty  -- ASBIYAN - 250 ML  sheet Asbiyan / 250 ml  qty=12  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1595 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- AZADI - 250 ML  sheet Azadi / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2135 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- AZADI - 500 ML  sheet Azadi / 500 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3246 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BANCO - 100 ML  sheet Banco / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3247 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- BANCO - 250 ML  sheet Banco / 250 Ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3248 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BANCO - 500 ML  sheet Banco / 500 ML  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2551 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- BARRIX CONTROL - 20 GMS  sheet Barrix Control / 20 Gm  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2457 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BENZA PLUS - 100 ML  sheet Benza Plus / 100 Ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2458 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BENZA PLUS - 250 MO  sheet Benza Plus / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 795 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BENZO CARE - 250 ML  sheet Benzocare / 250 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2517 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- BENZO CARE - 500 ML  sheet Benzocare / 500 ML  qty=20  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3886 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- BESTIE - 1 L  sheet Bestie / 1 L  qty=30  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3887 AS product_id, CAST(6 AS DECIMAL(14,3)) AS qty  -- BESTIE - 5 LTR  sheet Bestie / 5 L  qty=6  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3557 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- BESTIE - 500 ML  sheet Bestie / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3555 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BESTMAN - 100 ML  sheet Best Man / 100 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3556 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- BESTMAN - 250 ML  sheet Best Man / 250 ml  qty=30  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3554 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- BESTMAN - 50 ML  sheet Best Man / 50 ml  qty=160  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3161 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- BIO WIN - 1 KGS  sheet Bio Win / 1 Kg  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3569 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- BISON - 250 ML  sheet Bison / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3416 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BLAID EW - 600 ML  sheet Blaid EW / 600 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 803 AS product_id, CAST(300 AS DECIMAL(14,3)) AS qty  -- BLOOM FLOWER - 100 ML  sheet Bloomflower / 100 ml  qty=300  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 804 AS product_id, CAST(39 AS DECIMAL(14,3)) AS qty  -- BLOOM FLOWER - 250 ML  sheet Bloomflower / 250 ml  qty=39  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1153 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BLOOM FLOWER - 500 ML  sheet Bloomflower / 500 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 76 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BRAND - 20 ML  sheet Brand / 20 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3412 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- BRAND GR - 1 KGS  sheet Brand Gr / 1 Kg  qty=60  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1020 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- BULLET - 1 L  sheet Bullet / 1 L  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1576 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- BULLET - 100 ML  sheet Bullet / 100 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1018 AS product_id, CAST(63 AS DECIMAL(14,3)) AS qty  -- BULLET - 250 ML  sheet Bullet / 250 ml  qty=63  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1019 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BULLET - 500 ML  sheet Bullet / 500 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3563 AS product_id, CAST(90 AS DECIMAL(14,3)) AS qty  -- C HAWK - 250 GMS  sheet C-Hawk / 250 Gm  qty=90  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 747 AS product_id, CAST(363 AS DECIMAL(14,3)) AS qty  -- CAP-X-SP - 100 GMS  sheet Cap X / 100 Gm  qty=363  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1557 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- CHEETAH - 1 L  sheet Cheeta / 1 L  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3016 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- CITIGEN - 30 ML  sheet Citigen / 30 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 573 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- COMBI PLUS - 100 GMS  sheet Combi Plus / 100 Gm  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1067 AS product_id, CAST(54 AS DECIMAL(14,3)) AS qty  -- COMBI PLUS - 250 GMS  sheet Combi Plus / 250 Gm  qty=54  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1502 AS product_id, CAST(18 AS DECIMAL(14,3)) AS qty  -- COMBI PLUS - 500 GMS  sheet Combi Plus / 500 Gm  qty=18  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3849 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- CONFIDENCE 555 - 50 ML  sheet Confidence 555 / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3828 AS product_id, CAST(320 AS DECIMAL(14,3)) AS qty  -- DECLARE - 25 GMS  sheet Declare / 25 Gms  qty=320  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1783 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 10 ML  sheet Dry Up Gold / 10 ml  qty=100  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1724 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 100 ML  sheet Dry Up Gold / 100 ml  qty=50  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2243 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 200 ML  sheet Dry Up Gold / 200 ml  qty=60  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1725 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 50 ML  sheet Dry Up Gold / 50 ml  qty=160  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3152 AS product_id, CAST(8 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 500 ML  sheet Dry Up Gold / 500 ml  qty=8  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3850 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- DURSBAN - 100 ML  sheet Dursban / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3517 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- DURSBAN - 250 ML  sheet Dursban / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2218 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- EM POWER LIQ - 250 ML  sheet Em Power / 250 ML  qty=80  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 122 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- ENCOUNTER - 50MLS  sheet Encounter / 50 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3430 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- ETCIO STAR - 250 ML  sheet Etcio Star / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3431 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- ETCIO STAR - 500 ML  sheet Etcio Star / 500 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3672 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FAITA - 160 ML  sheet Faita / 160 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3760 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FAITA - 40 ML  sheet Faita / 40 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3717 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- FAITA - 80 ML  sheet Faita / 80 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3241 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FENNY - 1 LTR  sheet Fenny / 1 L  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2960 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FENNY - 100 ML  sheet Fenny / 100 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2961 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- FENNY - 250 ML  sheet Fenny / 250 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3172 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FENNY - 500 ML  sheet Fenny / 500 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2179 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- FERIO - 1L  sheet Ferio / 1 L  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1159 AS product_id, CAST(19 AS DECIMAL(14,3)) AS qty  -- FERTICEM - 1 LITR  sheet Ferticem / 1 L  qty=19  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3509 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- GALAXY EXPERT - 100 ML  sheet Galaxy Expert 0.001 / 100 ml  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 158 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- GUBERA - 100MLS  sheet Gubera / 100 ml  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 159 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- GUBERA - 250MLS  sheet Gubera / 250 ml  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 630 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- GUBERA - 500 ML  sheet Gubera / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 565 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- GURU - 100 ML  sheet Guru / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1347 AS product_id, CAST(32 AS DECIMAL(14,3)) AS qty  -- GURU - 250 ML  sheet Guru / 250 ml  qty=32  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3805 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- HOLD - 40 GMS  sheet Hold / 40 Gm  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 822 AS product_id, CAST(46 AS DECIMAL(14,3)) AS qty  -- HUMACH - 1 KGS  sheet Humach / 1 kg  qty=46  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3177 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- HUMI RICH - 1 LTR  sheet Humirich F / 1 L  qty=10  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3176 AS product_id, CAST(15 AS DECIMAL(14,3)) AS qty  -- HUMI RICH - 500 ML  sheet Humirich F / 500 ml  qty=15  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 527 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- HUMIRICH N - 250 ML  sheet Humirich N / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1785 AS product_id, CAST(22 AS DECIMAL(14,3)) AS qty  -- HURRICANE PLUS - 250 ML  sheet Hurrican Plus / 250 ml  qty=22  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2842 AS product_id, CAST(22 AS DECIMAL(14,3)) AS qty  -- IKEDA - 250 ML  sheet Ikeda / 250 ml  qty=22  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2995 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 1 LITR  sheet Jamindar / 1 L  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2636 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 100 ML  sheet Jamindar / 100 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2623 AS product_id, CAST(280 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 250 ML  sheet Jamindar / 250 ml  qty=280  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2974 AS product_id, CAST(140 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 500 ML  sheet Jamindar / 500 ml  qty=140  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3519 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- JIVORA - 100 GMS  sheet Jivora / 100 Gm  qty=30  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3312 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- KANTROL PLUSS - 100 ML  sheet Kantrol Plus / 100 ml  qty=0  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3313 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- KANTROL PLUSS - 250 ML  sheet Kantrol Plus / 250 ml  qty=160  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3598 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- KANTROL PLUSS - 500 ML  sheet Kantrol Plus / 500 ml  qty=80  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3371 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- KAVACHAM - 100 GMS  sheet Kavacham / 100 Gms  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3449 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- KAVACHAM - 250 GMS  sheet Kavacham / 250 Gms  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3499 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- KAVACHAM - 500 GMS  sheet Kavacham / 500 Gms  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 579 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- KEMLOX - 100 ML  sheet Kemlox / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 568 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- KEMLOX - 250 ML  sheet Kemlox / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1708 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- KEMSTAR - 100 GMS  sheet Kemstar / 100 Gm  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1081 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- KEMSTAR - 5 GMS  sheet Kemstar / 5 Gm  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3133 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- KEMSTAR EASY - 1 LTR  sheet Kemstar Easy / 1 ltr  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2714 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- KEMSTAR EASY - 100 ML  sheet Kemstar Easy / 100 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2697 AS product_id, CAST(16 AS DECIMAL(14,3)) AS qty  -- KING ZYME BUCKET - 5 KGS  sheet Kingzyme GR / 5 Kg  qty=16  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3004 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- LIGER - 100 ML  sheet Liger / 100 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 518 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- LIHOCIN - 100 ML  sheet Lihocin / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3325 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- MAAGRO - 50 ML  sheet Maagro / 50 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3572 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- MACROFERT HD 20:20:20 - 200 GMS  sheet Microfert HD 20:20:20 / 200 Gms  qty=120  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3857 AS product_id, CAST(240 AS DECIMAL(14,3)) AS qty  -- MAGICAL - 250 ML  sheet Samta-Magical / 250 ml  qty=240  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2962 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- MAGICAL - 500 ML  sheet Samta-Magical / 500 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3053 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- MEDISOL OCEANIC - 100 ML  sheet Medisol Oceanic / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3553 AS product_id, CAST(65 AS DECIMAL(14,3)) AS qty  -- MICRO CARE - 120 GMS  sheet Micro Care / 120 Gm  qty=65  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3552 AS product_id, CAST(39 AS DECIMAL(14,3)) AS qty  -- MICRO CARE - 60 GMS  sheet Micro Care / 60 Gm  qty=39  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 224 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- MICROGREEN - 100GMS  sheet Micro Green / 100 Gm  qty=100  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3316 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- MICRORICH - 250 ML  sheet Microrich / 250 ML  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3317 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- MICRORICH - 500 ML  sheet Microrich / 500 ML  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2834 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- MILQUAT - 1L  sheet Milquat / 1 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 227 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- MIRACLE - 100MLS  sheet Miracle / 100 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2270 AS product_id, CAST(37 AS DECIMAL(14,3)) AS qty  -- MITERICH - 250 ML  sheet Miterich / 250 ml  qty=37  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2798 AS product_id, CAST(42 AS DECIMAL(14,3)) AS qty  -- NANO DAP - 500 ML  sheet Iffco nano DAP / 500 ml  qty=42  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1693 AS product_id, CAST(180 AS DECIMAL(14,3)) AS qty  -- NANO UREA - 500 ML  sheet Iffco Nano urea / 500 ml  qty=180  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3216 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- NOVLECT - 250 ML  sheet Novlect / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3728 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- NUTRI WIN - 250 ML  sheet Nutriwin / 250 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3848 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- NUTROZEN - 100 ML  sheet Nutrozen / 100 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2778 AS product_id, CAST(12 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 1 KGS  sheet On A Top / 1 Kg  qty=12  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2747 AS product_id, CAST(300 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 10 GMS  sheet On A Top / 10 Gm  qty=300  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2749 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 100 GMS  sheet On A Top / 100 Gm  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1098 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 250 GMS  sheet On A Top / 250 Gm  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2748 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 50 GMS  sheet On A Top / 50 Gm  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2731 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- OXYCLEAN - 250 ML  sheet Oxyclean / 250 ml  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3268 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 100 ML  sheet Pasidi-6 / 100 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3464 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 250 ML  sheet Pasidi-6 / 250 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3024 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 30 ML  sheet Pasidi-6 / 30 ml  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3025 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 50 ML  sheet Pasidi-6 / 50 ml  qty=150  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1294 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- PATELA - 400 ML  sheet Patela / 400 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3791 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- PENDIKEM CS - 350 ML  sheet Pendikem Xtra / 350 ml  qty=150  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3790 AS product_id, CAST(75 AS DECIMAL(14,3)) AS qty  -- PENDIKEM CS - 700 ML  sheet Pendikem Xtra / 700 mml  qty=75  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3853 AS product_id, CAST(34 AS DECIMAL(14,3)) AS qty  -- PORTION - 100 ML  sheet Portion / 100 ml  qty=34  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1112 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- PORTION - 50 ML  sheet Portion / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3573 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 1 LTR  sheet Sea Diamond / 1 L  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2996 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 100 ML  sheet Sea Diamond / 100 ml  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2997 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 250 ML  sheet Sea Diamond / 250 ml  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2998 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 500 ML  sheet Sea Diamond / 500 ml  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2470 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- PRELUDE PLUS - 250 ML  sheet Prelude Plus / 250 ml  qty=160  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3435 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- PRETI EW - 600 ML  sheet Preti Super / 600 ml  qty=100  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1669 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- PROFEX SUPER - 1 L  sheet Profex Super / 1 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1283 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- PROFEX SUPER - 500 ML  sheet Profex Super / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3393 AS product_id, CAST(47 AS DECIMAL(14,3)) AS qty  -- PROFEX ULTRA - 150 GMS  sheet Profex Ultra / 150 Gm  qty=47  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 447 AS product_id, CAST(800 AS DECIMAL(14,3)) AS qty  -- PROGIBB EASY - 2.5 GMS  sheet Progib Easy / 2.5 Gms  qty=800  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3283 AS product_id, CAST(3 AS DECIMAL(14,3)) AS qty  -- PUTIN - 250 ML  sheet Putin / 250 ml  qty=3  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3394 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- PYRAKILL - 100 ML  sheet Pyrakil / 100 ml  qty=200  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3334 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- PYRAKILL - 250 ML  sheet Pyrakil / 250 ml  qty=120  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3424 AS product_id, CAST(22 AS DECIMAL(14,3)) AS qty  -- QUANTIS - 100 ML  sheet Quantis / 100 ml  qty=22  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1386 AS product_id, CAST(42 AS DECIMAL(14,3)) AS qty  -- QUANTIS - 400 ML  sheet Quantis / 400 ml  qty=42  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3120 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- RASAYAN CHLOR - 500 ML  sheet RashayanChlor / 500 ml  qty=80  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2119 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- RESULT - 1 L  sheet Result / 1 L  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1315 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- RESULT - 100 ML  sheet Result / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 613 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- RESULT - 250 ML  sheet Result / 250ml  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 991 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- RESULT - 500 ML  sheet Result / 500 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2658 AS product_id, CAST(250 AS DECIMAL(14,3)) AS qty  -- RICH BOR - 100 GMS  sheet Rich Boron / 100 Gms  qty=250  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2734 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- RICH GROW - 100 ML  sheet Richgrow / 100 ml  qty=30  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2810 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- RICH GROW - 250 ML  sheet Richgrow / 250 ml  qty=0  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2811 AS product_id, CAST(4 AS DECIMAL(14,3)) AS qty  -- RICH GROW - 500 ML  sheet Richgrow / 500 ml  qty=4  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3505 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- RICH MICRO - 1 LITR  sheet Rich Micro / 1 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3777 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- RONFEN - 1 LTR  sheet Ronfen / 1 L  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2720 AS product_id, CAST(280 AS DECIMAL(14,3)) AS qty  -- RONFEN - 100 ML  sheet Ronfen / 100 ML  qty=280  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2745 AS product_id, CAST(390 AS DECIMAL(14,3)) AS qty  -- RONFEN - 50 ML  sheet Ronfen / 50 ml  qty=390  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3181 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- RONFEN - 500 ML  sheet Ronfen / 500 ML  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1945 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- RUN OUT 71 - 100 GMS  sheet Run Out 71 / 100 Gms  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1655 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- SAGARIGA - 500 ML  sheet Sagariga / 500 ml  qty=160  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3061 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SAMTA 6-0-18 CA MG ZN - 500 ML  sheet Samta-6-0-18 / 500 ml  qty=40  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3856 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- SAMTA K SHINE - 250 ML  sheet Samta K Shine / 250 ML  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 320 AS product_id, CAST(75 AS DECIMAL(14,3)) AS qty  -- SANVEX 50 SP - 250GMS  sheet Sanvex Sp / 250 Gm  qty=75  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 542 AS product_id, CAST(9 AS DECIMAL(14,3)) AS qty  -- SANVEX 50 SP - 500 GMS  sheet Sanvex Sp / 500 Gm  qty=9  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2301 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- SETTI - 100 ML  sheet Setti / 100 ml  qty=150  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3197 AS product_id, CAST(16 AS DECIMAL(14,3)) AS qty  -- SHAKED - 800 ML  sheet Shaked / 800 ml  qty=16  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3783 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- SICKLE - 1 LTR  sheet GSP Sickle / 1 L  qty=10  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3781 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SICKLE - 250 ML  sheet GSP Sickle / 250 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3782 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- SICKLE - 500 ML  sheet GSP Sickle / 500 ML  qty=20  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3746 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- SIPVIN - 100 ML  sheet Sipvin / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3547 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- SLAYER PRO - 50 ML  sheet Slayer Pro / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2806 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SOLOMON - 250 ML  sheet Solomon / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 729 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- SPIC CYTOZYME - 250 ML  sheet Cytozyme / 250 ml  qty=80  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1423 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- SPIC CYTOZYME - 500 ML  sheet Cytozyme + Spic Cytoz / 500 ml + 500 ml  qty=80  match=packing+tokens+alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3847 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SUMI BLUE DIAMOND - 1KGS  sheet Blue Diamond / 1 Kgs  qty=40  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 333 AS product_id, CAST(62 AS DECIMAL(14,3)) AS qty  -- SUMI PREMPT - 100MLS  sheet Sumi Premt / 100 ml  qty=62  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1197 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SUPER RACER - 600 ML  sheet Super Racer / 600 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2791 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- SURFAFOUR - 100 ML  sheet Surfafour / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3566 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- TEJA - 100 ML  sheet Teja EW / 100 ml  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3567 AS product_id, CAST(48 AS DECIMAL(14,3)) AS qty  -- TEJA - 250 ML  sheet Teja EW / 250 ml  qty=48  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3628 AS product_id, CAST(24 AS DECIMAL(14,3)) AS qty  -- TEJA - 500 ML  sheet Teja EW / 500 ml  qty=24  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3274 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- TEMPER - 500 GMS  sheet Temper / 500 Gm  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3405 AS product_id, CAST(90 AS DECIMAL(14,3)) AS qty  -- TEPROANIL - 1 KGS  sheet Tepronil / 1 Kg  qty=90  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2619 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- TERMINATOR - 100 ML  sheet Terminator / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2970 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- TERMINATOR - 250 ML  sheet Terminator / 250 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2620 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- TERMINATOR - 50 ML  sheet Terminator / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3683 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- THUNDER BOLD - 100 ML  sheet ThunderBolt / 100 ml  qty=100  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3681 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- THUNDER BOLD - 500 ML  sheet ThunderBolt / 500 ml  qty=20  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 345 AS product_id, CAST(600 AS DECIMAL(14,3)) AS qty  -- TILT - 100MLS  sheet Tilt / 100 ml  qty=600  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 346 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- TILT - 250MLS  sheet Tilt / 250 Ml  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2343 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- TOBLER - 100 ML  sheet Tobler / 100 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2344 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- TOBLER - 250 ML  sheet Tobler / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2576 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- TOBLER - 500 ML  sheet Tobler / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3493 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- TOPPER 71 - 1 KGS  sheet Topper 71 / 1 Kg  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 357 AS product_id, CAST(70 AS DECIMAL(14,3)) AS qty  -- UNIQUAT - 1LTR  sheet Uniquat / 1 L  qty=70  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3494 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- VALXTRA - 100 ML  sheet Willowwood-Val Xtra / 100 ml  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3495 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- VALXTRA - 250 ML  sheet Willowwood-Val Xtra / 250 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2973 AS product_id, CAST(70 AS DECIMAL(14,3)) AS qty  -- VAM GOLD - 125 GMS  sheet Vam Gold / 125 gms  qty=70  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3023 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- VAM GOLD - 65 GMS  sheet Vam Gold / 65 Gms  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3448 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- VAM GOLD GR - 4 KGS  sheet Vam Gold / 4 Kg  qty=40  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3606 AS product_id, CAST(75 AS DECIMAL(14,3)) AS qty  -- VASUDHAA - 1 KGS  sheet Vasudha / 1 Kg  qty=75  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3463 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- VASUDHAA - 3 KGS  sheet Vasudha / 3 Kg  qty=60  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3665 AS product_id, CAST(5 AS DECIMAL(14,3)) AS qty  -- VESO MAX - 500 ML  sheet Vesomax / 500 ml  qty=5  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3046 AS product_id, CAST(36 AS DECIMAL(14,3)) AS qty  -- VIAGRO GOLD - 100 ML  sheet Viagro Gold / 100 ml  qty=36  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3327 AS product_id, CAST(136 AS DECIMAL(14,3)) AS qty  -- VIAGRO GOLD - 250 ML  sheet Viagro Gold / 250 ml  qty=136  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3326 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- VIAGRO GOLD - 50 ML  sheet Viagro Gold / 50 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 535 AS product_id, CAST(48 AS DECIMAL(14,3)) AS qty  -- VIRAAT - 250 ML  sheet Viraat / 250 ml  qty=48  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3653 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- VIRAAT VALIDA - 100 ML  sheet Viraat / 100 ml  qty=60  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3643 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- VISWAJIT - 100 GMS  sheet Viswajith / 100 Gms  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3602 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- WEALTH - 1 L  sheet Wealth / 1 L  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3604 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- WEALTH - 5 L  sheet Wealth / 5 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3153 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- WEED BLLAZE - 1 LTR  sheet Weed Blaze / 1 L  qty=0  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2701 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- WEED BLLAZE - 250 ML  sheet Weed Blaze / 250 ml  qty=120  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2700 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- WEED BLLAZE - 400 ML  sheet Weed Blaze / 400 ml  qty=20  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3876 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- YAMRAZ - 100 ML  sheet Yamraz / 100 ml  qty=150  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3877 AS product_id, CAST(36 AS DECIMAL(14,3)) AS qty  -- YAMRAZ - 250 ML  sheet Yamraz / 250 ml  qty=36  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1834 AS product_id, CAST(21 AS DECIMAL(14,3)) AS qty  -- YES BOSS BLACK MAGIC - 250 ML  sheet Black magic / 250 ml  qty=21  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3428 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- ZEN SPIC - 100 GMS  sheet Spic Zen / 100 Gm  qty=200  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3595 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- ZIPPY GOLD - 100 ML  sheet Zippy Gold / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3596 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- ZIPPY GOLD - 250 ML  sheet Zippy Gold / 250 ml  qty=40  match=exact
) x
JOIN batch b ON b.organization_id = x.organization_id
          AND b.product_id = x.product_id
          AND b.batch_no = 'STOCK-ON-HAND'
WHERE NOT EXISTS (
  SELECT 1 FROM stock s
  WHERE s.branch_id = x.branch_id AND s.batch_id = b.id
);

UPDATE stock s
JOIN batch b ON b.id = s.batch_id AND b.batch_no = 'STOCK-ON-HAND'
JOIN (
  SELECT 1 AS organization_id, 3 AS branch_id, 3880 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- 19:19:19 VAJRA - 100 ML  sheet Vajra 19:19:19 / 100 ml  qty=100  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3237 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- ADORA - 100 ML  sheet Adora / 100 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3238 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- ADORA - 200 ML  sheet Adora / 200 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3129 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- AGRO BUMPER - 100 ML  sheet Bumper / 100 ml  qty=200  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3726 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- AGRO BUMPER - 250 ML  sheet Bumper / 250 ml  qty=120  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3858 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- AGRO SATVA PLUS - 250 ML  sheet Samta Agro Satva / 250 ml  qty=120  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 834 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- AGZACT - 25 GMS  sheet Agzact / 25 Gms  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3209 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- AKEMI - 250 ML  sheet Akemi / 250 Ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 523 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- ALPHASAKTHI - 250 ML  sheet Alphasakthi / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1532 AS product_id, CAST(153 AS DECIMAL(14,3)) AS qty  -- ANTRACOL - 250 GMS  sheet Antracol / 250 Gm  qty=153  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3758 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- AQUACAL - 500 ML  sheet Aquacol / 500 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3636 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- ARIES BORON - 250 GMS  sheet Aries Boron / 250 Gm  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1024 AS product_id, CAST(12 AS DECIMAL(14,3)) AS qty  -- ASBIYAN - 250 ML  sheet Asbiyan / 250 ml  qty=12  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1595 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- AZADI - 250 ML  sheet Azadi / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2135 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- AZADI - 500 ML  sheet Azadi / 500 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3246 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BANCO - 100 ML  sheet Banco / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3247 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- BANCO - 250 ML  sheet Banco / 250 Ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3248 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BANCO - 500 ML  sheet Banco / 500 ML  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2551 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- BARRIX CONTROL - 20 GMS  sheet Barrix Control / 20 Gm  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2457 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BENZA PLUS - 100 ML  sheet Benza Plus / 100 Ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2458 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BENZA PLUS - 250 MO  sheet Benza Plus / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 795 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BENZO CARE - 250 ML  sheet Benzocare / 250 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2517 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- BENZO CARE - 500 ML  sheet Benzocare / 500 ML  qty=20  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3886 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- BESTIE - 1 L  sheet Bestie / 1 L  qty=30  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3887 AS product_id, CAST(6 AS DECIMAL(14,3)) AS qty  -- BESTIE - 5 LTR  sheet Bestie / 5 L  qty=6  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3557 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- BESTIE - 500 ML  sheet Bestie / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3555 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BESTMAN - 100 ML  sheet Best Man / 100 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3556 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- BESTMAN - 250 ML  sheet Best Man / 250 ml  qty=30  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3554 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- BESTMAN - 50 ML  sheet Best Man / 50 ml  qty=160  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3161 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- BIO WIN - 1 KGS  sheet Bio Win / 1 Kg  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3569 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- BISON - 250 ML  sheet Bison / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3416 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BLAID EW - 600 ML  sheet Blaid EW / 600 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 803 AS product_id, CAST(300 AS DECIMAL(14,3)) AS qty  -- BLOOM FLOWER - 100 ML  sheet Bloomflower / 100 ml  qty=300  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 804 AS product_id, CAST(39 AS DECIMAL(14,3)) AS qty  -- BLOOM FLOWER - 250 ML  sheet Bloomflower / 250 ml  qty=39  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1153 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BLOOM FLOWER - 500 ML  sheet Bloomflower / 500 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 76 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- BRAND - 20 ML  sheet Brand / 20 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3412 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- BRAND GR - 1 KGS  sheet Brand Gr / 1 Kg  qty=60  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1020 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- BULLET - 1 L  sheet Bullet / 1 L  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1576 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- BULLET - 100 ML  sheet Bullet / 100 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1018 AS product_id, CAST(63 AS DECIMAL(14,3)) AS qty  -- BULLET - 250 ML  sheet Bullet / 250 ml  qty=63  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1019 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- BULLET - 500 ML  sheet Bullet / 500 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3563 AS product_id, CAST(90 AS DECIMAL(14,3)) AS qty  -- C HAWK - 250 GMS  sheet C-Hawk / 250 Gm  qty=90  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 747 AS product_id, CAST(363 AS DECIMAL(14,3)) AS qty  -- CAP-X-SP - 100 GMS  sheet Cap X / 100 Gm  qty=363  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1557 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- CHEETAH - 1 L  sheet Cheeta / 1 L  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3016 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- CITIGEN - 30 ML  sheet Citigen / 30 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 573 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- COMBI PLUS - 100 GMS  sheet Combi Plus / 100 Gm  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1067 AS product_id, CAST(54 AS DECIMAL(14,3)) AS qty  -- COMBI PLUS - 250 GMS  sheet Combi Plus / 250 Gm  qty=54  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1502 AS product_id, CAST(18 AS DECIMAL(14,3)) AS qty  -- COMBI PLUS - 500 GMS  sheet Combi Plus / 500 Gm  qty=18  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3849 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- CONFIDENCE 555 - 50 ML  sheet Confidence 555 / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3828 AS product_id, CAST(320 AS DECIMAL(14,3)) AS qty  -- DECLARE - 25 GMS  sheet Declare / 25 Gms  qty=320  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1783 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 10 ML  sheet Dry Up Gold / 10 ml  qty=100  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1724 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 100 ML  sheet Dry Up Gold / 100 ml  qty=50  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2243 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 200 ML  sheet Dry Up Gold / 200 ml  qty=60  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1725 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 50 ML  sheet Dry Up Gold / 50 ml  qty=160  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3152 AS product_id, CAST(8 AS DECIMAL(14,3)) AS qty  -- DRYUP GOLD - 500 ML  sheet Dry Up Gold / 500 ml  qty=8  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3850 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- DURSBAN - 100 ML  sheet Dursban / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3517 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- DURSBAN - 250 ML  sheet Dursban / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2218 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- EM POWER LIQ - 250 ML  sheet Em Power / 250 ML  qty=80  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 122 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- ENCOUNTER - 50MLS  sheet Encounter / 50 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3430 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- ETCIO STAR - 250 ML  sheet Etcio Star / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3431 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- ETCIO STAR - 500 ML  sheet Etcio Star / 500 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3672 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FAITA - 160 ML  sheet Faita / 160 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3760 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FAITA - 40 ML  sheet Faita / 40 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3717 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- FAITA - 80 ML  sheet Faita / 80 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3241 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FENNY - 1 LTR  sheet Fenny / 1 L  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2960 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FENNY - 100 ML  sheet Fenny / 100 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2961 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- FENNY - 250 ML  sheet Fenny / 250 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3172 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- FENNY - 500 ML  sheet Fenny / 500 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2179 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- FERIO - 1L  sheet Ferio / 1 L  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1159 AS product_id, CAST(19 AS DECIMAL(14,3)) AS qty  -- FERTICEM - 1 LITR  sheet Ferticem / 1 L  qty=19  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3509 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- GALAXY EXPERT - 100 ML  sheet Galaxy Expert 0.001 / 100 ml  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 158 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- GUBERA - 100MLS  sheet Gubera / 100 ml  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 159 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- GUBERA - 250MLS  sheet Gubera / 250 ml  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 630 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- GUBERA - 500 ML  sheet Gubera / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 565 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- GURU - 100 ML  sheet Guru / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1347 AS product_id, CAST(32 AS DECIMAL(14,3)) AS qty  -- GURU - 250 ML  sheet Guru / 250 ml  qty=32  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3805 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- HOLD - 40 GMS  sheet Hold / 40 Gm  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 822 AS product_id, CAST(46 AS DECIMAL(14,3)) AS qty  -- HUMACH - 1 KGS  sheet Humach / 1 kg  qty=46  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3177 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- HUMI RICH - 1 LTR  sheet Humirich F / 1 L  qty=10  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3176 AS product_id, CAST(15 AS DECIMAL(14,3)) AS qty  -- HUMI RICH - 500 ML  sheet Humirich F / 500 ml  qty=15  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 527 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- HUMIRICH N - 250 ML  sheet Humirich N / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1785 AS product_id, CAST(22 AS DECIMAL(14,3)) AS qty  -- HURRICANE PLUS - 250 ML  sheet Hurrican Plus / 250 ml  qty=22  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2842 AS product_id, CAST(22 AS DECIMAL(14,3)) AS qty  -- IKEDA - 250 ML  sheet Ikeda / 250 ml  qty=22  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2995 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 1 LITR  sheet Jamindar / 1 L  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2636 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 100 ML  sheet Jamindar / 100 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2623 AS product_id, CAST(280 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 250 ML  sheet Jamindar / 250 ml  qty=280  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2974 AS product_id, CAST(140 AS DECIMAL(14,3)) AS qty  -- JAMINDAR - 500 ML  sheet Jamindar / 500 ml  qty=140  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3519 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- JIVORA - 100 GMS  sheet Jivora / 100 Gm  qty=30  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3312 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- KANTROL PLUSS - 100 ML  sheet Kantrol Plus / 100 ml  qty=0  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3313 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- KANTROL PLUSS - 250 ML  sheet Kantrol Plus / 250 ml  qty=160  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3598 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- KANTROL PLUSS - 500 ML  sheet Kantrol Plus / 500 ml  qty=80  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3371 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- KAVACHAM - 100 GMS  sheet Kavacham / 100 Gms  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3449 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- KAVACHAM - 250 GMS  sheet Kavacham / 250 Gms  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3499 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- KAVACHAM - 500 GMS  sheet Kavacham / 500 Gms  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 579 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- KEMLOX - 100 ML  sheet Kemlox / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 568 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- KEMLOX - 250 ML  sheet Kemlox / 250 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1708 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- KEMSTAR - 100 GMS  sheet Kemstar / 100 Gm  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1081 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- KEMSTAR - 5 GMS  sheet Kemstar / 5 Gm  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3133 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- KEMSTAR EASY - 1 LTR  sheet Kemstar Easy / 1 ltr  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2714 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- KEMSTAR EASY - 100 ML  sheet Kemstar Easy / 100 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2697 AS product_id, CAST(16 AS DECIMAL(14,3)) AS qty  -- KING ZYME BUCKET - 5 KGS  sheet Kingzyme GR / 5 Kg  qty=16  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3004 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- LIGER - 100 ML  sheet Liger / 100 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 518 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- LIHOCIN - 100 ML  sheet Lihocin / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3325 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- MAAGRO - 50 ML  sheet Maagro / 50 ml  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3572 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- MACROFERT HD 20:20:20 - 200 GMS  sheet Microfert HD 20:20:20 / 200 Gms  qty=120  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3857 AS product_id, CAST(240 AS DECIMAL(14,3)) AS qty  -- MAGICAL - 250 ML  sheet Samta-Magical / 250 ml  qty=240  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2962 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- MAGICAL - 500 ML  sheet Samta-Magical / 500 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3053 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- MEDISOL OCEANIC - 100 ML  sheet Medisol Oceanic / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3553 AS product_id, CAST(65 AS DECIMAL(14,3)) AS qty  -- MICRO CARE - 120 GMS  sheet Micro Care / 120 Gm  qty=65  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3552 AS product_id, CAST(39 AS DECIMAL(14,3)) AS qty  -- MICRO CARE - 60 GMS  sheet Micro Care / 60 Gm  qty=39  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 224 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- MICROGREEN - 100GMS  sheet Micro Green / 100 Gm  qty=100  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3316 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- MICRORICH - 250 ML  sheet Microrich / 250 ML  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3317 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- MICRORICH - 500 ML  sheet Microrich / 500 ML  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2834 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- MILQUAT - 1L  sheet Milquat / 1 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 227 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- MIRACLE - 100MLS  sheet Miracle / 100 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2270 AS product_id, CAST(37 AS DECIMAL(14,3)) AS qty  -- MITERICH - 250 ML  sheet Miterich / 250 ml  qty=37  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2798 AS product_id, CAST(42 AS DECIMAL(14,3)) AS qty  -- NANO DAP - 500 ML  sheet Iffco nano DAP / 500 ml  qty=42  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1693 AS product_id, CAST(180 AS DECIMAL(14,3)) AS qty  -- NANO UREA - 500 ML  sheet Iffco Nano urea / 500 ml  qty=180  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3216 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- NOVLECT - 250 ML  sheet Novlect / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3728 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- NUTRI WIN - 250 ML  sheet Nutriwin / 250 ml  qty=40  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3848 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- NUTROZEN - 100 ML  sheet Nutrozen / 100 ml  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2778 AS product_id, CAST(12 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 1 KGS  sheet On A Top / 1 Kg  qty=12  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2747 AS product_id, CAST(300 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 10 GMS  sheet On A Top / 10 Gm  qty=300  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2749 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 100 GMS  sheet On A Top / 100 Gm  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1098 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 250 GMS  sheet On A Top / 250 Gm  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2748 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- ON A TOP - 50 GMS  sheet On A Top / 50 Gm  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2731 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- OXYCLEAN - 250 ML  sheet Oxyclean / 250 ml  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3268 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 100 ML  sheet Pasidi-6 / 100 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3464 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 250 ML  sheet Pasidi-6 / 250 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3024 AS product_id, CAST(400 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 30 ML  sheet Pasidi-6 / 30 ml  qty=400  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3025 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- PASIDI-6 - 50 ML  sheet Pasidi-6 / 50 ml  qty=150  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1294 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- PATELA - 400 ML  sheet Patela / 400 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3791 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- PENDIKEM CS - 350 ML  sheet Pendikem Xtra / 350 ml  qty=150  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3790 AS product_id, CAST(75 AS DECIMAL(14,3)) AS qty  -- PENDIKEM CS - 700 ML  sheet Pendikem Xtra / 700 mml  qty=75  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3853 AS product_id, CAST(34 AS DECIMAL(14,3)) AS qty  -- PORTION - 100 ML  sheet Portion / 100 ml  qty=34  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1112 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- PORTION - 50 ML  sheet Portion / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3573 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 1 LTR  sheet Sea Diamond / 1 L  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2996 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 100 ML  sheet Sea Diamond / 100 ml  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2997 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 250 ML  sheet Sea Diamond / 250 ml  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2998 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- POSHAK SEA DIAMOND - 500 ML  sheet Sea Diamond / 500 ml  qty=0  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2470 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- PRELUDE PLUS - 250 ML  sheet Prelude Plus / 250 ml  qty=160  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3435 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- PRETI EW - 600 ML  sheet Preti Super / 600 ml  qty=100  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1669 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- PROFEX SUPER - 1 L  sheet Profex Super / 1 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1283 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- PROFEX SUPER - 500 ML  sheet Profex Super / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3393 AS product_id, CAST(47 AS DECIMAL(14,3)) AS qty  -- PROFEX ULTRA - 150 GMS  sheet Profex Ultra / 150 Gm  qty=47  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 447 AS product_id, CAST(800 AS DECIMAL(14,3)) AS qty  -- PROGIBB EASY - 2.5 GMS  sheet Progib Easy / 2.5 Gms  qty=800  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3283 AS product_id, CAST(3 AS DECIMAL(14,3)) AS qty  -- PUTIN - 250 ML  sheet Putin / 250 ml  qty=3  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3394 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- PYRAKILL - 100 ML  sheet Pyrakil / 100 ml  qty=200  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3334 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- PYRAKILL - 250 ML  sheet Pyrakil / 250 ml  qty=120  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3424 AS product_id, CAST(22 AS DECIMAL(14,3)) AS qty  -- QUANTIS - 100 ML  sheet Quantis / 100 ml  qty=22  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1386 AS product_id, CAST(42 AS DECIMAL(14,3)) AS qty  -- QUANTIS - 400 ML  sheet Quantis / 400 ml  qty=42  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3120 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- RASAYAN CHLOR - 500 ML  sheet RashayanChlor / 500 ml  qty=80  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2119 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- RESULT - 1 L  sheet Result / 1 L  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1315 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- RESULT - 100 ML  sheet Result / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 613 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- RESULT - 250 ML  sheet Result / 250ml  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 991 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- RESULT - 500 ML  sheet Result / 500 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2658 AS product_id, CAST(250 AS DECIMAL(14,3)) AS qty  -- RICH BOR - 100 GMS  sheet Rich Boron / 100 Gms  qty=250  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2734 AS product_id, CAST(30 AS DECIMAL(14,3)) AS qty  -- RICH GROW - 100 ML  sheet Richgrow / 100 ml  qty=30  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2810 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- RICH GROW - 250 ML  sheet Richgrow / 250 ml  qty=0  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2811 AS product_id, CAST(4 AS DECIMAL(14,3)) AS qty  -- RICH GROW - 500 ML  sheet Richgrow / 500 ml  qty=4  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3505 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- RICH MICRO - 1 LITR  sheet Rich Micro / 1 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3777 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- RONFEN - 1 LTR  sheet Ronfen / 1 L  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2720 AS product_id, CAST(280 AS DECIMAL(14,3)) AS qty  -- RONFEN - 100 ML  sheet Ronfen / 100 ML  qty=280  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2745 AS product_id, CAST(390 AS DECIMAL(14,3)) AS qty  -- RONFEN - 50 ML  sheet Ronfen / 50 ml  qty=390  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3181 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- RONFEN - 500 ML  sheet Ronfen / 500 ML  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1945 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- RUN OUT 71 - 100 GMS  sheet Run Out 71 / 100 Gms  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1655 AS product_id, CAST(160 AS DECIMAL(14,3)) AS qty  -- SAGARIGA - 500 ML  sheet Sagariga / 500 ml  qty=160  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3061 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SAMTA 6-0-18 CA MG ZN - 500 ML  sheet Samta-6-0-18 / 500 ml  qty=40  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3856 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- SAMTA K SHINE - 250 ML  sheet Samta K Shine / 250 ML  qty=80  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 320 AS product_id, CAST(75 AS DECIMAL(14,3)) AS qty  -- SANVEX 50 SP - 250GMS  sheet Sanvex Sp / 250 Gm  qty=75  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 542 AS product_id, CAST(9 AS DECIMAL(14,3)) AS qty  -- SANVEX 50 SP - 500 GMS  sheet Sanvex Sp / 500 Gm  qty=9  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2301 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- SETTI - 100 ML  sheet Setti / 100 ml  qty=150  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3197 AS product_id, CAST(16 AS DECIMAL(14,3)) AS qty  -- SHAKED - 800 ML  sheet Shaked / 800 ml  qty=16  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3783 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- SICKLE - 1 LTR  sheet GSP Sickle / 1 L  qty=10  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3781 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SICKLE - 250 ML  sheet GSP Sickle / 250 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3782 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- SICKLE - 500 ML  sheet GSP Sickle / 500 ML  qty=20  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3746 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- SIPVIN - 100 ML  sheet Sipvin / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3547 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- SLAYER PRO - 50 ML  sheet Slayer Pro / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2806 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SOLOMON - 250 ML  sheet Solomon / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 729 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- SPIC CYTOZYME - 250 ML  sheet Cytozyme / 250 ml  qty=80  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1423 AS product_id, CAST(80 AS DECIMAL(14,3)) AS qty  -- SPIC CYTOZYME - 500 ML  sheet Cytozyme + Spic Cytoz / 500 ml + 500 ml  qty=80  match=packing+tokens+alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3847 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SUMI BLUE DIAMOND - 1KGS  sheet Blue Diamond / 1 Kgs  qty=40  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 333 AS product_id, CAST(62 AS DECIMAL(14,3)) AS qty  -- SUMI PREMPT - 100MLS  sheet Sumi Premt / 100 ml  qty=62  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1197 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- SUPER RACER - 600 ML  sheet Super Racer / 600 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2791 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- SURFAFOUR - 100 ML  sheet Surfafour / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3566 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- TEJA - 100 ML  sheet Teja EW / 100 ml  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3567 AS product_id, CAST(48 AS DECIMAL(14,3)) AS qty  -- TEJA - 250 ML  sheet Teja EW / 250 ml  qty=48  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3628 AS product_id, CAST(24 AS DECIMAL(14,3)) AS qty  -- TEJA - 500 ML  sheet Teja EW / 500 ml  qty=24  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3274 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- TEMPER - 500 GMS  sheet Temper / 500 Gm  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3405 AS product_id, CAST(90 AS DECIMAL(14,3)) AS qty  -- TEPROANIL - 1 KGS  sheet Tepronil / 1 Kg  qty=90  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2619 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- TERMINATOR - 100 ML  sheet Terminator / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2970 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- TERMINATOR - 250 ML  sheet Terminator / 250 ml  qty=0  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2620 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- TERMINATOR - 50 ML  sheet Terminator / 50 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3683 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- THUNDER BOLD - 100 ML  sheet ThunderBolt / 100 ml  qty=100  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3681 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- THUNDER BOLD - 500 ML  sheet ThunderBolt / 500 ml  qty=20  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 345 AS product_id, CAST(600 AS DECIMAL(14,3)) AS qty  -- TILT - 100MLS  sheet Tilt / 100 ml  qty=600  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 346 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- TILT - 250MLS  sheet Tilt / 250 Ml  qty=120  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2343 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- TOBLER - 100 ML  sheet Tobler / 100 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2344 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- TOBLER - 250 ML  sheet Tobler / 250 ml  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2576 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- TOBLER - 500 ML  sheet Tobler / 500 ml  qty=20  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3493 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- TOPPER 71 - 1 KGS  sheet Topper 71 / 1 Kg  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 357 AS product_id, CAST(70 AS DECIMAL(14,3)) AS qty  -- UNIQUAT - 1LTR  sheet Uniquat / 1 L  qty=70  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3494 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- VALXTRA - 100 ML  sheet Willowwood-Val Xtra / 100 ml  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3495 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- VALXTRA - 250 ML  sheet Willowwood-Val Xtra / 250 ml  qty=40  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2973 AS product_id, CAST(70 AS DECIMAL(14,3)) AS qty  -- VAM GOLD - 125 GMS  sheet Vam Gold / 125 gms  qty=70  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3023 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- VAM GOLD - 65 GMS  sheet Vam Gold / 65 Gms  qty=40  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3448 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- VAM GOLD GR - 4 KGS  sheet Vam Gold / 4 Kg  qty=40  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3606 AS product_id, CAST(75 AS DECIMAL(14,3)) AS qty  -- VASUDHAA - 1 KGS  sheet Vasudha / 1 Kg  qty=75  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3463 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- VASUDHAA - 3 KGS  sheet Vasudha / 3 Kg  qty=60  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3665 AS product_id, CAST(5 AS DECIMAL(14,3)) AS qty  -- VESO MAX - 500 ML  sheet Vesomax / 500 ml  qty=5  match=compact-name
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3046 AS product_id, CAST(36 AS DECIMAL(14,3)) AS qty  -- VIAGRO GOLD - 100 ML  sheet Viagro Gold / 100 ml  qty=36  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3327 AS product_id, CAST(136 AS DECIMAL(14,3)) AS qty  -- VIAGRO GOLD - 250 ML  sheet Viagro Gold / 250 ml  qty=136  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3326 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- VIAGRO GOLD - 50 ML  sheet Viagro Gold / 50 ml  qty=200  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 535 AS product_id, CAST(48 AS DECIMAL(14,3)) AS qty  -- VIRAAT - 250 ML  sheet Viraat / 250 ml  qty=48  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3653 AS product_id, CAST(60 AS DECIMAL(14,3)) AS qty  -- VIRAAT VALIDA - 100 ML  sheet Viraat / 100 ml  qty=60  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3643 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- VISWAJIT - 100 GMS  sheet Viswajith / 100 Gms  qty=50  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3602 AS product_id, CAST(50 AS DECIMAL(14,3)) AS qty  -- WEALTH - 1 L  sheet Wealth / 1 L  qty=50  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3604 AS product_id, CAST(10 AS DECIMAL(14,3)) AS qty  -- WEALTH - 5 L  sheet Wealth / 5 L  qty=10  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3153 AS product_id, CAST(0 AS DECIMAL(14,3)) AS qty  -- WEED BLLAZE - 1 LTR  sheet Weed Blaze / 1 L  qty=0  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2701 AS product_id, CAST(120 AS DECIMAL(14,3)) AS qty  -- WEED BLLAZE - 250 ML  sheet Weed Blaze / 250 ml  qty=120  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 2700 AS product_id, CAST(20 AS DECIMAL(14,3)) AS qty  -- WEED BLLAZE - 400 ML  sheet Weed Blaze / 400 ml  qty=20  match=alias
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3876 AS product_id, CAST(150 AS DECIMAL(14,3)) AS qty  -- YAMRAZ - 100 ML  sheet Yamraz / 100 ml  qty=150  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3877 AS product_id, CAST(36 AS DECIMAL(14,3)) AS qty  -- YAMRAZ - 250 ML  sheet Yamraz / 250 ml  qty=36  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 1834 AS product_id, CAST(21 AS DECIMAL(14,3)) AS qty  -- YES BOSS BLACK MAGIC - 250 ML  sheet Black magic / 250 ml  qty=21  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3428 AS product_id, CAST(200 AS DECIMAL(14,3)) AS qty  -- ZEN SPIC - 100 GMS  sheet Spic Zen / 100 Gm  qty=200  match=packing+tokens
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3595 AS product_id, CAST(100 AS DECIMAL(14,3)) AS qty  -- ZIPPY GOLD - 100 ML  sheet Zippy Gold / 100 ml  qty=100  match=exact
  UNION ALL SELECT 1 AS organization_id, 3 AS branch_id, 3596 AS product_id, CAST(40 AS DECIMAL(14,3)) AS qty  -- ZIPPY GOLD - 250 ML  sheet Zippy Gold / 250 ml  qty=40  match=exact
) x ON x.product_id = s.product_id
   AND x.organization_id = s.organization_id
   AND x.branch_id = s.branch_id
SET s.quantity = x.qty, s.updated_at = NOW()
WHERE s.organization_id = 1 AND s.branch_id = 3;

-- ---------------------------------------------------------------------------
-- STEP 2) Expiry on STOCK-ON-HAND (from sheet, where present)
-- ---------------------------------------------------------------------------
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3880 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2026-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3237 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-05-01');
UPDATE batch SET expiry_date = '2026-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3238 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-05-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 834 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3209 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1532 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3758 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3636 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3246 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2029-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3247 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-04-01');
UPDATE batch SET expiry_date = '2026-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2551 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-12-01');
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3886 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3887 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3557 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3555 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3554 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2030-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3569 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2030-05-01');
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3416 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');
UPDATE batch SET expiry_date = '2028-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 804 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-10-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 76 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3412 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1020 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1576 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1018 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1019 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3563 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 747 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3016 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 573 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1067 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1502 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3849 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2026-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3828 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-04-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1783 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1724 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2243 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1725 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2027-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3152 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-04-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3850 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3517 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2218 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 122 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2027-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3430 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-06-01');
UPDATE batch SET expiry_date = '2027-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3431 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-06-01');
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3672 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3717 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2960 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2179 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1159 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3509 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');
UPDATE batch SET expiry_date = '2028-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 158 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-09-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1785 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2025-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2842 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2025-06-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2636 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '2028-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2623 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-10-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2974 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3519 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3313 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3598 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3371 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3449 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 579 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2026-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 568 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-08-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1708 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1081 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3133 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2714 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2697 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3004 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 518 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '1931-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3325 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '1931-04-01');
UPDATE batch SET expiry_date = '2026-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3572 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-04-01');
UPDATE batch SET expiry_date = '2029-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3857 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-04-01');
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2962 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3053 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2028-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3553 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-10-01');
UPDATE batch SET expiry_date = '2028-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3552 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-10-01');
UPDATE batch SET expiry_date = '2028-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 224 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-09-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2834 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 227 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');
UPDATE batch SET expiry_date = '2026-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2270 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-12-01');
UPDATE batch SET expiry_date = '2025-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2798 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2025-05-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3216 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2028-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3848 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-09-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2778 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2027-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2747 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-02-01');
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2749 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2027-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1098 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-10-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2748 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2025-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2731 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2025-12-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3268 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3464 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3024 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3025 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3791 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3790 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1112 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2996 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2470 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3435 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1283 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3393 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 447 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3283 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');
UPDATE batch SET expiry_date = '2028-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3394 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-08-01');
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3334 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2026-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3424 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-10-01');
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1386 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');
UPDATE batch SET expiry_date = '2029-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3120 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-10-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1315 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 613 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 991 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2029-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2734 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-10-01');
UPDATE batch SET expiry_date = '2029-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2810 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-03-01');
UPDATE batch SET expiry_date = '2029-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3505 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-09-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3777 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2720 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2028-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2745 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-07-01');
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1945 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3061 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2029-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3856 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-04-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 320 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2026-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 542 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-12-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2301 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3197 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2028-04-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3783 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-04-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3781 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3782 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3746 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3547 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2806 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '2029-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 729 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-01-01');
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1423 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3847 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2028-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 333 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-02-01');
UPDATE batch SET expiry_date = '2027-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1197 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-01-01');
UPDATE batch SET expiry_date = '2028-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3566 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-11-01');
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3567 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3628 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3274 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');
UPDATE batch SET expiry_date = '2028-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2619 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-12-01');
UPDATE batch SET expiry_date = '2028-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2970 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-05-01');
UPDATE batch SET expiry_date = '2028-03-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2620 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-03-01');
UPDATE batch SET expiry_date = '2028-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3683 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-08-01');
UPDATE batch SET expiry_date = '2028-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3681 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-08-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 345 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 346 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2343 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2344 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2576 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3493 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2029-05-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 357 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2029-05-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3494 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2026-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3495 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-01');
UPDATE batch SET expiry_date = '2026-11-11', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2973 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-11-11');
UPDATE batch SET expiry_date = '2027-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3023 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-11-01');
UPDATE batch SET expiry_date = '2028-08-11', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3606 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-08-11');
UPDATE batch SET expiry_date = '2026-08-11', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3463 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-08-11');
UPDATE batch SET expiry_date = '2026-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3665 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2026-09-01');
UPDATE batch SET expiry_date = '2030-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3046 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2030-06-01');
UPDATE batch SET expiry_date = '1931-02-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3326 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '1931-02-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 535 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-01-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3653 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-01-01');
UPDATE batch SET expiry_date = '2028-10-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3643 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-10-01');
UPDATE batch SET expiry_date = '2027-07-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2701 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-07-01');
UPDATE batch SET expiry_date = '2027-08-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 2700 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-08-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3876 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2028-06-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3877 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2028-06-01');
UPDATE batch SET expiry_date = '2025-11-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 1834 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2025-11-01');
UPDATE batch SET expiry_date = '2027-12-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3428 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-12-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3595 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');
UPDATE batch SET expiry_date = '2027-09-01', updated_at = NOW() WHERE organization_id = 1 AND product_id = 3596 AND batch_no = 'STOCK-ON-HAND' AND (expiry_date IS NULL OR expiry_date <> '2027-09-01');

COMMIT;

-- ---------------------------------------------------------------------------
-- Unmatched sheet rows (not applied). Add aliases or create the packing in product.
-- ---------------------------------------------------------------------------

-- Aries -Chelamin / 500 ml   Godown=20   (unmatched)
-- Autor / 300 ml   Godown=20   (unmatched)
-- Bounous / 250 ml   Godown=32   (unmatched)
-- Brand / 50 ml   Godown=29   (unmatched)
-- Bumper / 500 ml   Godown=40   (unmatched)
-- Bumper / 1 L   Godown=10   (unmatched)
-- Camalus / 400 ml   Godown=18   (unmatched)
-- Grande / 500 ml   Godown=20   (unmatched)
-- GSP Safari / 1 Kg   Godown=8   (unmatched)
-- Indo Top / 50 Gms   Godown=50   (unmatched)
-- Kushi Gel / 1 L   Godown=52   (unmatched)
-- Pherlap / 250 ml   Godown=24   (unmatched)
-- Power bank / 100 ml   Godown=120   (unmatched)
-- Pyrakil / 500 ml   Godown=0   (unmatched)
-- Rabit / 20 Gm   Godown=100   (unmatched)
-- Rich Boron / 10 ML   Godown=10   (unmatched)
-- Rich Vegetable / 1 L   Godown=20   (unmatched)
-- Surplus / 300 Gm   Godown=40   (unmatched)
-- Topper 71 / 500 Gm   Godown=20   (unmatched)
-- Vajra 00:00:50 / 500 ml   Godown=40   (unmatched)
-- Vajra 00:00:50 / 1 L   Godown=10   (unmatched)
-- Vajra 19:19:19 / 250 ml   Godown=40   (unmatched)
-- Vajra 19:19:19 / 500 ml   Godown=80   (unmatched)
-- Vajra 19:19:19 / 1 L   Godown=10   (unmatched)
-- Vesagro / 500 ml   Godown=20   (unmatched)
-- Vesagro / 1 L   Godown=10   (unmatched)
-- Viswajith / 250 Gms   Godown=0   (unmatched)

-- Duplicate mappings (merged):
--   product_id=2636 recount Jamindar/100 ml kept qty=0
--   product_id=2623 recount Jamindar/250 ml kept qty=280
--   product_id=2974 recount Jamindar/500 ml kept qty=140
--   product_id=2995 recount Jamindar/1 L kept qty=0
--   product_id=1081 recount Kemstar/5 Gm kept qty=400
--   product_id=3572 recount Microfert HD 20:20:20/200 Gms kept qty=120
--   product_id=3856 recount Samta K Shine/250 ML kept qty=80
--   product_id=1423 summed Cytozyme/500 ml=60 + Spic Cytoz/500 ml=20 -> 80
--   product_id=3046 recount Viagro Gold/100 ml kept qty=36

-- Applied unique products: 227  qty 18811
-- Unmatched counted rows: 27

-- Quick check after load:
--   SELECT COUNT(*), SUM(quantity) FROM stock WHERE organization_id = 1 AND branch_id = 3;

