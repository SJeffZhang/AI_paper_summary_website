-- One-time migration script from the legacy v2.0-ish schema to PRD v2.25.
-- Review carefully before running in production.

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Upgrade paper metadata columns.
ALTER TABLE `paper`
  ADD COLUMN IF NOT EXISTS `title_zh` VARCHAR(500) NULL AFTER `arxiv_id`,
  ADD COLUMN IF NOT EXISTS `title_original` VARCHAR(500) NULL AFTER `title_zh`,
  ADD COLUMN IF NOT EXISTS `venue` VARCHAR(255) NULL AFTER `authors`;

UPDATE `paper`
SET `title_original` = COALESCE(NULLIF(`title_original`, ''), NULLIF(`title_en`, ''), NULLIF(`title`, ''), `arxiv_id`)
WHERE `title_original` IS NULL OR `title_original` = '';

UPDATE `paper`
SET `title_zh` = COALESCE(NULLIF(`title_zh`, ''), NULLIF(`title`, ''), `title_original`)
WHERE `title_zh` IS NULL OR `title_zh` = '';

-- Normalize legacy authors JSON from ["Alice", "Bob"] to [{"name":"Alice","affiliation":""}, ...]
UPDATE `paper` p
JOIN (
  SELECT
    p2.id,
    JSON_ARRAYAGG(JSON_OBJECT('name', jt.author_name, 'affiliation', '')) AS normalized_authors
  FROM `paper` p2,
  JSON_TABLE(p2.authors, '$[*]' COLUMNS (
    author_name VARCHAR(255) PATH '$'
  )) jt
  WHERE JSON_TYPE(JSON_EXTRACT(p2.authors, '$[0]')) = 'STRING'
  GROUP BY p2.id
) converted ON converted.id = p.id
SET p.authors = converted.normalized_authors;

ALTER TABLE `paper`
  MODIFY COLUMN `title_zh` VARCHAR(500) NOT NULL,
  MODIFY COLUMN `title_original` VARCHAR(500) NOT NULL;

-- 2. Rebuild paper_summary as the issue snapshot truth table.
DROP TABLE IF EXISTS `paper_summary_v225`;

CREATE TABLE `paper_summary_v225` (
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
  KEY `idx_direction` (`direction`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `paper_summary_v225` (
  `paper_id`,
  `issue_date`,
  `score`,
  `score_reasons`,
  `category`,
  `candidate_reason`,
  `direction`,
  `one_line_summary`,
  `one_line_summary_en`,
  `core_highlights`,
  `core_highlights_en`,
  `application_scenarios`,
  `application_scenarios_en`
)
SELECT
  p.id,
  ps.issue_date,
  COALESCE(p.score, 0),
  p.score_reasons,
  CASE
    WHEN p.category IN ('focus', 'watching', 'candidate') THEN p.category
    WHEN COALESCE(p.score, 0) >= 80 THEN 'focus'
    WHEN COALESCE(p.score, 0) >= 50 THEN 'watching'
    ELSE 'candidate'
  END,
  CASE
    WHEN p.category = 'candidate' AND COALESCE(p.score, 0) < 50 THEN 'low_score'
    WHEN p.category = 'candidate' THEN 'capacity_overflow'
    ELSE NULL
  END,
  CASE
    WHEN p.direction IN (
      'Agent', 'Reasoning', 'Training_Opt', 'RAG', 'Multimodal', 'Code_Intelligence',
      'Vision_Image', 'Video', 'Safety_Alignment', 'Robotics', 'Audio',
      'Interpretability', 'Benchmarking', 'Data_Engineering', 'Industry_Trends'
    ) THEN p.direction
    ELSE 'Industry_Trends'
  END,
  ps.one_line_summary,
  COALESCE(ps.one_line_summary_en, NULL),
  ps.core_highlights,
  COALESCE(ps.core_highlights_en, NULL),
  ps.application_scenarios,
  COALESCE(ps.application_scenarios_en, NULL)
FROM `paper_summary` ps
JOIN `paper` p ON p.id = ps.paper_id;

-- Backfill papers that never had a summary row into candidate snapshots.
INSERT INTO `paper_summary_v225` (
  `paper_id`,
  `issue_date`,
  `score`,
  `score_reasons`,
  `category`,
  `candidate_reason`,
  `direction`
)
SELECT
  p.id,
  DATE_ADD(p.arxiv_publish_date, INTERVAL 3 DAY),
  COALESCE(p.score, 0),
  p.score_reasons,
  'candidate',
  CASE
    WHEN COALESCE(p.score, 0) < 50 THEN 'low_score'
    ELSE 'capacity_overflow'
  END,
  CASE
    WHEN p.direction IN (
      'Agent', 'Reasoning', 'Training_Opt', 'RAG', 'Multimodal', 'Code_Intelligence',
      'Vision_Image', 'Video', 'Safety_Alignment', 'Robotics', 'Audio',
      'Interpretability', 'Benchmarking', 'Data_Engineering', 'Industry_Trends'
    ) THEN p.direction
    ELSE 'Industry_Trends'
  END
FROM `paper` p
WHERE NOT EXISTS (
  SELECT 1
  FROM `paper_summary_v225` ps
  WHERE ps.paper_id = p.id
    AND ps.issue_date = DATE_ADD(p.arxiv_publish_date, INTERVAL 3 DAY)
);

RENAME TABLE `paper_summary` TO `paper_summary_legacy`, `paper_summary_v225` TO `paper_summary`;
ALTER TABLE `paper_summary`
  ADD CONSTRAINT `fk_paper_summary_paper_id`
  FOREIGN KEY (`paper_id`) REFERENCES `paper` (`id`) ON DELETE CASCADE;

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
  CONSTRAINT `fk_paper_ai_trace_summary_id`
    FOREIGN KEY (`paper_summary_id`) REFERENCES `paper_summary` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

ALTER TABLE `paper_ai_trace`
  MODIFY COLUMN `stage_status` ENUM('generated', 'accepted', 'rejected', 'invalid') NOT NULL;

-- 3. Upgrade subscriber token fields.
ALTER TABLE `subscriber`
  CHANGE COLUMN `unsubscribe_token` `unsub_token` VARCHAR(64) NULL,
  CHANGE COLUMN `token_expires_at` `verify_expires_at` DATETIME NULL,
  ADD COLUMN IF NOT EXISTS `unsub_expires_at` DATETIME NULL AFTER `verify_expires_at`;

UPDATE `subscriber`
SET `unsub_expires_at` = COALESCE(`verify_expires_at`, DATE_ADD(`created_at`, INTERVAL 24 HOUR))
WHERE `unsub_expires_at` IS NULL;

ALTER TABLE `subscriber`
  DROP INDEX `uk_unsubscribe_token`,
  ADD UNIQUE KEY `uk_unsub_token` (`unsub_token`);

SET FOREIGN_KEY_CHECKS = 1;
