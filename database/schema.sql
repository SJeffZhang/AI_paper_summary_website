-- Database Initialization Script for AI Paper Summary Website - PRD v2.25
-- Character Set: utf8mb4

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `paper` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `arxiv_id` VARCHAR(50) NOT NULL,
  `title_zh` VARCHAR(500) NOT NULL,
  `title_original` VARCHAR(500) NOT NULL,
  `authors` JSON NOT NULL,
  `venue` VARCHAR(255) DEFAULT NULL,
  `abstract` TEXT NOT NULL,
  `pdf_url` VARCHAR(255) NOT NULL,
  `upvotes` INT NOT NULL DEFAULT 0,
  `arxiv_publish_date` DATE NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_arxiv_id` (`arxiv_id`),
  KEY `idx_publish_date` (`arxiv_publish_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paper_summary` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `paper_id` INT NOT NULL,
  `issue_date` DATE NOT NULL,
  `score` INT NOT NULL DEFAULT 0,
  `score_reasons` JSON DEFAULT NULL,
  `category` ENUM('focus', 'watching', 'candidate') NOT NULL,
  `candidate_reason` ENUM('low_score', 'capacity_overflow', 'reviewer_rejected') DEFAULT NULL,
  `direction` ENUM(
    'Agent',
    'Reasoning',
    'Training_Opt',
    'RAG',
    'Multimodal',
    'Code_Intelligence',
    'Vision_Image',
    'Video',
    'Safety_Alignment',
    'Robotics',
    'Audio',
    'Interpretability',
    'Benchmarking',
    'Data_Engineering',
    'Industry_Trends'
  ) NOT NULL,
  `one_line_summary` TEXT DEFAULT NULL,
  `one_line_summary_en` TEXT DEFAULT NULL,
  `core_highlights` JSON DEFAULT NULL,
  `core_highlights_en` JSON DEFAULT NULL,
  `application_scenarios` TEXT DEFAULT NULL,
  `application_scenarios_en` TEXT DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_paper_issue` (`paper_id`, `issue_date`),
  KEY `idx_issue_date` (`issue_date`),
  KEY `idx_category` (`category`),
  KEY `idx_direction` (`direction`),
  CONSTRAINT `fk_paper_summary_paper_id` FOREIGN KEY (`paper_id`) REFERENCES `paper` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `paper_ai_trace` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `paper_summary_id` INT NOT NULL,
  `stage` ENUM('editor', 'writer', 'reviewer') NOT NULL,
  `stage_status` ENUM('generated', 'accepted', 'rejected', 'invalid') NOT NULL,
  `attempt_no` INT NOT NULL DEFAULT 1,
  `content` TEXT NOT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_trace_summary_stage_attempt` (`paper_summary_id`, `stage`, `attempt_no`),
  KEY `idx_trace_summary_id` (`paper_summary_id`),
  KEY `idx_trace_stage` (`stage`),
  CONSTRAINT `fk_paper_ai_trace_summary_id` FOREIGN KEY (`paper_summary_id`) REFERENCES `paper_summary` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `subscriber` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `email` VARCHAR(255) NOT NULL,
  `status` INT NOT NULL DEFAULT 0 COMMENT '0:未验证, 1:活跃, 2:退订',
  `verify_token` VARCHAR(64) DEFAULT NULL,
  `unsub_token` VARCHAR(64) DEFAULT NULL,
  `verify_expires_at` DATETIME DEFAULT NULL,
  `unsub_expires_at` DATETIME DEFAULT NULL,
  `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_email` (`email`),
  UNIQUE KEY `uk_verify_token` (`verify_token`),
  UNIQUE KEY `uk_unsub_token` (`unsub_token`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `system_task_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `issue_date` DATE NOT NULL,
  `status` VARCHAR(20) NOT NULL,
  `fetched_count` INT NOT NULL DEFAULT 0,
  `processed_count` INT NOT NULL DEFAULT 0,
  `error_log` TEXT DEFAULT NULL,
  `started_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `finished_at` DATETIME DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_issue_date` (`issue_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `notification_delivery_log` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `notification_type` ENUM('daily_digest', 'job_alert') NOT NULL,
  `run_date` DATE NOT NULL,
  `issue_date` DATE DEFAULT NULL,
  `recipient_email` VARCHAR(255) NOT NULL,
  `status` ENUM('sent', 'failed', 'skipped') NOT NULL,
  `subject` VARCHAR(255) NOT NULL,
  `error_log` TEXT DEFAULT NULL,
  `sent_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_notification_type_run_recipient` (`notification_type`, `run_date`, `recipient_email`),
  KEY `idx_notification_type` (`notification_type`),
  KEY `idx_notification_run_date` (`run_date`),
  KEY `idx_notification_issue_date` (`issue_date`),
  KEY `idx_notification_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;
