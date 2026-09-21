-- Shri Gouri Engineers -- local MySQL bootstrap
--
-- Creates the database and a dedicated application user. Run once, as a
-- MySQL administrator:
--
--     mysql -u root -p < db/setup_mysql.sql
--
-- On Windows, if `mysql` is not on PATH:
--     & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p < db\setup_mysql.sql
--
-- IMPORTANT: replace CHANGE_ME below with a password of your own before
-- running this, and put the same value in .env as DB_PASSWORD. Do not commit
-- either file with a real password in it.

-- utf8mb4 throughout: project names and machine specifications contain
-- characters (degree, plus-minus, multiplication signs) that utf8mb3 cannot
-- store, and the rupee sign appears in invoice text.
CREATE DATABASE IF NOT EXISTS sge_portal
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- A dedicated account with rights on this one database only, rather than
-- running the application as root.
CREATE USER IF NOT EXISTS 'sge_app'@'localhost' IDENTIFIED BY 'CHANGE_ME';
CREATE USER IF NOT EXISTS 'sge_app'@'127.0.0.1' IDENTIFIED BY 'CHANGE_ME';

-- Django needs DDL rights to run migrations, and CREATE/DROP on the
-- test_ database when running the suite against MySQL.
GRANT ALL PRIVILEGES ON sge_portal.* TO 'sge_app'@'localhost';
GRANT ALL PRIVILEGES ON sge_portal.* TO 'sge_app'@'127.0.0.1';
GRANT ALL PRIVILEGES ON `test\_sge\_portal`.* TO 'sge_app'@'localhost';
GRANT ALL PRIVILEGES ON `test\_sge\_portal`.* TO 'sge_app'@'127.0.0.1';

FLUSH PRIVILEGES;

-- Confirm the result.
SELECT
  SCHEMA_NAME AS `database`,
  DEFAULT_CHARACTER_SET_NAME AS `charset`,
  DEFAULT_COLLATION_NAME AS `collation`
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'sge_portal';
