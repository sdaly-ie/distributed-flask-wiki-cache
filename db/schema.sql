-- CT5169 CA1 cache schema.
-- Runs automatically on first MySQL container boot via the
-- docker-entrypoint-initdb.d mount defined in db/docker-compose.yml.

CREATE DATABASE IF NOT EXISTS wiki_cache
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE wiki_cache;

CREATE TABLE IF NOT EXISTS searches (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    query_text  VARCHAR(255) NOT NULL UNIQUE,
    result_text MEDIUMTEXT   NOT NULL,
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP,
    updated_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP
                             ON UPDATE CURRENT_TIMESTAMP
);