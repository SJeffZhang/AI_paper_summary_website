-- Add paper-level institution extraction storage.

ALTER TABLE `paper`
  ADD COLUMN `affiliations` JSON NULL AFTER `authors`;
