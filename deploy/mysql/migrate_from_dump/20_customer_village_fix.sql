-- Normalize customer.village / customer.district against LGD village panchayats
-- in deploy/mysql/master_villages.sql, plus SKAC shop abbreviations.
--
-- Review before running. Safe to re-run (matches old typed names and official names).
-- Run after 07_customer.sql (and after master_villages.sql so POS dropdowns exist).
--
-- Customers from dump: 20425 (empty village: 4)
-- Unique typed villages: 2912
-- Official LGD matches: 11494 customers, 427 spellings
-- Habitations not in LGD: 3303 customers, 63 spellings
-- Left unmatched (title-cased, district Tiruvannamalai): 5624 customers, 2422 spellings
--
-- Shop abbreviations used only when the AVL/TVM split is clear:
--   K.P / K.PURAIUR     → Kovilporaiyur (Viluppuram, Melmalayanur)
--   A.P / AVALURPET     → Avalurpettai (Viluppuram)  [A.P is AVL-shop, not Ananthapuram]
--   B.M                 → Boodamangalam (Tiruvannamalai)
--   T.K / T.KUPPAM      → Thathankuppam (habitation, not in LGD)
-- Duplicate panchayat names (Mangalam, Mottur, …) prefer Tiruvannamalai,
-- or Viluppuram Melmalayanur when 80%+ of that spelling is AVL-shop.
--
-- mysql -u root -p skac_new < deploy/mysql/migrate_from_dump/20_customer_village_fix.sql

USE skac_new;
SET NAMES utf8mb4;

SET @org_id := 1;
SET @d_kallakurichi := (SELECT id FROM config_item WHERE organization_id=@org_id AND kind='district' AND code='kallakurichi' AND is_deleted=0 ORDER BY id LIMIT 1);
SET @d_tiruvannamalai := (SELECT id FROM config_item WHERE organization_id=@org_id AND kind='district' AND code='tiruvannamalai' AND is_deleted=0 ORDER BY id LIMIT 1);
SET @d_viluppuram := (SELECT id FROM config_item WHERE organization_id=@org_id AND kind='district' AND code='viluppuram' AND is_deleted=0 ORDER BY id LIMIT 1);

-- ---------------------------------------------------------------------------
-- A) Official LGD village panchayat names + district
-- ---------------------------------------------------------------------------

-- 700 customers  VEDANTHAVADI x611, VEDAANTHAVADI x59, VEDANTHAVDI x23, V VADI x5, VEDANDHAVADI x1, V 'VADI x1  →  Vedandavadi / Tiruvannamalai
UPDATE customer SET village = 'Vedandavadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vedandavadi', 'VEDANTHAVADI', 'VEDAANTHAVADI', 'VEDANTHAVDI', 'V VADI', 'V \'VADI', 'VEDANDHAVADI', 'V \'Vadi', 'V Vadi', 'Vedaanthavadi', 'Vedandhavadi', 'Vedanthavadi', 'Vedanthavdi');

-- 576 customers  K.P x204, K.PURAIUR x153, K.PURAIOUR x131, KOVILPURAIUR x37, K. PURAIUR x28, KOVILPURAIYUR x9, K.PURAIYUR x4, KP x4, KOVIL PURAIYUR x3, KOVIL PORAIYUR x1, K.PURAIOUR,KELAKUPPAM x1, KOVILPORAIYUR x1  →  Kovilporaiyur / Viluppuram
UPDATE customer SET village = 'Kovilporaiyur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kovilporaiyur', 'K.P', 'K.PURAIUR', 'K.PURAIOUR', 'KOVILPURAIUR', 'K. PURAIUR', 'KOVILPURAIYUR', 'K.PURAIYUR', 'KP', 'KOVIL PURAIYUR', 'K.PURAIOUR,KELAKUPPAM', 'KOVIL PORAIYUR', 'KOVILPORAIYUR', 'K. Puraiur', 'K.Puraiour', 'K.Puraiour,Kelakuppam', 'K.Puraiur', 'K.Puraiyur', 'Kovil Poraiyur', 'Kovil Puraiyur', 'Kovilpuraiur', 'Kovilpuraiyur', 'Kp');

-- 445 customers  ERUMBUNDI x221, ERUMPUNDI x130, ERUMPOONDI x59, ERUMBOONDI x33, ERUMPOONNDI x1, ERRUMPOONDI x1  →  Erumpoondi / Tiruvannamalai
UPDATE customer SET village = 'Erumpoondi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Erumpoondi', 'ERUMBUNDI', 'ERUMPUNDI', 'ERUMPOONDI', 'ERUMBOONDI', 'ERRUMPOONDI', 'ERUMPOONNDI', 'Errumpoondi', 'Erumboondi', 'Erumbundi', 'Erumpoonndi', 'Erumpundi');

-- 415 customers  PALANANTHAL x161, MELPALANANTHAL x72, PALANANDHAL x36, KELPALANANTHAL x30, MELPALANANDHAL x25, MELPALANADHAL x25, PALANADHAL x24, KILPALANANTHAL x23, PALANANDAL x11, MEL PALANANTHAL x6, PALANANTHAL,STALIN x1, KILPALANANTHAL,MGR x1  →  Palanandal / Tiruvannamalai
UPDATE customer SET village = 'Palanandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Palanandal', 'PALANANTHAL', 'MELPALANANTHAL', 'PALANANDHAL', 'KELPALANANTHAL', 'MELPALANADHAL', 'MELPALANANDHAL', 'PALANADHAL', 'KILPALANANTHAL', 'PALANANDAL', 'MEL PALANANTHAL', 'KILPALANANTHAL,MGR', 'PALANANTHAL,STALIN', 'Kelpalananthal', 'Kilpalananthal', 'Kilpalananthal,Mgr', 'Mel Palananthal', 'Melpalanadhal', 'Melpalanandhal', 'Melpalananthal', 'Palanadhal', 'Palanandhal', 'Palananthal', 'Palananthal,Stalin');

-- 414 customers  SADAYANUDAI x269, SADAYANODAI x145  →  Sadayanodai / Tiruvannamalai
UPDATE customer SET village = 'Sadayanodai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sadayanodai', 'SADAYANUDAI', 'SADAYANODAI', 'Sadayanudai');

-- 398 customers  BOOTHAMANGALAM x250, B.M x99, B.MANGALAM x29, BM x17, BUTHAMANGALAM x2, BOODHAMANGALAM x1  →  Boodamangalam / Tiruvannamalai
UPDATE customer SET village = 'Boodamangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Boodamangalam', 'BOOTHAMANGALAM', 'B.M', 'B.MANGALAM', 'BM', 'BUTHAMANGALAM', 'BOODHAMANGALAM', 'B.Mangalam', 'Bm', 'Boodhamangalam', 'Boothamangalam', 'Buthamangalam');

-- 395 customers  KALASTHAMBADI x294, KALASTHAMABADI x56, KALASTHAMPADI x43, KALASTHAMPADI,INDRA NAGAR x1, KALASTHAMBADI,INTHARANAGAR x1  →  Kalasthambadi / Tiruvannamalai
UPDATE customer SET village = 'Kalasthambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kalasthambadi', 'KALASTHAMBADI', 'KALASTHAMABADI', 'KALASTHAMPADI', 'KALASTHAMBADI,INTHARANAGAR', 'KALASTHAMPADI,INDRA NAGAR', 'Kalasthamabadi', 'Kalasthambadi,Intharanagar', 'Kalasthampadi', 'Kalasthampadi,Indra Nagar');

-- 393 customers  VALLIVAGAI x379, VALIVAGAI x10, VALLI VAGAI x2, VALLIVAGAI,KUNNAMKUPPAM x1, VALLIVAGAI,ETTAYAPUREM x1  →  Vallivagai / Tiruvannamalai
UPDATE customer SET village = 'Vallivagai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vallivagai', 'VALLIVAGAI', 'VALIVAGAI', 'VALLI VAGAI', 'VALLIVAGAI,ETTAYAPUREM', 'VALLIVAGAI,KUNNAMKUPPAM', 'Valivagai', 'Valli Vagai', 'Vallivagai,Ettayapurem', 'Vallivagai,Kunnamkuppam');

-- 372 customers  KEKLUR x202, KEKKALUR x103, KEGALUR x22, KEKALUR x20, KEEKALUR x11, KIKKALUR x5, KIKALUR x5, KEKALUR,PURAVADAI x1, KEKLUR,KATTUKULAM x1, KEKLUR ,PURADAI x1, KEKLUR,PURAVADAI x1  →  Keekalur / Tiruvannamalai
UPDATE customer SET village = 'Keekalur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Keekalur', 'KEKLUR', 'KEKKALUR', 'KEGALUR', 'KEKALUR', 'KEEKALUR', 'KIKALUR', 'KIKKALUR', 'KEKALUR,PURAVADAI', 'KEKLUR ,PURADAI', 'KEKLUR,KATTUKULAM', 'KEKLUR,PURAVADAI', 'Kegalur', 'Kekalur', 'Kekalur,Puravadai', 'Kekkalur', 'Keklur', 'Keklur ,Puradai', 'Keklur,Kattukulam', 'Keklur,Puravadai', 'Kikalur', 'Kikkalur');

-- 356 customers  SANANTHAL x264, SANANDHAL x62, SANANANTHAL x21, SANANDAL x7, SANANANTHAL,3840 9180 5176 x1, SANANANTHAL,9616 4252 1517 x1  →  Sananandal / Tiruvannamalai
UPDATE customer SET village = 'Sananandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sananandal', 'SANANTHAL', 'SANANDHAL', 'SANANANTHAL', 'SANANDAL', 'SANANANTHAL,3840 9180 5176', 'SANANANTHAL,9616 4252 1517', 'Sanananthal', 'Sanananthal,3840 9180 5176', 'Sanananthal,9616 4252 1517', 'Sanandal', 'Sanandhal', 'Sananthal');

-- 355 customers  ANANTHAL x327, ANATHAL x27, ANANTHAL,KALARPALAIYAM x1  →  Ananandal / Tiruvannamalai
UPDATE customer SET village = 'Ananandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ananandal', 'ANANTHAL', 'ANATHAL', 'ANANTHAL,KALARPALAIYAM', 'Ananthal', 'Ananthal,Kalarpalaiyam', 'Anathal');

-- 348 customers  KILIPATTU x197, KILIYAPATTU x146, KILLIYAPATTU x2, KILIPATTU,KELKUNNUMURINJI x1, KILIPATTU,7021 0171 0906 x1, KILIYAPPATTU x1  →  Kiliyapattu / Tiruvannamalai
UPDATE customer SET village = 'Kiliyapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kiliyapattu', 'KILIPATTU', 'KILIYAPATTU', 'KILLIYAPATTU', 'KILIPATTU,7021 0171 0906', 'KILIPATTU,KELKUNNUMURINJI', 'KILIYAPPATTU', 'Kilipattu', 'Kilipattu,7021 0171 0906', 'Kilipattu,Kelkunnumurinji', 'Kiliyappattu', 'Killiyapattu');

-- 344 customers  AVALURPET x186, A.P x155, AP x2, A P x1  →  Avalurpettai / Viluppuram
UPDATE customer SET village = 'Avalurpettai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Avalurpettai', 'AVALURPET', 'A.P', 'AP', 'A P', 'Ap', 'Avalurpet');

-- 302 customers  NOOKAMBADI x164, NUKAMBADI x129, NUKKAMBADI x9  →  Nookkambadi / Tiruvannamalai
UPDATE customer SET village = 'Nookkambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nookkambadi', 'NOOKAMBADI', 'NUKAMBADI', 'NUKKAMBADI', 'Nookambadi', 'Nukambadi', 'Nukkambadi');

-- 290 customers  MANGALAM x287, MANGALAM,KEDATHANGAL x1, MANGALAM,AMMANKALODAI x1, AMMANKALOADI,MANGALAM x1  →  Mangalam / Tiruvannamalai
UPDATE customer SET village = 'Mangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mangalam', 'MANGALAM', 'AMMANKALOADI,MANGALAM', 'MANGALAM,AMMANKALODAI', 'MANGALAM,KEDATHANGAL', 'Ammankaloadi,Mangalam', 'Mangalam,Ammankalodai', 'Mangalam,Kedathangal');

-- 283 customers  KELAKUPPAM x170, KILKUPPAM x42, KELKUPPAM x30, KILAKUPPAM x22, KEELKUPPAM x19  →  Kilkuppam / Tiruvannamalai
UPDATE customer SET village = 'Kilkuppam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kilkuppam', 'KELAKUPPAM', 'KILKUPPAM', 'KELKUPPAM', 'KILAKUPPAM', 'KEELKUPPAM', 'Keelkuppam', 'Kelakuppam', 'Kelkuppam', 'Kilakuppam');

-- 277 customers  KODAPADI x117, KODAMPADI x113, KODAMBADI x47  →  Kodampadi / Viluppuram
UPDATE customer SET village = 'Kodampadi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kodampadi', 'KODAPADI', 'KODAMPADI', 'KODAMBADI', 'Kodambadi', 'Kodapadi');

-- 277 customers  VADUGAPUNDI x245, VADUGABUNDI x26, VADUKAPOONDI x5, VADUKAPUNDI x1  →  Vadukapoondi / Viluppuram
UPDATE customer SET village = 'Vadukapoondi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Vadukapoondi', 'VADUGAPUNDI', 'VADUGABUNDI', 'VADUKAPOONDI', 'VADUKAPUNDI', 'Vadugabundi', 'Vadugapundi', 'Vadukapundi');

-- 265 customers  NOCHALUR x261, NOCHALLUR x3, NOCHILUR x1  →  Nochalur / Viluppuram
UPDATE customer SET village = 'Nochalur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Nochalur', 'NOCHALUR', 'NOCHALLUR', 'NOCHILUR', 'Nochallur', 'Nochilur');

-- 235 customers  SAVARAPUNDI x64, SEVARAPUNDI x49, SEYAPUNDI x37, SAVARABUNDI x33, SEIYAPUNDI x25, SEVARAPOONDI x23, SAVARAPOONDI x4  →  Sevarapoondi / Tiruvannamalai
UPDATE customer SET village = 'Sevarapoondi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sevarapoondi', 'SAVARAPUNDI', 'SEVARAPUNDI', 'SEYAPUNDI', 'SAVARABUNDI', 'SEIYAPUNDI', 'SEVARAPOONDI', 'SAVARAPOONDI', 'Savarabundi', 'Savarapoondi', 'Savarapundi', 'Seiyapundi', 'Sevarapundi', 'Seyapundi');

-- 220 customers  METTUVAILAMBUR x132, MELVAILAMBUR x85, MELVAILAMUR x3  →  Melvailamur / Viluppuram
UPDATE customer SET village = 'Melvailamur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Melvailamur', 'METTUVAILAMBUR', 'MELVAILAMBUR', 'MELVAILAMUR', 'Melvailambur', 'Mettuvailambur');

-- 193 customers  KUNTHALAPATTU x101, KUNTHALAMPATTU x90, KUNTHALAM PATTU x2  →  Kunthalampattu / Viluppuram
UPDATE customer SET village = 'Kunthalampattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kunthalampattu', 'KUNTHALAPATTU', 'KUNTHALAMPATTU', 'KUNTHALAM PATTU', 'Kunthalam Pattu', 'Kunthalapattu');

-- 176 customers  VELUGANADHAL x62, VELUGANANTHAL x50, VELUGANATHAL x28, VELUGANANDHAL x25, VELUGANANDAL x10, VELUGANANTHAL,7857 5965 2358 x1  →  Veluganandal / Tiruvannamalai
UPDATE customer SET village = 'Veluganandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Veluganandal', 'VELUGANADHAL', 'VELUGANANTHAL', 'VELUGANATHAL', 'VELUGANANDHAL', 'VELUGANANDAL', 'VELUGANANTHAL,7857 5965 2358', 'Veluganadhal', 'Veluganandhal', 'Velugananthal', 'Velugananthal,7857 5965 2358', 'Veluganathal');

-- 173 customers  THAYANUR x172, THAYANUR ,THOPPU x1  →  Thayanur / Viluppuram
UPDATE customer SET village = 'Thayanur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Thayanur', 'THAYANUR', 'THAYANUR ,THOPPU', 'Thayanur ,Thoppu');

-- 170 customers  ETHAPATTU x168, ETHAPPATTU x2  →  Edapattu / Viluppuram
UPDATE customer SET village = 'Edapattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Edapattu', 'ETHAPATTU', 'ETHAPPATTU', 'Ethapattu', 'Ethappattu');

-- 145 customers  SENTHIPATTU x110, SINTHIPATTU x33, SINDHIPATTU x1, SINTHIPATU x1  →  Sinthipattu / Viluppuram
UPDATE customer SET village = 'Sinthipattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Sinthipattu', 'SENTHIPATTU', 'SINTHIPATTU', 'SINDHIPATTU', 'SINTHIPATU', 'Senthipattu', 'Sindhipattu', 'Sinthipatu');

-- 141 customers  MEKLUR x80, MEKKALUR x51, MEKALUR x10  →  Mekkalur / Tiruvannamalai
UPDATE customer SET village = 'Mekkalur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mekkalur', 'MEKLUR', 'MEKKALUR', 'MEKALUR', 'Mekalur', 'Meklur');

-- 134 customers  MANANTHAL x132, MANANTHAL,MOTTUR x2  →  Manandal / Viluppuram
UPDATE customer SET village = 'Manandal', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Manandal', 'MANANTHAL', 'MANANTHAL,MOTTUR', 'Mananthal', 'Mananthal,Mottur');

-- 132 customers  NAMINTHAL x45, NAMMIYANTHAL x43, T.NAMINTHAL x39, NAMMIYANDAL x3, T. NAMINTHAL x1, NAMIYANDAL x1  →  So.namiyandal / Tiruvannamalai
UPDATE customer SET village = 'So.namiyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('So.namiyandal', 'NAMINTHAL', 'NAMMIYANTHAL', 'T.NAMINTHAL', 'NAMMIYANDAL', 'NAMIYANDAL', 'T. NAMINTHAL', 'Naminthal', 'Namiyandal', 'Nammiyandal', 'Nammiyanthal', 'T. Naminthal', 'T.Naminthal');

-- 126 customers  ARPAKKAM x121, ARPAKAM x4, ARRPAKKAM x1  →  Arppakkam / Tiruvannamalai
UPDATE customer SET village = 'Arppakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Arppakkam', 'ARPAKKAM', 'ARPAKAM', 'ARRPAKKAM', 'Arpakam', 'Arpakkam', 'Arrpakkam');

-- 124 customers  VADAANDAPATTU x117, VADANDAPATTU x6, VADA ANDAPATTU x1  →  Vadaandapattu / Tiruvannamalai
UPDATE customer SET village = 'Vadaandapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vadaandapattu', 'VADAANDAPATTU', 'VADANDAPATTU', 'VADA ANDAPATTU', 'Vada Andapattu', 'Vadandapattu');

-- 118 customers  MOTTUR x114, M.MOTTUR x2, KORATTUKUPPAM,MOTTUR x1, MOTTOOR x1  →  Mottur / Tiruvannamalai
UPDATE customer SET village = 'Mottur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mottur', 'MOTTUR', 'M.MOTTUR', 'KORATTUKUPPAM,MOTTUR', 'MOTTOOR', 'Korattukuppam,Mottur', 'M.Mottur', 'Mottoor');

-- 117 customers  D NAMMIYANTHAL x65, THURKAINAMINTHAL x23, DURGAINAMMIYANTHAL x11, D.NAMINTHAL x8, DURGAI NAMIYANDAL x2, DHURGAINAMMIYANTHAL x1, THURGAINAMMIYANTHAL x1, THURGAINAMINTHAL x1, DHURGAINAMIYANDHAL x1, DURGAI NAMMIYANDAL x1, DURGAINAMIYANDAL x1, DURGAI NAMIYANTHAL x1, D.NAMIYANDAL x1  →  Durgainammiyandal / Tiruvannamalai
UPDATE customer SET village = 'Durgainammiyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Durgainammiyandal', 'D NAMMIYANTHAL', 'THURKAINAMINTHAL', 'DURGAINAMMIYANTHAL', 'D.NAMINTHAL', 'DURGAI NAMIYANDAL', 'D.NAMIYANDAL', 'DHURGAINAMIYANDHAL', 'DHURGAINAMMIYANTHAL', 'DURGAI NAMIYANTHAL', 'DURGAI NAMMIYANDAL', 'DURGAINAMIYANDAL', 'THURGAINAMINTHAL', 'THURGAINAMMIYANTHAL', 'D Nammiyanthal', 'D.Naminthal', 'D.Namiyandal', 'Dhurgainamiyandhal', 'Dhurgainammiyanthal', 'Durgai Namiyandal', 'Durgai Namiyanthal', 'Durgai Nammiyandal', 'Durgainamiyandal', 'Durgainammiyanthal', 'Thurgainaminthal', 'Thurgainammiyanthal', 'Thurkainaminthal');

-- 110 customers  KUNNIYANTHAL x75, KUNNIYENTHAL x28, KUNIYANTHAL x3, KUNNIYANDAL x3, KUNNIYANDHAL x1  →  Kunniyandal / Tiruvannamalai
UPDATE customer SET village = 'Kunniyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kunniyandal', 'KUNNIYANTHAL', 'KUNNIYENTHAL', 'KUNIYANTHAL', 'KUNNIYANDAL', 'KUNNIYANDHAL', 'Kuniyanthal', 'Kunniyandhal', 'Kunniyanthal', 'Kunniyenthal');

-- 108 customers  RANTHAM x107, RANTHAM,ANNANAGAR x1  →  Rantham / Tiruvannamalai
UPDATE customer SET village = 'Rantham', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Rantham', 'RANTHAM', 'RANTHAM,ANNANAGAR', 'Rantham,Annanagar');

-- 105 customers  KARADIKUPPAM x103, KARADIKKUPPAM x1, KARADIKKUPAM x1  →  Karadikuppam / Viluppuram
UPDATE customer SET village = 'Karadikuppam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Karadikuppam', 'KARADIKUPPAM', 'KARADIKKUPAM', 'KARADIKKUPPAM', 'Karadikkupam', 'Karadikkuppam');

-- 99 customers  THURINJAPURAM x63, THURINJAPUREM x32, THURINJAPUREM,PUDHUR x1, THURINJA PURAM x1, DHURINJAPURAM x1, DURINJAPURAM x1  →  Thurinjapuram / Tiruvannamalai
UPDATE customer SET village = 'Thurinjapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thurinjapuram', 'THURINJAPURAM', 'THURINJAPUREM', 'DHURINJAPURAM', 'DURINJAPURAM', 'THURINJA PURAM', 'THURINJAPUREM,PUDHUR', 'Dhurinjapuram', 'Durinjapuram', 'Thurinja Puram', 'Thurinjapurem', 'Thurinjapurem,Pudhur');

-- 83 customers  KAPPALAMPADI x59, KAPPALAPADI x22, KAPPLAMPADI x1, KAPLAMPADI x1  →  Kapplampadi / Viluppuram
UPDATE customer SET village = 'Kapplampadi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kapplampadi', 'KAPPALAMPADI', 'KAPPALAPADI', 'KAPLAMPADI', 'KAPPLAMPADI', 'Kaplampadi', 'Kappalampadi', 'Kappalapadi');

-- 76 customers  PARAIYAPATTU x76  →  Paraiampattu / Viluppuram
UPDATE customer SET village = 'Paraiampattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Paraiampattu', 'PARAIYAPATTU', 'Paraiyapattu');

-- 71 customers  KOTTAPUNDI x50, KOTTAPOONDI x12, KOTTAPONDI x9  →  Kottapondi / Viluppuram
UPDATE customer SET village = 'Kottapondi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kottapondi', 'KOTTAPUNDI', 'KOTTAPOONDI', 'KOTTAPONDI', 'Kottapoondi', 'Kottapundi');

-- 70 customers  RANDHAM x63, RANDAM x7  →  Randam / Tiruvannamalai
UPDATE customer SET village = 'Randam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Randam', 'RANDHAM', 'RANDAM', 'Randham');

-- 65 customers  PARAIYAMPATTU x46, PARAYAMPATTU x19  →  Parayampattu / Tiruvannamalai
UPDATE customer SET village = 'Parayampattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Parayampattu', 'PARAIYAMPATTU', 'PARAYAMPATTU', 'Paraiyampattu');

-- 63 customers  AATHIPATTU x36, ATHIPATTU x27  →  Athipattu / Viluppuram
UPDATE customer SET village = 'Athipattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Athipattu', 'AATHIPATTU', 'ATHIPATTU', 'Aathipattu');

-- 60 customers  KARUMARAPATTI x58, KARUMARAPATI x2  →  Karumarapatti / Tiruvannamalai
UPDATE customer SET village = 'Karumarapatti', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Karumarapatti', 'KARUMARAPATTI', 'KARUMARAPATI', 'Karumarapati');

-- 56 customers  PADAGAM x56  →  Padagam / Tiruvannamalai
UPDATE customer SET village = 'Padagam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Padagam', 'PADAGAM');

-- 54 customers  INAMKARIYANTHAL x48, INNAMKARIYANTHAL x2, INAMKARIYANDAL x2, INAMKARIYANDHAL x1, INAM KARIYANTHAL x1  →  Inamkariyandal / Tiruvannamalai
UPDATE customer SET village = 'Inamkariyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Inamkariyandal', 'INAMKARIYANTHAL', 'INAMKARIYANDAL', 'INNAMKARIYANTHAL', 'INAM KARIYANTHAL', 'INAMKARIYANDHAL', 'Inam Kariyanthal', 'Inamkariyandhal', 'Inamkariyanthal', 'Innamkariyanthal');

-- 51 customers  KAIKULAM x47, KAZHIKULAM x4  →  Kazhikulam / Tiruvannamalai
UPDATE customer SET village = 'Kazhikulam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kazhikulam', 'KAIKULAM', 'KAZHIKULAM', 'Kaikulam');

-- 51 customers  MELPUTHUPATTU x48, MELPUDUPATTU x2, MEL PUTHUPATTU x1  →  Melpudupattu / Viluppuram
UPDATE customer SET village = 'Melpudupattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Melpudupattu', 'MELPUTHUPATTU', 'MELPUDUPATTU', 'MEL PUTHUPATTU', 'Mel Puthupattu', 'Melputhupattu');

-- 47 customers  KADAPANANTHAL x45, KADAPPANANTHAL x2  →  Kadapanandal / Viluppuram
UPDATE customer SET village = 'Kadapanandal', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kadapanandal', 'KADAPANANTHAL', 'KADAPPANANTHAL', 'Kadapananthal', 'Kadappananthal');

-- 43 customers  AANDAPATTU x29, ANDAPATTU x13, ANNDAPATTU x1  →  Andapattu / Viluppuram
UPDATE customer SET village = 'Andapattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Andapattu', 'AANDAPATTU', 'ANDAPATTU', 'ANNDAPATTU', 'Aandapattu', 'Anndapattu');

-- 42 customers  MELMALAYANUR x22, MELMALAIYANUR x20  →  Melmaliyanur / Viluppuram
UPDATE customer SET village = 'Melmaliyanur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Melmaliyanur', 'MELMALAYANUR', 'MELMALAIYANUR', 'Melmalaiyanur', 'Melmalayanur');

-- 38 customers  EYAKUNAM x33, EAYAKUNAM x4, IYAKUNAM x1  →  Eayakunam / Viluppuram
UPDATE customer SET village = 'Eayakunam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Eayakunam', 'EYAKUNAM', 'EAYAKUNAM', 'IYAKUNAM', 'Eyakunam', 'Iyakunam');

-- 36 customers  KAMALAPUTHUR x36  →  Kamalaputhur / Tiruvannamalai
UPDATE customer SET village = 'Kamalaputhur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kamalaputhur', 'KAMALAPUTHUR');

-- 33 customers  KOTHANTHAVADI x33  →  Kothanthavadi / Tiruvannamalai
UPDATE customer SET village = 'Kothanthavadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kothanthavadi', 'KOTHANTHAVADI');

-- 32 customers  CHIRUTHALAIPUNDI x25, SIRUTHALAIPOONDI x7  →  Siruthlaipoondi / Viluppuram
UPDATE customer SET village = 'Siruthlaipoondi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Siruthlaipoondi', 'CHIRUTHALAIPUNDI', 'SIRUTHALAIPOONDI', 'Chiruthalaipundi', 'Siruthalaipoondi');

-- 30 customers  KANALAPADI x30  →  Ganalapadi / Tiruvannamalai
UPDATE customer SET village = 'Ganalapadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ganalapadi', 'KANALAPADI', 'Kanalapadi');

-- 29 customers  ANANTHAPURAM x27, ANANDHAPURAM x2  →  Ananthapuram / Tiruvannamalai
UPDATE customer SET village = 'Ananthapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ananthapuram', 'ANANTHAPURAM', 'ANANDHAPURAM', 'Anandhapuram');

-- 22 customers  VALATHI x22  →  Valathi / Viluppuram
UPDATE customer SET village = 'Valathi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Valathi', 'VALATHI');

-- 18 customers  MALLAVADI x18  →  Mallavadi / Tiruvannamalai
UPDATE customer SET village = 'Mallavadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mallavadi', 'MALLAVADI');

-- 16 customers  KONALUR x15, KONALOOR x1  →  Konalur / Tiruvannamalai
UPDATE customer SET village = 'Konalur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Konalur', 'KONALUR', 'KONALOOR', 'Konaloor');

-- 15 customers  NOCHIMALAI x15  →  Nochimalai / Tiruvannamalai
UPDATE customer SET village = 'Nochimalai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nochimalai', 'NOCHIMALAI');

-- 14 customers  PORKUNAM x13, PORKKUNAM x1  →  Porkunam / Tiruvannamalai
UPDATE customer SET village = 'Porkunam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Porkunam', 'PORKUNAM', 'PORKKUNAM', 'Porkkunam');

-- 13 customers  ARANJI x12, ARRANJI x1  →  Aranji / Tiruvannamalai
UPDATE customer SET village = 'Aranji', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Aranji', 'ARANJI', 'ARRANJI', 'Arranji');

-- 13 customers  KOLAPPALUR x11, KOLLAPPALUR x1, KOLAPALUR x1  →  Kolappalur / Tiruvannamalai
UPDATE customer SET village = 'Kolappalur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kolappalur', 'KOLAPPALUR', 'KOLAPALUR', 'KOLLAPPALUR', 'Kolapalur', 'Kollappalur');

-- 13 customers  MELSEVALAMPADI x12, MEL SEVALAMPADI x1  →  Melsevalampadi / Viluppuram
UPDATE customer SET village = 'Melsevalampadi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Melsevalampadi', 'MELSEVALAMPADI', 'MEL SEVALAMPADI', 'Mel Sevalampadi');

-- 13 customers  SOMASIPADI x13  →  Somasipadi / Tiruvannamalai
UPDATE customer SET village = 'Somasipadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Somasipadi', 'SOMASIPADI');

-- 13 customers  VENGIKKAL x11, VENGIKAL x2  →  Vengikkal / Tiruvannamalai
UPDATE customer SET village = 'Vengikkal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vengikkal', 'VENGIKKAL', 'VENGIKAL', 'Vengikal');

-- 12 customers  KARKONAM x11, KARKONAM ,MANGALAM x1  →  Karkonam / Tiruvannamalai
UPDATE customer SET village = 'Karkonam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Karkonam', 'KARKONAM', 'KARKONAM ,MANGALAM', 'Karkonam ,Mangalam');

-- 12 customers  NALLANPILLAIPETRAL x9, NALLANPILLAI PETRAL x2, NALLAN PILLAI PETRAL x1  →  Nallanpillaipetral / Tiruvannamalai
UPDATE customer SET village = 'Nallanpillaipetral', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nallanpillaipetral', 'NALLANPILLAIPETRAL', 'NALLANPILLAI PETRAL', 'NALLAN PILLAI PETRAL', 'Nallan Pillai Petral', 'Nallanpillai Petral');

-- 11 customers  KANNAPANTHAL x5, KANNAPANANDHAL x3, KANNAPANDHAL x2, KANNAPPANTHAL x1  →  Kannapandal / Tiruvannamalai
UPDATE customer SET village = 'Kannapandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kannapandal', 'KANNAPANTHAL', 'KANNAPANANDHAL', 'KANNAPANDHAL', 'KANNAPPANTHAL', 'Kannapanandhal', 'Kannapandhal', 'Kannapanthal', 'Kannappanthal');

-- 10 customers  KILPALUR x9, KIL PALUR x1  →  Kilpalur / Tiruvannamalai
UPDATE customer SET village = 'Kilpalur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kilpalur', 'KILPALUR', 'KIL PALUR', 'Kil Palur');

-- 10 customers  KOLATHUR x10  →  Kolathur / Tiruvannamalai
UPDATE customer SET village = 'Kolathur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kolathur', 'KOLATHUR');

-- 10 customers  LADAVARAM x10  →  Ladavaram / Tiruvannamalai
UPDATE customer SET village = 'Ladavaram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ladavaram', 'LADAVARAM');

-- 10 customers  MATHALAMPADI x8, MADHALAMPADI x2  →  Madalampadi / Tiruvannamalai
UPDATE customer SET village = 'Madalampadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Madalampadi', 'MATHALAMPADI', 'MADHALAMPADI', 'Madhalampadi', 'Mathalampadi');

-- 10 customers  SORAKULATHUR x10  →  Sorakulathur / Tiruvannamalai
UPDATE customer SET village = 'Sorakulathur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sorakulathur', 'SORAKULATHUR');

-- 10 customers  THENMATHUR x10  →  Thenmathur / Tiruvannamalai
UPDATE customer SET village = 'Thenmathur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thenmathur', 'THENMATHUR');

-- 10 customers  THORAPADI x9, THORAPPADI x1  →  Thorapadi / Viluppuram
UPDATE customer SET village = 'Thorapadi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Thorapadi', 'THORAPADI', 'THORAPPADI', 'Thorappadi');

-- 9 customers  NAIDUMANGALAM x7, NAIDU MANGALAM x2  →  Naidumangalam / Tiruvannamalai
UPDATE customer SET village = 'Naidumangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Naidumangalam', 'NAIDUMANGALAM', 'NAIDU MANGALAM', 'Naidu Mangalam');

-- 9 customers  NARAYANAPURAM x9  →  Narayanapuram / Viluppuram
UPDATE customer SET village = 'Narayanapuram', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Narayanapuram', 'NARAYANAPURAM');

-- 8 customers  THEVANUR x6, DHEVANUR x2  →  Dhevanur / Viluppuram
UPDATE customer SET village = 'Dhevanur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Dhevanur', 'THEVANUR', 'DHEVANUR', 'Thevanur');

-- 8 customers  KILPATTU x8  →  Kilpattu / Tiruvannamalai
UPDATE customer SET village = 'Kilpattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kilpattu', 'KILPATTU');

-- 8 customers  VINAYAGAPURAM x8  →  Vinayagapuram / Tiruvannamalai
UPDATE customer SET village = 'Vinayagapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vinayagapuram', 'VINAYAGAPURAM');

-- 7 customers  ANIYALAI x7  →  Aniyalai / Tiruvannamalai
UPDATE customer SET village = 'Aniyalai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Aniyalai', 'ANIYALAI');

-- 7 customers  KOLAKUDI x6, KOLLAKUDI x1  →  Kolakudi / Tiruvannamalai
UPDATE customer SET village = 'Kolakudi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kolakudi', 'KOLAKUDI', 'KOLLAKUDI', 'Kollakudi');

-- 7 customers  KOVUR x7  →  Kovur / Tiruvannamalai
UPDATE customer SET village = 'Kovur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kovur', 'KOVUR');

-- 7 customers  MN PALAYAM x5, MNPALAYAM x1, M.N PALAYAM x1  →  M. N. Palayam / Tiruvannamalai
UPDATE customer SET village = 'M. N. Palayam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('M. N. Palayam', 'MN PALAYAM', 'M.N PALAYAM', 'MNPALAYAM', 'M.N Palayam', 'Mn Palayam', 'MN Palayam', 'Mnpalayam');

-- 7 customers  NARIYAMANGALAM x7  →  Nariyamangalam / Tiruvannamalai
UPDATE customer SET village = 'Nariyamangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nariyamangalam', 'NARIYAMANGALAM');

-- 7 customers  SEETAMBATTU x7  →  Seetambattu / Tiruvannamalai
UPDATE customer SET village = 'Seetambattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Seetambattu', 'SEETAMBATTU');

-- 6 customers  ADIANNAMALAI x6  →  Adiannamalai / Tiruvannamalai
UPDATE customer SET village = 'Adiannamalai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Adiannamalai', 'ADIANNAMALAI');

-- 6 customers  KALASAPAKKAM x6  →  Kalasapakkam / Tiruvannamalai
UPDATE customer SET village = 'Kalasapakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kalasapakkam', 'KALASAPAKKAM');

-- 6 customers  KALLANTHAL x5, KALANTHAL x1  →  Kallandhal / Viluppuram
UPDATE customer SET village = 'Kallandhal', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kallandhal', 'KALLANTHAL', 'KALANTHAL', 'Kalanthal', 'Kallanthal');

-- 6 customers  KAMPATTU x6  →  Kampattu / Tiruvannamalai
UPDATE customer SET village = 'Kampattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kampattu', 'KAMPATTU');

-- 6 customers  KARIPUR x5, KARIPPUR x1  →  Karippur / Tiruvannamalai
UPDATE customer SET village = 'Karippur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Karippur', 'KARIPUR', 'KARIPPUR', 'Karipur');

-- 5 customers  ARASAMPATTU x5  →  Arasampattu / Kallakurichi
UPDATE customer SET village = 'Arasampattu', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Arasampattu', 'ARASAMPATTU');

-- 5 customers  ATHIYANTHAL x5  →  Athiyanthal / Kallakurichi
UPDATE customer SET village = 'Athiyanthal', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Athiyanthal', 'ATHIYANTHAL');

-- 5 customers  CHETPET x5  →  Chetpet / Tiruvannamalai
UPDATE customer SET village = 'Chetpet', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Chetpet', 'CHETPET');

-- 5 customers  DEVANUR x5  →  Devanur / Tiruvannamalai
UPDATE customer SET village = 'Devanur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Devanur', 'DEVANUR');

-- 5 customers  KANDAMANALUR x2, KANDAMANALLUR x2, KANDAMANALLUR,VILLUPUREM x1  →  Kandamanallur / Viluppuram
UPDATE customer SET village = 'Kandamanallur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kandamanallur', 'KANDAMANALLUR', 'KANDAMANALUR', 'KANDAMANALLUR,VILLUPUREM', 'Kandamanallur,Villupurem', 'Kandamanalur');

-- 5 customers  KANNALAM x5  →  Kannalam / Viluppuram
UPDATE customer SET village = 'Kannalam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kannalam', 'KANNALAM');

-- 5 customers  NARANAMANGALAM x5  →  Naranamangalam / Viluppuram
UPDATE customer SET village = 'Naranamangalam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Naranamangalam', 'NARANAMANGALAM');

-- 5 customers  PALIYAPATTU x5  →  Paliyapattu / Tiruvannamalai
UPDATE customer SET village = 'Paliyapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Paliyapattu', 'PALIYAPATTU');

-- 5 customers  PALLIYAMPATTU x5  →  Palliyampattu / Viluppuram
UPDATE customer SET village = 'Palliyampattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Palliyampattu', 'PALLIYAMPATTU');

-- 5 customers  PELASUR x5  →  Pelasur / Tiruvannamalai
UPDATE customer SET village = 'Pelasur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Pelasur', 'PELASUR');

-- 5 customers  THADAGAM x5  →  Thadagam / Viluppuram
UPDATE customer SET village = 'Thadagam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Thadagam', 'THADAGAM');

-- 5 customers  THANDRAMPATTU x5  →  Thandrampattu / Tiruvannamalai
UPDATE customer SET village = 'Thandrampattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thandrampattu', 'THANDRAMPATTU');

-- 4 customers  ATHURAI x4  →  Athurai / Tiruvannamalai
UPDATE customer SET village = 'Athurai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Athurai', 'ATHURAI');

-- 4 customers  KARAPATTU x4  →  Karapattu / Viluppuram
UPDATE customer SET village = 'Karapattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Karapattu', 'KARAPATTU');

-- 4 customers  SEELAPANTHAL x2, SEELAPANDHAL x1, SEELAPANDAL x1  →  Seelappandal / Tiruvannamalai
UPDATE customer SET village = 'Seelappandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Seelappandal', 'SEELAPANTHAL', 'SEELAPANDAL', 'SEELAPANDHAL', 'Seelapandal', 'Seelapandhal', 'Seelapanthal');

-- 4 customers  SINGAVARAM x4  →  Singavaram / Viluppuram
UPDATE customer SET village = 'Singavaram', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Singavaram', 'SINGAVARAM');

-- 4 customers  SIRUNATHUR x4  →  Sirunathur / Tiruvannamalai
UPDATE customer SET village = 'Sirunathur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sirunathur', 'SIRUNATHUR');

-- 4 customers  VADAPALAI x4  →  Vadapalai / Viluppuram
UPDATE customer SET village = 'Vadapalai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Vadapalai', 'VADAPALAI');

-- 4 customers  VANAPURAM x4  →  Vanapuram / Tiruvannamalai
UPDATE customer SET village = 'Vanapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vanapuram', 'VANAPURAM');

-- 4 customers  VELANANDHAL x3, VELANTHAL x1  →  Velanandhal / Kallakurichi
UPDATE customer SET village = 'Velanandhal', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Velanandhal', 'VELANANDHAL', 'VELANTHAL', 'Velanthal');

-- 3 customers  ALAGANANTHAL x3  →  Alaganandal / Tiruvannamalai
UPDATE customer SET village = 'Alaganandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Alaganandal', 'ALAGANANTHAL', 'Alagananthal');

-- 3 customers  DEVANAMPATTU x3  →  Devanampattu / Tiruvannamalai
UPDATE customer SET village = 'Devanampattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Devanampattu', 'DEVANAMPATTU');

-- 3 customers  DEVANANTHAL x2, DEVANANDAL x1  →  Devanandal / Tiruvannamalai
UPDATE customer SET village = 'Devanandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Devanandal', 'DEVANANTHAL', 'DEVANANDAL', 'Devananthal');

-- 3 customers  ENDAL x2, ENTHAL x1  →  Endal / Tiruvannamalai
UPDATE customer SET village = 'Endal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Endal', 'ENDAL', 'ENTHAL', 'Enthal');

-- 3 customers  GENGAVARAM x3  →  Gengavaram / Tiruvannamalai
UPDATE customer SET village = 'Gengavaram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Gengavaram', 'GENGAVARAM');

-- 3 customers  KAMAGARAM x3  →  Kamagaram / Viluppuram
UPDATE customer SET village = 'Kamagaram', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kamagaram', 'KAMAGARAM');

-- 3 customers  KANJI x3  →  Kanji / Tiruvannamalai
UPDATE customer SET village = 'Kanji', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kanji', 'KANJI');

-- 3 customers  KARUNTHUVAMBADI x3  →  Karunthuvambadi / Tiruvannamalai
UPDATE customer SET village = 'Karunthuvambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Karunthuvambadi', 'KARUNTHUVAMBADI');

-- 3 customers  KILKACHIRAPATTU x3  →  Kilkachirapattu / Tiruvannamalai
UPDATE customer SET village = 'Kilkachirapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kilkachirapattu', 'KILKACHIRAPATTU');

-- 3 customers  KUPPAM x3  →  Kuppam / Tiruvannamalai
UPDATE customer SET village = 'Kuppam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kuppam', 'KUPPAM');

-- 3 customers  MAMBATTU x3  →  Mambattu / Tiruvannamalai
UPDATE customer SET village = 'Mambattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mambattu', 'MAMBATTU');

-- 3 customers  MANDAKOLATHUR x3  →  Mandakolathur / Tiruvannamalai
UPDATE customer SET village = 'Mandakolathur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mandakolathur', 'MANDAKOLATHUR');

-- 3 customers  MATTAVETTU x3  →  Mattavettu / Tiruvannamalai
UPDATE customer SET village = 'Mattavettu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mattavettu', 'MATTAVETTU');

-- 3 customers  MEYYUR x3  →  Meyyur / Tiruvannamalai
UPDATE customer SET village = 'Meyyur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Meyyur', 'MEYYUR');

-- 3 customers  NADUPATTU x3  →  Nadupattu / Tiruvannamalai
UPDATE customer SET village = 'Nadupattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nadupattu', 'NADUPATTU');

-- 3 customers  PANDITHAPATTU x3  →  Pandithapattu / Tiruvannamalai
UPDATE customer SET village = 'Pandithapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Pandithapattu', 'PANDITHAPATTU');

-- 3 customers  PUTHUPATTU x3  →  Pudupattu / Tiruvannamalai
UPDATE customer SET village = 'Pudupattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Pudupattu', 'PUTHUPATTU', 'Puthupattu');

-- 3 customers  THENPALAI x3  →  Thenpalai / Viluppuram
UPDATE customer SET village = 'Thenpalai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Thenpalai', 'THENPALAI');

-- 3 customers  VADAMATHUR x3  →  Vadamathur / Tiruvannamalai
UPDATE customer SET village = 'Vadamathur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vadamathur', 'VADAMATHUR');

-- 2 customers  AGARAM x2  →  Agaram / Tiruvannamalai
UPDATE customer SET village = 'Agaram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Agaram', 'AGARAM');

-- 2 customers  ALANGARAMANGALAM x2  →  Alangaramangalam / Tiruvannamalai
UPDATE customer SET village = 'Alangaramangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Alangaramangalam', 'ALANGARAMANGALAM');

-- 2 customers  CHINNAKOLAPADI x2  →  Chinnakolapadi / Tiruvannamalai
UPDATE customer SET village = 'Chinnakolapadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Chinnakolapadi', 'CHINNAKOLAPADI');

-- 2 customers  KADAMBAI x2  →  Kadambai / Tiruvannamalai
UPDATE customer SET village = 'Kadambai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kadambai', 'KADAMBAI');

-- 2 customers  KALPUNDI x2  →  Kalpoondi / Tiruvannamalai
UPDATE customer SET village = 'Kalpoondi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kalpoondi', 'KALPUNDI', 'Kalpundi');

-- 2 customers  KUDUKKANKUPPAM x1, KUDUKKAN KUPPAM x1  →  Kudukankuppam / Viluppuram
UPDATE customer SET village = 'Kudukankuppam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kudukankuppam', 'KUDUKKAN KUPPAM', 'KUDUKKANKUPPAM', 'Kudukkan Kuppam', 'Kudukkankuppam');

-- 2 customers  MATHAPUNDI x2  →  Madhapoondi / Viluppuram
UPDATE customer SET village = 'Madhapoondi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Madhapoondi', 'MATHAPUNDI', 'Mathapundi');

-- 2 customers  MARUTHUVAMBADI x2  →  Maruthuvambadi / Tiruvannamalai
UPDATE customer SET village = 'Maruthuvambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Maruthuvambadi', 'MARUTHUVAMBADI');

-- 2 customers  MASHAR x2  →  Mashar / Tiruvannamalai
UPDATE customer SET village = 'Mashar', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mashar', 'MASHAR');

-- 2 customers  MELPALUR x2  →  Melpalur / Tiruvannamalai
UPDATE customer SET village = 'Melpalur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Melpalur', 'MELPALUR');

-- 2 customers  NALLAVANPALAYAM x2  →  Nallavanpalayam / Tiruvannamalai
UPDATE customer SET village = 'Nallavanpalayam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nallavanpalayam', 'NALLAVANPALAYAM');

-- 2 customers  PAKKAM x2  →  Pakkam / Viluppuram
UPDATE customer SET village = 'Pakkam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Pakkam', 'PAKKAM');

-- 2 customers  PALIPATTU x2  →  Pallipattu / Kallakurichi
UPDATE customer SET village = 'Pallipattu', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Pallipattu', 'PALIPATTU', 'Palipattu');

-- 2 customers  PARUTHIPURAM x2  →  Paruthipuram / Viluppuram
UPDATE customer SET village = 'Paruthipuram', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Paruthipuram', 'PARUTHIPURAM');

-- 2 customers  PERIYANOLAMBAI x1, PERIYA NOLAMBAI x1  →  Periyanolambai / Viluppuram
UPDATE customer SET village = 'Periyanolambai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Periyanolambai', 'PERIYA NOLAMBAI', 'PERIYANOLAMBAI', 'Periya Nolambai');

-- 2 customers  PERUMBAKKAM x2  →  Perumbakkam / Tiruvannamalai
UPDATE customer SET village = 'Perumbakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Perumbakkam', 'PERUMBAKKAM');

-- 2 customers  PUTHUPALAYAM x2  →  Pudupalayam / Tiruvannamalai
UPDATE customer SET village = 'Pudupalayam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Pudupalayam', 'PUTHUPALAYAM', 'Puthupalayam');

-- 2 customers  POOTHAMANGALAM x2  →  Puthamangalam / Kallakurichi
UPDATE customer SET village = 'Puthamangalam', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Puthamangalam', 'POOTHAMANGALAM', 'Poothamangalam');

-- 2 customers  SEMMEDU x2  →  Semmedu / Viluppuram
UPDATE customer SET village = 'Semmedu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Semmedu', 'SEMMEDU');

-- 2 customers  SIRUPAKKAM x1, SIRUPPAKKAM x1  →  Sirupakkam / Kallakurichi
UPDATE customer SET village = 'Sirupakkam', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Sirupakkam', 'SIRUPAKKAM', 'SIRUPPAKKAM', 'Siruppakkam');

-- 2 customers  THACHAMPATTU x2  →  Thachampattu / Viluppuram
UPDATE customer SET village = 'Thachampattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Thachampattu', 'THACHAMPATTU');

-- 2 customers  THANIPADI x2  →  Thanipadi / Tiruvannamalai
UPDATE customer SET village = 'Thanipadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thanipadi', 'THANIPADI');

-- 2 customers  VILAPAKKAM x2  →  Vilapakkam / Tiruvannamalai
UPDATE customer SET village = 'Vilapakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vilapakkam', 'VILAPAKKAM');

-- 1 customers  AATHIPAKKAM x1  →  A. Athipakkam / Kallakurichi
UPDATE customer SET village = 'A. Athipakkam', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('A. Athipakkam', 'AATHIPAKKAM', 'Aathipakkam');

-- 1 customers  AMARNATHAPUTHUR x1  →  Amarnathapudur / Tiruvannamalai
UPDATE customer SET village = 'Amarnathapudur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Amarnathapudur', 'AMARNATHAPUTHUR', 'Amarnathaputhur');

-- 1 customers  ARIYAPADI x1  →  Ariyapadi / Tiruvannamalai
UPDATE customer SET village = 'Ariyapadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ariyapadi', 'ARIYAPADI');

-- 1 customers  ARUMBAKKAM x1  →  Arumbakkam / Tiruvannamalai
UPDATE customer SET village = 'Arumbakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Arumbakkam', 'ARUMBAKKAM');

-- 1 customers  ARUNGUNAM x1  →  Arungunam / Tiruvannamalai
UPDATE customer SET village = 'Arungunam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Arungunam', 'ARUNGUNAM');

-- 1 customers  C.NAMINTHAL x1  →  C.Nammiyandal / Tiruvannamalai
UPDATE customer SET village = 'C.Nammiyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('C.Nammiyandal', 'C.NAMINTHAL', 'C.Naminthal');

-- 1 customers  CHELLANKUPPAM x1  →  Chellankuppam / Tiruvannamalai
UPDATE customer SET village = 'Chellankuppam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Chellankuppam', 'CHELLANKUPPAM');

-- 1 customers  DEVATHANAMPETTAI x1  →  Devathanampettai / Viluppuram
UPDATE customer SET village = 'Devathanampettai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Devathanampettai', 'DEVATHANAMPETTAI');

-- 1 customers  DEVIKAPURAM x1  →  Devikapuram / Tiruvannamalai
UPDATE customer SET village = 'Devikapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Devikapuram', 'DEVIKAPURAM');

-- 1 customers  DEVANTHAVADI x1  →  Dhevanthavadi / Viluppuram
UPDATE customer SET village = 'Dhevanthavadi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Dhevanthavadi', 'DEVANTHAVADI', 'Devanthavadi');

-- 1 customers  ELUVAMBADI x1  →  Eluvambadi / Tiruvannamalai
UPDATE customer SET village = 'Eluvambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Eluvambadi', 'ELUVAMBADI');

-- 1 customers  GANAPAPURAM x1  →  Ganapapuram / Tiruvannamalai
UPDATE customer SET village = 'Ganapapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ganapapuram', 'GANAPAPURAM');

-- 1 customers  JAPTHIKARIYANTHAL x1  →  Japthikariyandal / Tiruvannamalai
UPDATE customer SET village = 'Japthikariyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Japthikariyandal', 'JAPTHIKARIYANTHAL', 'Japthikariyanthal');

-- 1 customers  KALATHAMPATTU x1  →  Kalathampattu / Viluppuram
UPDATE customer SET village = 'Kalathampattu', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kalathampattu', 'KALATHAMPATTU');

-- 1 customers  KALLARAIPADI x1  →  Kallaraipadi / Tiruvannamalai
UPDATE customer SET village = 'Kallaraipadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kallaraipadi', 'KALLARAIPADI');

-- 1 customers  KARAI x1  →  Karai / Viluppuram
UPDATE customer SET village = 'Karai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Karai', 'KARAI');

-- 1 customers  KARIYANTHAL x1  →  Kariyandal / Tiruvannamalai
UPDATE customer SET village = 'Kariyandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kariyandal', 'KARIYANTHAL', 'Kariyanthal');

-- 1 customers  KATTUMALAIYANUR x1  →  Kattumalaiyanur / Tiruvannamalai
UPDATE customer SET village = 'Kattumalaiyanur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kattumalaiyanur', 'KATTUMALAIYANUR');

-- 1 customers  KELLUR x1  →  Kelur / Tiruvannamalai
UPDATE customer SET village = 'Kelur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kelur', 'KELLUR', 'Kellur');

-- 1 customers  KIL CHETTIPATTU x1  →  Kilchettipattu / Tiruvannamalai
UPDATE customer SET village = 'Kilchettipattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kilchettipattu', 'KIL CHETTIPATTU', 'Kil Chettipattu');

-- 1 customers  KILLNAGAR x1  →  Kilnagar / Tiruvannamalai
UPDATE customer SET village = 'Kilnagar', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kilnagar', 'KILLNAGAR', 'Killnagar');

-- 1 customers  KOLAMANJANUR x1  →  Kolamanjanur / Tiruvannamalai
UPDATE customer SET village = 'Kolamanjanur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kolamanjanur', 'KOLAMANJANUR');

-- 1 customers  KOTTUPAKKAM x1  →  Kottupakkam / Tiruvannamalai
UPDATE customer SET village = 'Kottupakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kottupakkam', 'KOTTUPAKKAM');

-- 1 customers  MATHAMPOONDI x1  →  Madampoondi / Kallakurichi
UPDATE customer SET village = 'Madampoondi', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Madampoondi', 'MATHAMPOONDI', 'Mathampoondi');

-- 1 customers  MADURAI x1  →  Madhurai / Tiruvannamalai
UPDATE customer SET village = 'Madhurai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Madhurai', 'MADURAI', 'Madurai');

-- 1 customers  MATHURAMPATTU x1  →  Madurampattu / Tiruvannamalai
UPDATE customer SET village = 'Madurampattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Madurampattu', 'MATHURAMPATTU', 'Mathurampattu');

-- 1 customers  MAHADEVIMANGALAM x1  →  Mahadevimangalam / Tiruvannamalai
UPDATE customer SET village = 'Mahadevimangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mahadevimangalam', 'MAHADEVIMANGALAM');

-- 1 customers  MALAPAMBADI x1  →  Malappambadi / Tiruvannamalai
UPDATE customer SET village = 'Malappambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Malappambadi', 'MALAPAMBADI', 'Malapambadi');

-- 1 customers  MANMALAI x1  →  Manmalai / Tiruvannamalai
UPDATE customer SET village = 'Manmalai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Manmalai', 'MANMALAI');

-- 1 customers  MANSURABAD x1  →  Mansurabad / Tiruvannamalai
UPDATE customer SET village = 'Mansurabad', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mansurabad', 'MANSURABAD');

-- 1 customers  MATTA PIRAIYUR x1  →  Mattapiraiyur / Tiruvannamalai
UPDATE customer SET village = 'Mattapiraiyur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mattapiraiyur', 'MATTA PIRAIYUR', 'Matta Piraiyur');

-- 1 customers  MELATHANGAL x1  →  Melathangal / Tiruvannamalai
UPDATE customer SET village = 'Melathangal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Melathangal', 'MELATHANGAL');

-- 1 customers  MEL NACHIPATTU x1  →  Melnachippattu / Tiruvannamalai
UPDATE customer SET village = 'Melnachippattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Melnachippattu', 'MEL NACHIPATTU', 'Mel Nachipattu');

-- 1 customers  MELNEMILI x1  →  Melnemili / Viluppuram
UPDATE customer SET village = 'Melnemili', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Melnemili', 'MELNEMILI');

-- 1 customers  NACHANANTHAL x1  →  Nachanandal / Tiruvannamalai
UPDATE customer SET village = 'Nachanandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nachanandal', 'NACHANANTHAL', 'Nachananthal');

-- 1 customers  NADALAGANATHAL x1  →  Nadalaganadal / Tiruvannamalai
UPDATE customer SET village = 'Nadalaganadal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nadalaganadal', 'NADALAGANATHAL', 'Nadalaganathal');

-- 1 customers  NAGAPADI x1  →  Nagapadi / Tiruvannamalai
UPDATE customer SET village = 'Nagapadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nagapadi', 'NAGAPADI');

-- 1 customers  THEAGI ANNAMALAI,NAGAR x1  →  Nagar / Viluppuram
UPDATE customer SET village = 'Nagar', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Nagar', 'THEAGI ANNAMALAI,NAGAR', 'Theagi Annamalai,Nagar');

-- 1 customers  NARASINGANALLUR x1  →  Narasinganallur / Tiruvannamalai
UPDATE customer SET village = 'Narasinganallur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Narasinganallur', 'NARASINGANALLUR');

-- 1 customers  NARAYANAMANGALAM x1  →  Narayanamangalam / Tiruvannamalai
UPDATE customer SET village = 'Narayanamangalam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Narayanamangalam', 'NARAYANAMANGALAM');

-- 1 customers  NEDUNGAVADI x1  →  Nedungavadi / Tiruvannamalai
UPDATE customer SET village = 'Nedungavadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Nedungavadi', 'NEDUNGAVADI');

-- 1 customers  PACHAL x1  →  Pachal / Tiruvannamalai
UPDATE customer SET village = 'Pachal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Pachal', 'PACHAL');

-- 1 customers  PADUR x1  →  Padur / Tiruvannamalai
UPDATE customer SET village = 'Padur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Padur', 'PADUR');

-- 1 customers  PERIYA KALLAPADI x1  →  Periyakallapadi / Tiruvannamalai
UPDATE customer SET village = 'Periyakallapadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Periyakallapadi', 'PERIYA KALLAPADI', 'Periya Kallapadi');

-- 1 customers  PERIYA KOLAPADI x1  →  Periyakolapadi / Tiruvannamalai
UPDATE customer SET village = 'Periyakolapadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Periyakolapadi', 'PERIYA KOLAPADI', 'Periya Kolapadi');

-- 1 customers  PERUMPAKKAM x1  →  Perumpakkam / Viluppuram
UPDATE customer SET village = 'Perumpakkam', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Perumpakkam', 'PERUMPAKKAM');

-- 1 customers  PERUVALUR x1  →  Peruvalur / Viluppuram
UPDATE customer SET village = 'Peruvalur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Peruvalur', 'PERUVALUR');

-- 1 customers  .POONDI x1  →  Poondi / Tiruvannamalai
UPDATE customer SET village = 'Poondi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Poondi', '.POONDI', '.Poondi');

-- 1 customers  POTHUVAI x1  →  Pothuvai / Viluppuram
UPDATE customer SET village = 'Pothuvai', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Pothuvai', 'POTHUVAI');

-- 1 customers  PUDHUR CHEKKADI x1  →  Pudur Chekkadi / Tiruvannamalai
UPDATE customer SET village = 'Pudur Chekkadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Pudur Chekkadi', 'PUDHUR CHEKKADI', 'Pudhur Chekkadi');

-- 1 customers  PUTHAGARAM x1  →  Puthagaram / Viluppuram
UPDATE customer SET village = 'Puthagaram', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Puthagaram', 'PUTHAGARAM');

-- 1 customers  RAYAMPETTAI x1  →  Rayampettai / Tiruvannamalai
UPDATE customer SET village = 'Rayampettai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Rayampettai', 'RAYAMPETTAI');

-- 1 customers  SALAIYANUR x1  →  Salaiyanur / Tiruvannamalai
UPDATE customer SET village = 'Salaiyanur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Salaiyanur', 'SALAIYANUR');

-- 1 customers  SANIPUNDI x1  →  Sanipoondi / Tiruvannamalai
UPDATE customer SET village = 'Sanipoondi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sanipoondi', 'SANIPUNDI', 'Sanipundi');

-- 1 customers  SANTHAVASAL x1  →  Santhavasal / Tiruvannamalai
UPDATE customer SET village = 'Santhavasal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Santhavasal', 'SANTHAVASAL');

-- 1 customers  SATHANANTHAL x1  →  Sathanandal / Viluppuram
UPDATE customer SET village = 'Sathanandal', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Sathanandal', 'SATHANANTHAL', 'Sathananthal');

-- 1 customers  SATHANUR x1  →  Sathanur / Viluppuram
UPDATE customer SET village = 'Sathanur', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Sathanur', 'SATHANUR');

-- 1 customers  SUTHAMALAI x1  →  Suthamalai / Kallakurichi
UPDATE customer SET village = 'Suthamalai', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Suthamalai', 'SUTHAMALAI');

-- 1 customers  THALAYAMPALLAM x1  →  Thalayampallam / Tiruvannamalai
UPDATE customer SET village = 'Thalayampallam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thalayampallam', 'THALAYAMPALLAM');

-- 1 customers  THAMARAIPAKKAM x1  →  Thamaraipakkam / Tiruvannamalai
UPDATE customer SET village = 'Thamaraipakkam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thamaraipakkam', 'THAMARAIPAKKAM');

-- 1 customers  THELLAR x1  →  Thellar / Tiruvannamalai
UPDATE customer SET village = 'Thellar', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thellar', 'THELLAR');

-- 1 customers  THENMUDIYANUR x1  →  Thenmudiyanoor / Tiruvannamalai
UPDATE customer SET village = 'Thenmudiyanoor', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thenmudiyanoor', 'THENMUDIYANUR', 'Thenmudiyanur');

-- 1 customers  THOTAPPADI x1  →  Thottapadi / Kallakurichi
UPDATE customer SET village = 'Thottapadi', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Thottapadi', 'THOTAPPADI', 'Thotappadi');

-- 1 customers  UDAYANTHAL x1  →  Udayandal / Tiruvannamalai
UPDATE customer SET village = 'Udayandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Udayandal', 'UDAYANTHAL', 'Udayanthal');

-- 1 customers  UTHIRAMPUNDI x1  →  Uthirampoondi / Tiruvannamalai
UPDATE customer SET village = 'Uthirampoondi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Uthirampoondi', 'UTHIRAMPUNDI', 'Uthirampundi');

-- 1 customers  VANAMPATTU x1  →  Vanampattu / Kallakurichi
UPDATE customer SET village = 'Vanampattu', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Vanampattu', 'VANAMPATTU');

-- 1 customers  VARAGUR x1  →  Varagur / Kallakurichi
UPDATE customer SET village = 'Varagur', district = 'Kallakurichi' WHERE organization_id = 1 AND village IN ('Varagur', 'VARAGUR');

-- 1 customers  VEDANATHAM x1  →  Vedanatham / Tiruvannamalai
UPDATE customer SET village = 'Vedanatham', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vedanatham', 'VEDANATHAM');

-- 1 customers  VELANANTHAL x1  →  Velanandal / Tiruvannamalai
UPDATE customer SET village = 'Velanandal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Velanandal', 'VELANANTHAL', 'Velananthal');

-- ---------------------------------------------------------------------------
-- B) Habitations that are not LGD village panchayats (normalized local names)
--    Add them to config so POS district→village dropdowns still work.
-- ---------------------------------------------------------------------------

-- 447 customers  →  Mathulambadi / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'mathulambadi', 'Mathulambadi', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='mathulambadi' OR c.name='Mathulambadi')
);

-- 439 customers  →  Thayakunam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'thayakunam', 'Thayakunam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='thayakunam' OR c.name='Thayakunam')
);

-- 248 customers  →  Thathankuppam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'thathankuppam', 'Thathankuppam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='thathankuppam' OR c.name='Thathankuppam')
);

-- 218 customers  →  Mansurapath / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'mansurapath', 'Mansurapath', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='mansurapath' OR c.name='Mansurapath')
);

-- 186 customers  →  Kunnumurinji / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'kunnumurinji', 'Kunnumurinji', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='kunnumurinji' OR c.name='Kunnumurinji')
);

-- 179 customers  →  Koothalavadi / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'koothalavadi', 'Koothalavadi', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='koothalavadi' OR c.name='Koothalavadi')
);

-- 150 customers  →  Poiyananthal / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'poiyananthal', 'Poiyananthal', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='poiyananthal' OR c.name='Poiyananthal')
);

-- 146 customers  →  Thoppu / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'thoppu', 'Thoppu', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='thoppu' OR c.name='Thoppu')
);

-- 104 customers  →  Selvapuram / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'selvapuram', 'Selvapuram', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='selvapuram' OR c.name='Selvapuram')
);

-- 102 customers  →  V.P. Kuppam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'v-p-kuppam', 'V.P. Kuppam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='v-p-kuppam' OR c.name='V.P. Kuppam')
);

-- 101 customers  →  M. Puthur / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'm-puthur', 'M. Puthur', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='m-puthur' OR c.name='M. Puthur')
);

-- 97 customers  →  Mayankulam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'mayankulam', 'Mayankulam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='mayankulam' OR c.name='Mayankulam')
);

-- 94 customers  →  Ravanapattu / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'ravanapattu', 'Ravanapattu', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='ravanapattu' OR c.name='Ravanapattu')
);

-- 75 customers  →  Maniyanthapattu / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'maniyanthapattu', 'Maniyanthapattu', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='maniyanthapattu' OR c.name='Maniyanthapattu')
);

-- 63 customers  →  Vaniyamthangal / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'vaniyamthangal', 'Vaniyamthangal', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='vaniyamthangal' OR c.name='Vaniyamthangal')
);

-- 61 customers  →  Tiruvannamalai / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'tiruvannamalai', 'Tiruvannamalai', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='tiruvannamalai' OR c.name='Tiruvannamalai')
);

-- 51 customers  →  Mannapatti / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'mannapatti', 'Mannapatti', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='mannapatti' OR c.name='Mannapatti')
);

-- 50 customers  →  Kalarpalayam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'kalarpalayam', 'Kalarpalayam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='kalarpalayam' OR c.name='Kalarpalayam')
);

-- 46 customers  →  V. Naminthal / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'v-naminthal', 'V. Naminthal', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='v-naminthal' OR c.name='V. Naminthal')
);

-- 45 customers  →  Melmampattu / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'melmampattu', 'Melmampattu', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='melmampattu' OR c.name='Melmampattu')
);

-- 45 customers  →  Ramanathapuram / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'ramanathapuram', 'Ramanathapuram', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='ramanathapuram' OR c.name='Ramanathapuram')
);

-- 43 customers  →  Mattaparai / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'mattaparai', 'Mattaparai', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='mattaparai' OR c.name='Mattaparai')
);

-- 41 customers  →  Sekkadikuppam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'sekkadikuppam', 'Sekkadikuppam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='sekkadikuppam' OR c.name='Sekkadikuppam')
);

-- 37 customers  →  Chatram / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'chatram', 'Chatram', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='chatram' OR c.name='Chatram')
);

-- 36 customers  →  Kodapundi / Viluppuram  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_viluppuram, 'kodapundi', 'Kodapundi', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_viluppuram AND (c.code='kodapundi' OR c.name='Kodapundi')
);

-- 35 customers  →  Kattukulam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'kattukulam', 'Kattukulam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='kattukulam' OR c.name='Kattukulam')
);

-- 35 customers  →  Thellananthal / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'thellananthal', 'Thellananthal', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='thellananthal' OR c.name='Thellananthal')
);

-- 35 customers  →  Koragathangal / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'koragathangal', 'Koragathangal', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='koragathangal' OR c.name='Koragathangal')
);

-- 33 customers  →  Ammankalodai / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'ammankalodai', 'Ammankalodai', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='ammankalodai' OR c.name='Ammankalodai')
);

-- 33 customers  →  Karapallam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'karapallam', 'Karapallam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='karapallam' OR c.name='Karapallam')
);

-- 27 customers  →  Ilavathadi / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'ilavathadi', 'Ilavathadi', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='ilavathadi' OR c.name='Ilavathadi')
);

-- 1 customers  →  Vaithanakunam / Tiruvannamalai  (not in LGD panchayat list)
INSERT INTO config_item (organization_id, kind, parent_id, code, name, extra, is_active, sort_order)
SELECT @org_id, 'village', @d_tiruvannamalai, 'vaithanakunam', 'Vaithanakunam', '{"source":"skac-legacy-habitation"}', 1, 9000
WHERE NOT EXISTS (
  SELECT 1 FROM config_item c WHERE c.organization_id=@org_id AND c.kind='village' AND c.is_deleted=0 AND c.parent_id=@d_tiruvannamalai AND (c.code='vaithanakunam' OR c.name='Vaithanakunam')
);

-- 447 customers  MATHULAMBADI x334, MATHULAMABADI x69, MATHULAMPADI x43, MATHULAMBADY x1  →  Mathulambadi / Tiruvannamalai
UPDATE customer SET village = 'Mathulambadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mathulambadi', 'MATHULAMBADI', 'MATHULAMABADI', 'MATHULAMPADI', 'MATHULAMBADY', 'Mathulamabadi', 'Mathulambady', 'Mathulampadi');

-- 439 customers  THAYAKUNAM x436, THAYANKUNAM x3  →  Thayakunam / Tiruvannamalai
UPDATE customer SET village = 'Thayakunam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thayakunam', 'THAYAKUNAM', 'THAYANKUNAM', 'Thayankunam');

-- 248 customers  T.KUPPAM x169, T.K x65, THATHANKUPPAM x12, T K x2  →  Thathankuppam / Tiruvannamalai
UPDATE customer SET village = 'Thathankuppam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thathankuppam', 'T.KUPPAM', 'T.K', 'THATHANKUPPAM', 'T K', 'T.Kuppam');

-- 218 customers  MANSURABATH x109, MANSURAPATH x109  →  Mansurapath / Tiruvannamalai
UPDATE customer SET village = 'Mansurapath', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mansurapath', 'MANSURABATH', 'MANSURAPATH', 'Mansurabath');

-- 186 customers  KUNNUMURINJI x129, KUNNUMURUNJI x56, KUNNUMURINJ x1  →  Kunnumurinji / Tiruvannamalai
UPDATE customer SET village = 'Kunnumurinji', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kunnumurinji', 'KUNNUMURINJI', 'KUNNUMURUNJI', 'KUNNUMURINJ', 'Kunnumurinj', 'Kunnumurunji');

-- 179 customers  KOOTHALAVADI x98, KUTHALAVADI x78, KUTHALAVADY x2, THAMARAI SELVAPUREM,KUTHALAVADI x1  →  Koothalavadi / Tiruvannamalai
UPDATE customer SET village = 'Koothalavadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Koothalavadi', 'KOOTHALAVADI', 'KUTHALAVADI', 'KUTHALAVADY', 'THAMARAI SELVAPUREM,KUTHALAVADI', 'Kuthalavadi', 'Kuthalavady', 'Thamarai Selvapurem,Kuthalavadi');

-- 150 customers  POIYANANTHAL x124, POIYANATHAL x22, POYANANTHAL x4  →  Poiyananthal / Tiruvannamalai
UPDATE customer SET village = 'Poiyananthal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Poiyananthal', 'POIYANANTHAL', 'POIYANATHAL', 'POYANANTHAL', 'Poiyanathal', 'Poyananthal');

-- 146 customers  THOPPU x146  →  Thoppu / Tiruvannamalai
UPDATE customer SET village = 'Thoppu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thoppu', 'THOPPU');

-- 104 customers  SELVAPURAM x64, SELVAPUREM x40  →  Selvapuram / Tiruvannamalai
UPDATE customer SET village = 'Selvapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Selvapuram', 'SELVAPURAM', 'SELVAPUREM', 'Selvapurem');

-- 102 customers  V.P.KUPPAM x99, V.P KUPPAM x3  →  V.P. Kuppam / Tiruvannamalai
UPDATE customer SET village = 'V.P. Kuppam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('V.P. Kuppam', 'V.P.KUPPAM', 'V.P KUPPAM', 'V.P Kuppam', 'V.P.Kuppam');

-- 101 customers  M PUDHUR x51, M.PUTHUR x35, M PUTHUR x9, M.PUDHUR x6  →  M. Puthur / Tiruvannamalai
UPDATE customer SET village = 'M. Puthur', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('M. Puthur', 'M PUDHUR', 'M.PUTHUR', 'M PUTHUR', 'M.PUDHUR', 'M Pudhur', 'M Puthur', 'M.Pudhur', 'M.Puthur');

-- 97 customers  MAYANKULAM x74, MAYAKULAM x23  →  Mayankulam / Tiruvannamalai
UPDATE customer SET village = 'Mayankulam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mayankulam', 'MAYANKULAM', 'MAYAKULAM', 'Mayakulam');

-- 94 customers  RAVANAPATTU x51, RAVANAMPATTU x43  →  Ravanapattu / Tiruvannamalai
UPDATE customer SET village = 'Ravanapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ravanapattu', 'RAVANAPATTU', 'RAVANAMPATTU', 'Ravanampattu');

-- 75 customers  MANIYANTHAPATTU x75  →  Maniyanthapattu / Tiruvannamalai
UPDATE customer SET village = 'Maniyanthapattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Maniyanthapattu', 'MANIYANTHAPATTU');

-- 63 customers  VANIYAMTHANGAL x53, VANIYANTHANGAL x10  →  Vaniyamthangal / Tiruvannamalai
UPDATE customer SET village = 'Vaniyamthangal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vaniyamthangal', 'VANIYAMTHANGAL', 'VANIYANTHANGAL', 'Vaniyanthangal');

-- 61 customers  TVM x50, THIRUVANNAMALAI x6, TIRUVANNAMALAI x5  →  Tiruvannamalai / Tiruvannamalai
UPDATE customer SET village = 'Tiruvannamalai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Tiruvannamalai', 'TVM', 'THIRUVANNAMALAI', 'TIRUVANNAMALAI', 'Thiruvannamalai', 'Tvm');

-- 51 customers  MANNAPATTI x51  →  Mannapatti / Tiruvannamalai
UPDATE customer SET village = 'Mannapatti', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mannapatti', 'MANNAPATTI');

-- 50 customers  KALARPALAYAM x49, KALARPALAYAM,.. x1  →  Kalarpalayam / Tiruvannamalai
UPDATE customer SET village = 'Kalarpalayam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kalarpalayam', 'KALARPALAYAM', 'KALARPALAYAM,..', 'Kalarpalayam,..');

-- 46 customers  V NAMMIYANTHAL x23, V.NAMINTHAL x20, V.NAMMIYANTHAL x2, V. NAMINTHAL x1  →  V. Naminthal / Tiruvannamalai
UPDATE customer SET village = 'V. Naminthal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('V. Naminthal', 'V NAMMIYANTHAL', 'V.NAMINTHAL', 'V.NAMMIYANTHAL', 'V. NAMINTHAL', 'V Nammiyanthal', 'V.Naminthal', 'V.Nammiyanthal');

-- 45 customers  MELMAMPATTU x44, MEL MAMPATTU x1  →  Melmampattu / Tiruvannamalai
UPDATE customer SET village = 'Melmampattu', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Melmampattu', 'MELMAMPATTU', 'MEL MAMPATTU', 'Mel Mampattu');

-- 45 customers  RAMANATHAPURAM x45  →  Ramanathapuram / Tiruvannamalai
UPDATE customer SET village = 'Ramanathapuram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ramanathapuram', 'RAMANATHAPURAM');

-- 43 customers  MATTAPARAI x43  →  Mattaparai / Tiruvannamalai
UPDATE customer SET village = 'Mattaparai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Mattaparai', 'MATTAPARAI');

-- 41 customers  SEKKADIKUPPAM x41  →  Sekkadikuppam / Tiruvannamalai
UPDATE customer SET village = 'Sekkadikuppam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Sekkadikuppam', 'SEKKADIKUPPAM');

-- 37 customers  CHATRAM x37  →  Chatram / Tiruvannamalai
UPDATE customer SET village = 'Chatram', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Chatram', 'CHATRAM');

-- 36 customers  KODAPUNDI x36  →  Kodapundi / Viluppuram
UPDATE customer SET village = 'Kodapundi', district = 'Viluppuram' WHERE organization_id = 1 AND village IN ('Kodapundi', 'KODAPUNDI');

-- 35 customers  KATTUKULAM x35  →  Kattukulam / Tiruvannamalai
UPDATE customer SET village = 'Kattukulam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Kattukulam', 'KATTUKULAM');

-- 35 customers  KORAGATHANGAL x35  →  Koragathangal / Tiruvannamalai
UPDATE customer SET village = 'Koragathangal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Koragathangal', 'KORAGATHANGAL');

-- 35 customers  THELLANANTHAL x35  →  Thellananthal / Tiruvannamalai
UPDATE customer SET village = 'Thellananthal', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Thellananthal', 'THELLANANTHAL');

-- 33 customers  AMMANKALODAI x33  →  Ammankalodai / Tiruvannamalai
UPDATE customer SET village = 'Ammankalodai', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ammankalodai', 'AMMANKALODAI');

-- 33 customers  KARAPALLAM x33  →  Karapallam / Tiruvannamalai
UPDATE customer SET village = 'Karapallam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Karapallam', 'KARAPALLAM');

-- 27 customers  ELAVATHADI x26, ILAVATHADI x1  →  Ilavathadi / Tiruvannamalai
UPDATE customer SET village = 'Ilavathadi', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Ilavathadi', 'ELAVATHADI', 'ILAVATHADI', 'Elavathadi');

-- 1 customers  VAITHANAKUNAM x1  →  Vaithanakunam / Tiruvannamalai
UPDATE customer SET village = 'Vaithanakunam', district = 'Tiruvannamalai' WHERE organization_id = 1 AND village IN ('Vaithanakunam', 'VAITHANAKUNAM');

-- ---------------------------------------------------------------------------
-- C) Unmatched spellings (not updated). Title-cased only in 07_customer.sql.
--     Add to Config or extend ALIASES in scripts/generate_customer_village_fix.py.
-- ---------------------------------------------------------------------------

-- count  typed_name
--    30  KATHAYAPATTU   (no-lgd-match)
--    29  KOMOTTUR   (no-lgd-match)
--    29  MANIMANGALAM   (no-lgd-match)
--    29  RAJAPALAIYAM   (no-lgd-match)
--    29  VIJAYANAGARAM   (no-lgd-match)
--    28  RAJAPALAYAM   (no-lgd-match)
--    27  KEERANANTHAPATTU   (no-lgd-match)
--    26  PALLAOUR   (no-lgd-match)
--    26  KEERANTHAPATTU   (no-lgd-match)
--    25  PERIYAKALLANTHAL   (no-lgd-match)
--    25  VAITHALAKULAM   (no-lgd-match)
--    23  KATTUVANAM   (no-lgd-match)
--    22  MANNAMPATTI   (no-lgd-match)
--    21  ELANTHAKULAM   (no-lgd-match)
--    20  KOOUR   (no-lgd-match)
--    20  RAMAPURAM   (no-lgd-match)
--    20  KUNIYENTHAL   (no-lgd-match)
--    20  SERIYANTHAL   (no-lgd-match)
--    20  VADUGAPOONDI   (no-lgd-match)
--    19  SETTITHANGAL   (no-lgd-match)
--    19  NUKAMPADI   (no-lgd-match)
--    19  CHINNAKALLANTHAL   (no-lgd-match)
--    18  KALARPALAIYAM   (no-lgd-match)
--    18  OTTERI   (no-lgd-match)
--    18  VADAKARUMBALUR   (no-lgd-match)
--    18  THURINJAPAURAM   (no-lgd-match)
--    17  ANANDHAL   (no-lgd-match)
--    17  V.NAMIYENTHAL   (no-lgd-match)
--    17  UTHANGAL   (no-lgd-match)
--    17  GANESHAPURAM   (no-lgd-match)
--    17  INTHRANAGAR   (no-lgd-match)
--    17  KAPALAPADI   (no-lgd-match)
--    17  KODUGANKUPPAM   (no-lgd-match)
--    17  GANESHAPUREM   (no-lgd-match)
--    16  POIYANTHAL   (no-lgd-match)
--    16  SANATHAL   (no-lgd-match)
--    16  BOTHAMANGALAM   (no-lgd-match)
--    16  NARNAMANGALAM   (no-lgd-match)
--    16  SANADHAL   (no-lgd-match)
--    16  MATHALABADI   (no-lgd-match)
--    15  MANGALAMPUTHUR   (no-lgd-match)
--    15  UNKNOWN   (no-lgd-match)
--    15  SATHRAM   (no-lgd-match)
--    15  SERIYENTHAL   (no-lgd-match)
--    15  KARNAMPUNDI   (no-lgd-match)
--    15  GANAPATHIPURAM   (no-lgd-match)
--    14  MALAIYANUR   (no-lgd-match)
--    14  THEPPARAMPATTU   (no-lgd-match)
--    14  INAMKARIYENTHAL   (no-lgd-match)
--    14  SANANANDHAL   (no-lgd-match)
--    14  PUDHUR   (no-lgd-match)
--    14  VADAKARAMBALUR   (no-lgd-match)
--    14  KODUKUPPAM   (no-lgd-match)
--    14  THEPARAPATTU   (no-lgd-match)
--    13  KLIPATTU   (no-lgd-match)
--    13  OOTERI   (no-lgd-match)
--    13  JAMBODAI   (no-lgd-match)
--    13  SALAKUPPAM   (no-lgd-match)
--    13  KAPPALAPATI   (no-lgd-match)
--    13  KOYAPULUR   (no-lgd-match)
--    13  MANATHAL   (no-lgd-match)
--    13  SERUTHALAIPUNDI   (no-lgd-match)
--    13  VENGATESAPURAM   (no-lgd-match)
--    13  AATHURAI   (no-lgd-match)
--    13  VADUGAPONDI   (no-lgd-match)
--    13  KALASTHABADI   (no-lgd-match)
--    13  MADHULAMBADI   (no-lgd-match)
--    12  KO MOTTUR   (no-lgd-match)
--    12  SANGALIKUPPAM   (no-lgd-match)
--    12  MELSADAYANUDAI   (no-lgd-match)
--    12  VP KUPPAM   (no-lgd-match)
--    12  PALLAUR   (no-lgd-match)
--    12  KATTHALAMPATTU   (no-lgd-match)
--    12  SANKILIKUPPAM   (no-lgd-match)
--    12  THEPPARAPATTU   (no-lgd-match)
--    12  NUKABADI   (no-lgd-match)
--    11  MELPALANTHAL   (no-lgd-match)
--    11  ANANTHAL PATTI   (no-lgd-match)
--    11  KORATTUKUPPAM   (no-lgd-match)
--    11  KLIYAPATTU   (no-lgd-match)
--    11  KATTUVANATHAM   (no-lgd-match)
--    11  MANGALAM PUDHUR   (no-lgd-match)
--    11  MANAGALAM   (no-lgd-match)
--    11  KUNNAKUPPAM   (no-lgd-match)
--    11  KANAPAPURAM   (no-lgd-match)
--    11  SETTAPATTU   (no-lgd-match)
--    11  GANESAPURAM   (no-lgd-match)
--    11  MELPALANDHAL   (no-lgd-match)
--    11  MEL PALANANDAL   (no-lgd-match)
--    10  KOVILPURAYUR   (no-lgd-match)
--    10  VAITHALAKUNAM   (no-lgd-match)
--    10  CHEKKADIKUPPAM   (no-lgd-match)
--    10  KOPALLAOUR   (no-lgd-match)
--    10  NELLIMEDU   (no-lgd-match)
--    10  T. KUPPAM   (no-lgd-match)
--    10  ALAMPURADAI   (no-lgd-match)
--    10  MANGALAM PUTHUR   (no-lgd-match)
--    10  MELMAMBATTU   (no-lgd-match)
--    10  NOOKAMABADI   (no-lgd-match)
--    10  MELSAVALAPADI   (no-lgd-match)
--    10  AMMANGALODAI   (no-lgd-match)
--    10  KATHAZHAPATTU   (no-lgd-match)
--    10  KALASTHAMABDI   (no-lgd-match)
--    10  PENNATHUR   (no-lgd-match)
--    10  SORAKOLATHUR   (no-lgd-match)
--    10  SADAIYANODAI   (no-lgd-match)
--    10  KAPLABADI   (no-lgd-match)
--     9  PURADAI   (no-lgd-match)
--     9  CHATHRAM   (no-lgd-match)
--     9  K PURAYUR   (no-lgd-match)
--     9  RAVANAMBATTU   (no-lgd-match)
--     9  KATAPPANANTHAL   (no-lgd-match)
--     9  PALLIKONDAPATTU   (no-lgd-match)
--     9  KUNTHALAMBATTU   (no-lgd-match)
--     9  ANNANAGAR   (no-lgd-match)
--     9  KALASHTHAMBADI   (no-lgd-match)
--     9  KILLAMBADI   (no-lgd-match)
--     9  VALLIVAGAI PUDHUR   (no-lgd-match)
--     9  VALLIVAGAI PATTI   (no-lgd-match)
--     9  ALAPURAVADAI   (no-lgd-match)
--     9  MOTUR   (no-lgd-match)
--     9  KOTAPUNDI   (no-lgd-match)
--     9  SIRUTHALAIPUNDI   (no-lgd-match)
--     9  KALSTHAMBADI   (no-lgd-match)
--     9  DHURGAM   (no-lgd-match)
--     9  ATHARAI   (no-lgd-match)
--     9  SATHIRAM   (no-lgd-match)
--     9  DD   (abbrev)
--     9  KOYAPALUR   (no-lgd-match)
--     9  KADAPANATHAL   (no-lgd-match)
--     9  V.VADI   (no-lgd-match)
--     9  VAYALAMUR   (no-lgd-match)
--     8  AVALUPET   (no-lgd-match)
--     8  ANITHANGAL   (no-lgd-match)
--     8  CHETTITHANGAL   (no-lgd-match)
--     8  UDAYARPALAYAM   (no-lgd-match)
--     8  SADAIYANUDAI   (no-lgd-match)
--     8  MELPALANATHAL   (no-lgd-match)
--     8  VALLIVAGAI PUTHUR   (no-lgd-match)
--     8  KARKUNAM   (no-lgd-match)
--     8  MELKUNNUMURINJI   (no-lgd-match)
--     8  PULIYANKULAM   (no-lgd-match)
--     8  KEDATHANGAL   (no-lgd-match)
--     8  KOLAPADI   (no-lgd-match)
--     8  VAILAMBUR   (no-lgd-match)
--     8  OOTHAPOONDI   (no-lgd-match)
--     8  VELUGANDHAL   (no-lgd-match)
--     8  CC   (abbrev)
--     8  MELARUNKUNAM   (no-lgd-match)
--     7  VADANTHAVADI   (no-lgd-match)
--     7  RPAKKAM   (no-lgd-match)
--     7  KAPLAMBADI   (no-lgd-match)
--     7  MALAYANUR   (no-lgd-match)
--     7  KAPALAMPADI   (no-lgd-match)
--     7  VALLUVA   (no-lgd-match)
--     7  KAPPALAMPATI   (no-lgd-match)
--     7  PERIYAKULAM   (no-lgd-match)
--     7  PARIYAMPATTU   (no-lgd-match)
--     7  DEEPAMNAGAR   (no-lgd-match)
--     7  SAMANTHIYAPURAM   (no-lgd-match)
--     7  NAMIYENTHAL   (no-lgd-match)
--     7  KATAPANANTHAL   (no-lgd-match)
--     7  SAVARAPONDI   (no-lgd-match)
--     7  MGR NAGAR   (no-lgd-match)
--     7  PUTHUR   (no-lgd-match)
--     7  SOYANTHANGAL   (no-lgd-match)
--     7  ALAGARAMANGALAM   (no-lgd-match)
--     7  PALANATHAL   (no-lgd-match)
--     7  KARNAMBUNDI   (no-lgd-match)
--     7  NAMMIYANATHAL   (no-lgd-match)
--     7  D NAMMIYANATHAL   (no-lgd-match)
--     7  SEETAMPATTU   (no-lgd-match)
--     7  DEEPAM NAGAR   (no-lgd-match)
--     7  KARNALPADI   (no-lgd-match)
--     7  KODUKANKUPPAM   (no-lgd-match)
--     7  PORKONAM   (no-lgd-match)
--     7  VALUTHALAMKUNAM   (no-lgd-match)
--     7  MAMPATTU   (no-lgd-match)
--     7  VASTHALAPURAVADAI   (no-lgd-match)
--     7  VV   (abbrev)
--     7  K.PURADAI   (no-lgd-match)
--     7  KORAKATHAGAL   (no-lgd-match)
--     7  KAPALABADI   (no-lgd-match)
--     7  K PURIYUR   (no-lgd-match)
--     6  R PAKKAM   (no-lgd-match)
--     6  AARPAKKAM   (no-lgd-match)
--     6  BOOTHAMANAGALAM   (no-lgd-match)
--     6  PALANTHAL   (no-lgd-match)
--     6  METTUVAILAMUR   (no-lgd-match)
--     6  KILLIPATTU   (no-lgd-match)
--     6  ANANTHAL MULLAINAGAR   (no-lgd-match)
--     6  SEEYAPOONDI   (no-lgd-match)
--     6  VADAAANDAPATTU   (no-lgd-match)
--     6  MULLAINAGAR   (no-lgd-match)
--     6  KONANTHAL   (no-lgd-match)
--     6  SANANATHAL   (no-lgd-match)
--     6  KODUNKUPPAM   (no-lgd-match)
--     6  KUNNUMURINGI   (no-lgd-match)
--     6  METTUVAILAMPUR   (no-lgd-match)
--     6  KERANANTHAPATTU   (no-lgd-match)
--     6  INDHIRANAGAR   (no-lgd-match)
--     6  KOUR   (no-lgd-match)
--     6  VENGADESAPURAM   (no-lgd-match)
--     6  SANARPALAYAM   (no-lgd-match)
--     6  KEKLUR PURAVADAI   (no-lgd-match)
--     6  V PATTI   (no-lgd-match)
--     6  MALLANDI   (no-lgd-match)
--     6  ANNAKILIKOTTA   (no-lgd-match)
--     6  KALANAPADI   (no-lgd-match)
--     6  KARNAMPOONDI   (no-lgd-match)
--     6  ARIYANKUPPAM   (no-lgd-match)
--     6  RAMAPUREM   (no-lgd-match)
--     6  EAMPALAM   (no-lgd-match)
--     6  KILAMBADI   (no-lgd-match)
--     6  DHURUVAM   (no-lgd-match)
--     6  VANIYAMTHANAGAL   (no-lgd-match)
--     6  KATTUTHELLUR   (no-lgd-match)
--     6  KOLAKUDY   (no-lgd-match)
--     6  VAITHALANKULAM   (no-lgd-match)
--     6  POLUR   (no-lgd-match)
--     6  KELKUPAM   (no-lgd-match)
--     6  KANAPABURAM   (no-lgd-match)
--     6  ANNATHAL   (no-lgd-match)
--     6  PUNALKADU   (no-lgd-match)
--     6  CHENGAM   (no-lgd-match)
--     5  KELPALANTHAL   (no-lgd-match)
--     5  KIL PALANANTHAL   (no-lgd-match)
--     5  K.PURIYUR   (no-lgd-match)
--     5  VALLINAGAR   (no-lgd-match)
--     5  CHALLAMKUPPAM   (no-lgd-match)
--     5  T.V.MALAI   (no-lgd-match)
--     5  MANGALAMPUDHUR   (no-lgd-match)
--     5  INDRANAGAR   (no-lgd-match)
--     5  KAPPALAMBATI   (no-lgd-match)
--     5  NUKKAMPADI   (no-lgd-match)
--     5  T KUPPAM   (no-lgd-match)
--     5  SOMASPADI   (no-lgd-match)
--     5  V P KUPPAM   (no-lgd-match)
--     5  THELLANANDHAL   (no-lgd-match)
--     5  PENATHUR   (no-lgd-match)
--     5  KILYAPATTU   (no-lgd-match)
--     5  DHURKAM   (no-lgd-match)
--     5  MATHALAMBADI   (no-lgd-match)
--     5  KORAKKANTHANGAL   (no-lgd-match)
--     5  VENGAYAVELLORE   (no-lgd-match)
--     5  KRISHNANAGAR   (no-lgd-match)
--     5  LADAPURAM   (no-lgd-match)
--     5  MELKUNNUMURUNJI   (no-lgd-match)
--     5  OOSAMBADI   (no-lgd-match)
--     5  KEKLURPURAVADAI   (no-lgd-match)
--     5  KAMBATTU   (no-lgd-match)
--     5  KORAKATHANGAL   (no-lgd-match)
--     5  ADUGAPACHI   (no-lgd-match)
--     5  SELVAPAURAM   (no-lgd-match)
--     5  SARTHAPADI   (no-lgd-match)
--     5  ERUMBONDI   (no-lgd-match)
--     5  OTERI   (no-lgd-match)
--     5  BYE PASS   (no-lgd-match)
--     5  THELLANADHAL   (no-lgd-match)
--     5  D NAMMIAYANTHAL   (no-lgd-match)
--     5  THAYAKONAM   (no-lgd-match)
--     5  BHARATHIPURAM   (no-lgd-match)
--     5  VASTHALAMPURADAI   (no-lgd-match)
--     5  REDDIYARPALAYAM   (no-lgd-match)
--     5  D NAMMIYATHAL   (no-lgd-match)
--     5  POYANATHAL   (no-lgd-match)
--     5  INAMKARIAYANTHAL   (no-lgd-match)
--     5  ARUKUNAM   (no-lgd-match)
--     5  MELVAYALAMUR   (no-lgd-match)
--     5  MELSEVALABADI   (no-lgd-match)
--     5  ETHUVAPETTAI   (no-lgd-match)
--     5  KALAR KOTTA   (no-lgd-match)
--     5  SIYAPONDI   (no-lgd-match)
--     5  EECHANKUPPAM   (no-lgd-match)
-- … plus 2895 customers across spellings with fewer than 5 farmers each

