-- Database Initialization Script for AI Paper Summary Website - v2.0
-- Character Set: utf8mb4

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------
-- Table structure for paper
-- ----------------------------
CREATE TABLE IF NOT EXISTS `paper` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `arxiv_id` VARCHAR(50) NOT NULL,
  `title` VARCHAR(500) NOT NULL,
  `title_en` VARCHAR(500) DEFAULT NULL, -- PRD v2.0
  `authors` JSON NOT NULL,
  `abstract` TEXT NOT NULL,
  `pdf_url` VARCHAR(255) NOT NULL,
  `upvotes` INT DEFAULT 0,
  `arxiv_publish_date` DATE NOT NULL,
  
  -- PRD v2.0 Fields
  `score` INT DEFAULT 0,
  `score_reasons` JSON DEFAULT NULL,
  `category` VARCHAR(20) DEFAULT NULL COMMENT 'focus, watching, candidate',
  `direction` VARCHAR(50) DEFAULT NULL COMMENT 'e.g. Agent, Inference',
  
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_arxiv_id` (`arxiv_id`),
  INDEX `idx_publish_date` (`arxiv_publish_date`),
  INDEX `idx_category` (`category`),
  INDEX `idx_direction` (`direction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for paper_summary
-- ----------------------------
CREATE TABLE IF NOT EXISTS `paper_summary` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `paper_id` INT NOT NULL,
  
  -- PRD v2.0 Bilingual Fields
  `one_line_summary` VARCHAR(255) NOT NULL, -- CN
  `one_line_summary_en` VARCHAR(255) DEFAULT NULL, -- EN
  `core_highlights` JSON NOT NULL, -- CN Array
  `core_highlights_en` JSON DEFAULT NULL, -- EN Array
  `application_scenarios` TEXT NOT NULL, -- CN
  `application_scenarios_en` TEXT DEFAULT NULL, -- EN
  
  `issue_date` DATE NOT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  CONSTRAINT `fk_paper_id` FOREIGN KEY (`paper_id`) REFERENCES `paper` (`id`) ON DELETE CASCADE,
  UNIQUE KEY `uk_paper_issue` (`paper_id`, `issue_date`),
  INDEX `idx_issue_date` (`issue_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for subscriber
-- ----------------------------
CREATE TABLE IF NOT EXISTS `subscriber` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(255) NOT NULL,
  `status` TINYINT DEFAULT 0 COMMENT '0: unverified, 1: active, 2: unsubscribed',
  `verify_token` VARCHAR(64) DEFAULT NULL,
  `unsubscribe_token` VARCHAR(64) NOT NULL,
  `token_expires_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_verify_token` (`verify_token`),
  UNIQUE KEY `uk_unsubscribe_token` (`unsubscribe_token`),
  INDEX `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ----------------------------
-- Table structure for system_task_log
-- ----------------------------
CREATE TABLE IF NOT EXISTS `system_task_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `issue_date` DATE NOT NULL,
  `status` VARCHAR(20) NOT NULL COMMENT 'RUNNING, SUCCESS, FAILED',
  `fetched_count` INT DEFAULT 0,
  `processed_count` INT DEFAULT 0,
  `error_log` TEXT DEFAULT NULL,
  `started_at` DATETIME DEFAULT CURRENT_TIMESTAMP,
  `finished_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_issue_date` (`issue_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
