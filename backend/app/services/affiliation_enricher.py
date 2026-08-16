import json
import os
import re
import tempfile
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence

import requests

from app.core.config import settings
from app.services.ai_processor import AIProcessor


@dataclass
class AffiliationValidation:
    affiliations: List[str]
    rejected_reasons: List[str] = field(default_factory=list)

    @property
    def approved(self) -> bool:
        return bool(self.affiliations) and not self.rejected_reasons


@dataclass
class AffiliationEnrichmentResult:
    status: str
    affiliations: List[str] = field(default_factory=list)
    attempts: int = 0
    reasons: List[str] = field(default_factory=list)

    @property
    def affiliation_count(self) -> int:
        return len(self.affiliations)


class AffiliationEnricher:
    """
    Recover paper-level institution names from the first page of a paper PDF.

    This intentionally follows the article-style flow: extract first-page text,
    ask the LLM for organization names, then validate and deduplicate the list
    before writing a paper-level `affiliations` field.
    """

    RESOURCE_SUFFIX_PATTERN = re.compile(
        r"\b(?:github|huggingface|code|website|homepage|project\s+page|project\s+site|demo|blog)\b.*$",
        re.I,
    )

    def __init__(
        self,
        ai_processor: Optional[AIProcessor] = None,
        *,
        downloader: Optional[Callable[[str], bytes]] = None,
        page_text_extractor: Optional[Callable[[str], str]] = None,
        progress_callback: Optional[Callable[[str, Dict[str, Any]], None]] = None,
    ):
        self.ai_processor = ai_processor or AIProcessor()
        self.downloader = downloader or self._download_pdf
        self.page_text_extractor = page_text_extractor or self._extract_first_page_text
        self.progress_callback = progress_callback

    def enrich_paper(self, paper: Dict[str, Any]) -> AffiliationEnrichmentResult:
        pdf_url = str(paper.get("pdf_url") or "").strip()
        if not pdf_url:
            return AffiliationEnrichmentResult(status="skipped_no_pdf_url")

        try:
            pdf_bytes = self.downloader(pdf_url)
        except Exception as exc:
            return AffiliationEnrichmentResult(status="download_failed", reasons=[str(exc)])

        pdf_path = ""
        try:
            with tempfile.NamedTemporaryFile(prefix="paper-affiliation-", suffix=".pdf", delete=False) as tmp:
                tmp.write(pdf_bytes)
                pdf_path = tmp.name

            try:
                page_text = self.page_text_extractor(pdf_path)
            except Exception as exc:
                return AffiliationEnrichmentResult(status="text_extract_failed", reasons=[str(exc)])
        finally:
            if pdf_path:
                try:
                    os.unlink(pdf_path)
                except OSError:
                    pass

        page_text = self._normalize_page_text(page_text)
        if len(page_text) < max(1, int(settings.AFFILIATION_ENRICH_PAGE_TEXT_MIN_CHARS or 1)):
            return AffiliationEnrichmentResult(
                status="text_extract_failed",
                reasons=["first page text is too short for reliable affiliation extraction"],
            )
        extraction_text = self._front_matter_text(page_text)
        extraction_text = self._strip_title_from_front_matter(
            extraction_text,
            str(paper.get("title_original") or ""),
        )
        max_attempts = min(5, max(1, int(settings.AFFILIATION_ENRICH_MAX_RETRIES or 1)))
        previous_output = ""
        retry_feedback = ""
        last_validation = AffiliationValidation(affiliations=[], rejected_reasons=["not_attempted"])

        for attempt in range(1, max_attempts + 1):
            self._emit_progress(
                "attempt_start",
                {
                    "arxiv_id": paper.get("arxiv_id", ""),
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                },
            )
            try:
                raw_output = self._extract_affiliations(
                    paper=paper,
                    page_text=extraction_text,
                    retry_feedback=retry_feedback,
                    previous_output=previous_output,
                )
                previous_output = raw_output
                affiliations, review_reasons = self._parse_affiliation_review_output(raw_output)
            except Exception as exc:
                reasons = [f"extract_invalid: {exc}"]
                last_validation = AffiliationValidation(affiliations=[], rejected_reasons=reasons)
                self._emit_progress(
                    "attempt_extract_invalid",
                    {
                        "arxiv_id": paper.get("arxiv_id", ""),
                        "attempt": attempt,
                        "max_attempts": max_attempts,
                        "reasons": reasons,
                    },
                )
                retry_feedback = self._build_retry_feedback(reasons, previous_output)
                continue

            validation = self._validate_affiliations(
                affiliations,
                page_text,
                title_original=str(paper.get("title_original") or ""),
            )
            validation.rejected_reasons.extend(review_reasons)
            last_validation = validation
            self._emit_progress(
                "attempt_validated",
                {
                    "arxiv_id": paper.get("arxiv_id", ""),
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "affiliation_count": len(validation.affiliations),
                    "reasons": validation.rejected_reasons,
                },
            )
            if not validation.approved:
                retry_feedback = self._build_retry_feedback(validation.rejected_reasons, previous_output)
                continue

            last_validation = validation
            self._emit_progress(
                "attempt_reviewed",
                {
                    "arxiv_id": paper.get("arxiv_id", ""),
                    "attempt": attempt,
                    "max_attempts": max_attempts,
                    "affiliation_count": len(validation.affiliations),
                    "reasons": validation.rejected_reasons,
                },
            )
            if validation.approved:
                return AffiliationEnrichmentResult(
                    status="overwrite_applied",
                    affiliations=validation.affiliations,
                    attempts=attempt,
                )

            retry_feedback = self._build_retry_feedback(validation.rejected_reasons, previous_output)

        return AffiliationEnrichmentResult(
            status=self._status_from_reasons(last_validation.rejected_reasons),
            affiliations=[],
            attempts=max_attempts,
            reasons=last_validation.rejected_reasons,
        )

    def _extract_affiliations(
        self,
        *,
        paper: Dict[str, Any],
        page_text: str,
        retry_feedback: str,
        previous_output: str,
    ) -> str:
        user_content = "\n".join(
            [
                "Extract affiliation organization names from the paper front-matter text.",
                "",
                "# Paper",
                f"arxiv_id: {paper.get('arxiv_id', '')}",
                f"title: {paper.get('title_original', '')}",
                "",
                "# JSON output contract",
                "Return a JSON object with exactly one field: affiliations.",
                "affiliations must be an array of objects with name, is_institution, and reason fields.",
                "name must preserve the institution's official English spelling and word boundaries.",
                "Use one ASCII space between adjacent English words, even when PDF text extraction joins them "
                "(for example, output 'Fudan University', not 'FudanUniversity').",
                "Do not invent, translate, abbreviate, or otherwise change organization names.",
                "is_institution must be true only for a real university, company, research institute, hospital, or lab.",
                "Use false for author names, emails, URLs, footnote labels, addresses, funding bodies, paper titles, methods, datasets, and headings.",
                "reason must be a short explanation; use an empty string when is_institution is true.",
                "Never infer organizations not present in the source text.",
                "If no organization is present, return {\"affiliations\": []}.",
                "",
                "# Source text",
                "BEGIN_SOURCE",
                page_text,
                "END_SOURCE",
            ]
        )
        if previous_output or retry_feedback:
            user_content += "\n\n# Retry feedback\n"
            user_content += retry_feedback

        return self.ai_processor._call_llm(
            system_prompt=(
                "You are a high-precision paper affiliation extractor and reviewer. "
                "Return only valid JSON and follow the requested schema exactly."
            ),
            user_content=user_content,
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=600,
        )

    def _parse_affiliation_review_output(self, raw_output: str) -> tuple[List[str], List[str]]:
        parsed = self._try_parse_json_any(raw_output)
        if not isinstance(parsed, dict) or not isinstance(parsed.get("affiliations"), list):
            raise ValueError("affiliation_output_must_contain_an_affiliations_array")

        affiliations: List[str] = []
        rejected_reasons: List[str] = []
        for item in parsed["affiliations"]:
            if not isinstance(item, dict):
                rejected_reasons.append("review_invalid_item: affiliation item must be an object")
                continue
            name = self._normalize_affiliation(item.get("name"))
            verdict = item.get("is_institution")
            reason = str(item.get("reason") or "not an institution").strip()
            if not name:
                rejected_reasons.append("review_invalid_item: missing affiliation name")
                continue
            if verdict is True:
                affiliations.append(name)
            elif verdict is False:
                rejected_reasons.append(f"review_rejected: affiliation={name!r} reason={reason}")
            else:
                rejected_reasons.append(f"review_invalid_item: affiliation={name!r} missing boolean is_institution")
        return affiliations, rejected_reasons

    def _extract_numbered_affiliations(self, page_text: str) -> List[str]:
        text = " ".join(str(page_text or "").split())
        if not text:
            return []

        marker_matches = list(re.finditer(r"(?:(?<=\s)|^)(\d{1,2})\s+", text))
        if not marker_matches:
            return []

        affiliations: List[str] = []
        for index, marker in enumerate(marker_matches):
            start = marker.end()
            end = marker_matches[index + 1].start() if index + 1 < len(marker_matches) else len(text)
            segment = text[start:end].strip()
            segment = self._clean_numbered_affiliation_segment(segment)
            if segment:
                affiliations.append(segment)

        deduped: List[str] = []
        seen: set[str] = set()
        for affiliation in affiliations:
            key = self._dedupe_key(affiliation)
            if key and key not in seen:
                seen.add(key)
                deduped.append(affiliation)
        return deduped

    def _clean_numbered_affiliation_segment(self, segment: str) -> str:
        cleaned = str(segment or "").strip(" ,;:-")
        if not cleaned:
            return ""
        cleaned = re.sub(self.RESOURCE_SUFFIX_PATTERN, "", cleaned).strip(" ,;:-")
        cleaned = re.sub(r"\s+", " ", cleaned)
        if not cleaned:
            return ""
        if re.search(r"[@:/]", cleaned):
            return ""
        if len(cleaned) > 120:
            return ""
        return self._normalize_affiliation(cleaned)

    def _validate_affiliations(
        self,
        affiliations: Sequence[str],
        page_text: str,
        *,
        title_original: str = "",
    ) -> AffiliationValidation:
        rejected_reasons: List[str] = []
        accepted: List[str] = []
        seen: set[str] = set()

        for raw_affiliation in affiliations:
            affiliation = self._normalize_affiliation(raw_affiliation)
            if not affiliation:
                continue
            key = self._dedupe_key(affiliation)
            if not key or key in seen:
                continue
            seen.add(key)

            if self._looks_like_title_fragment(affiliation, title_original):
                rejected_reasons.append(f"looks_like_title_fragment: affiliation={affiliation!r}")
                continue
            if not self._contains_fuzzy(page_text, affiliation):
                rejected_reasons.append(f"no_text_evidence: affiliation_not_found={affiliation!r}")
                continue
            accepted.append(affiliation)

        if not accepted and not rejected_reasons:
            rejected_reasons.append("empty_or_low_quality_output: no valid affiliations extracted")

        return AffiliationValidation(affiliations=accepted, rejected_reasons=rejected_reasons)

    def _review_affiliations(self, affiliations: Sequence[str]) -> AffiliationValidation:
        if not affiliations:
            return AffiliationValidation(
                affiliations=[],
                rejected_reasons=["empty_or_low_quality_output: no valid affiliations extracted"],
            )

        approved: List[str] = []
        rejected_reasons: List[str] = []
        for affiliation in affiliations:
            raw_output = self.ai_processor._call_llm(
                system_prompt=(
                    "Classify whether VALUE is the name of an institution or organization. "
                    "Output exactly one line. "
                    "Use YES if it is an institution or organization name. "
                    "Use NO: <short reason> if it is not. "
                    "Do not repeat the prompt. Do not explain."
                ),
                user_content=f"Value: {affiliation}",
                temperature=0.0,
                max_tokens=64,
            )
            approved_value, reason = self._parse_single_review_output(raw_output, affiliation)
            if approved_value:
                approved.append(affiliation)
            else:
                rejected_reasons.append(f"review_rejected: affiliation={affiliation!r} reason={reason}")

        return AffiliationValidation(affiliations=approved, rejected_reasons=rejected_reasons)

    def _download_pdf(self, pdf_url: str) -> bytes:
        response = requests.get(
            pdf_url,
            timeout=max(1, int(settings.AFFILIATION_ENRICH_TIMEOUT_SECONDS or 1)),
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "")
        if "pdf" not in content_type.lower() and not response.content.startswith(b"%PDF"):
            raise ValueError("downloaded content is not a PDF")
        return response.content

    @staticmethod
    def _extract_first_page_text(pdf_path: str) -> str:
        try:
            import pdfplumber

            with pdfplumber.open(pdf_path) as pdf:
                if pdf.pages:
                    text = pdf.pages[0].extract_text() or ""
                    if text.strip():
                        return text
        except Exception:
            pass

        try:
            from pypdf import PdfReader

            reader = PdfReader(pdf_path)
            if reader.pages:
                return reader.pages[0].extract_text() or ""
        except Exception as exc:
            raise ValueError(f"failed to extract first-page text: {exc}") from exc

        return ""

    def _parse_affiliations(self, raw_output: str, source_text: str = "") -> List[str]:
        normalized = str(raw_output or "").strip()
        if not normalized or normalized.casefold() == "empty":
            return []

        parsed = self._try_parse_json_any(normalized)
        if parsed is not None:
            values = self._flatten_json_affiliations(parsed)
        else:
            values = self._split_freeform_affiliations(normalized, source_text)

        affiliations: List[str] = []
        seen: set[str] = set()
        for value in values:
            affiliation = self._normalize_affiliation(value)
            if not affiliation or affiliation.casefold() in {"empty", "none", "n/a", "not provided"}:
                continue
            key = self._dedupe_key(affiliation)
            if key and key not in seen:
                seen.add(key)
                affiliations.append(affiliation)
        return affiliations

    def _try_parse_json_any(self, raw_output: str) -> Any:
        normalized = str(raw_output or "").strip()
        if normalized.startswith("```"):
            normalized = re.sub(r"^```(?:json)?\s*|\s*```$", "", normalized, flags=re.S).strip()

        decoder = json.JSONDecoder()
        for candidate in (normalized,):
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                pass
        for match in re.finditer(r"[\[{]", normalized):
            try:
                parsed, _ = decoder.raw_decode(normalized[match.start():])
                return parsed
            except json.JSONDecodeError:
                continue
        return None

    def _flatten_json_affiliations(self, parsed: Any) -> List[str]:
        if isinstance(parsed, str):
            return self._split_freeform_affiliations(parsed)
        if isinstance(parsed, list):
            values: List[str] = []
            for item in parsed:
                values.extend(self._flatten_json_affiliations(item))
            return values
        if isinstance(parsed, dict):
            for key in ("affiliations", "institutions", "organizations", "organization_names", "data"):
                if key in parsed:
                    return self._flatten_json_affiliations(parsed[key])
            for key in ("name", "affiliation", "institution", "organization"):
                if key in parsed:
                    return [str(parsed[key])]
        return []

    def _split_freeform_affiliations(self, raw_output: str, source_text: str = "") -> List[str]:
        values: List[str] = []
        for raw_line in str(raw_output or "").splitlines():
            line = raw_line.strip()
            if not line:
                continue
            line = re.sub(r"^[-*•\s]+", "", line)
            line = re.sub(r"^\d+[\).:\-\s]+", "", line).strip()
            line = re.sub(r"^(organization|institution|affiliation)s?\s*[:：]\s*", "", line, flags=re.I).strip()
            if not line or line.casefold().startswith(("here are", "the organization", "extracted")):
                continue
            line_candidates = self._extract_line_candidates(raw_line, source_text)
            values.extend(line_candidates)
            if line_candidates:
                continue
            parts = [part.strip() for part in re.split(r"\s*[;；]\s*", line) if part.strip()]
            for part in parts or [line]:
                if self._looks_like_candidate_fragment(part, source_text):
                    values.append(part)
        return values

    def _parse_single_review_output(self, raw_output: str, affiliation: str) -> tuple[bool, str]:
        normalized = str(raw_output or "").strip()
        if normalized.startswith("```"):
            normalized = re.sub(r"^```(?:text|json)?\s*|\s*```$", "", normalized, flags=re.S).strip()

        parsed = self._try_parse_json_any(normalized)
        if parsed is not None:
            return self._parse_single_review_json(parsed, affiliation)

        normalized_casefold = normalized.casefold()
        verdict_lines = list(
            re.finditer(
                r"(?mi)^\s*(yes|no|approved|rejected|approve|reject|true|false)\b(?:\s*[:,|-]\s*(.*))?$",
                normalized,
            )
        )
        if verdict_lines:
            match = verdict_lines[-1]
            verdict = match.group(1).casefold()
            reason = (match.group(2) or "").strip() or "not an institution"
            if verdict in {"yes", "approved", "approve", "true"}:
                return True, ""
            return False, reason

        if re.search(
            r"\b(?:not\s+an?\s+(?:institution|organization)|not\s+the\s+name\s+of\s+an?\s+(?:institution|organization))\b",
            normalized_casefold,
        ):
            return False, normalized.strip() or "not an institution"
        if re.search(
            (
                r"\b(?:is|looks\s+like|appears\s+to\s+be|seems\s+to\s+be)\b"
                r"[^.\n]{0,120}\b("
                r"institution|organization|university|institute|college|school|department|"
                r"laboratory|lab|hospital|company|corporation|startup|enterprise|research\s+center|research\s+centre"
                r")\b"
            ),
            normalized_casefold,
        ):
            return True, ""
        if re.search(
            r"\b(?:is|looks\s+like|appears\s+to\s+be)\s+an?\s+(?:institution|organization)\b",
            normalized_casefold,
        ):
            return True, ""
        raise ValueError(f"review_invalid_verdict: affiliation={affiliation!r} raw={normalized[:160]!r}")

    def _parse_single_review_json(self, parsed: Any, affiliation: str) -> tuple[bool, str]:
        if isinstance(parsed, dict):
            if isinstance(parsed.get("items"), list) and parsed["items"]:
                parsed = parsed["items"][0]
            elif isinstance(parsed.get("results"), list) and parsed["results"]:
                parsed = parsed["results"][0]
        if not isinstance(parsed, dict):
            raise ValueError("review_output_must_be_an_object")
        verdict = str(parsed.get("verdict", parsed.get("approved", parsed.get("decision", "")))).casefold()
        if verdict in {"yes", "approved", "approve", "true"}:
            return True, ""
        if verdict in {"no", "rejected", "reject", "false"}:
            reason = str(parsed.get("reason", "not an institution")).strip() or "not an institution"
            return False, reason
        raise ValueError(f"review_invalid_verdict: affiliation={affiliation!r} raw={parsed!r}")

    def _extract_line_candidates(self, raw_line: str, source_text: str) -> List[str]:
        values: List[str] = []
        for quote_match in re.finditer(r'["“”]([^"\n]{2,120})["“”]', str(raw_line or "")):
            candidate = quote_match.group(1).strip()
            if self._looks_like_candidate_fragment(candidate, source_text, require_source_match=True):
                values.append(candidate)

        reasoning_match = re.match(
            r'^\s*["“”]?(?:\d+[\s:.)-]+)?([A-Z][A-Za-z0-9&./\-]*(?:\s+[A-Z][A-Za-z0-9&./\-]*){0,6})["“”]?\s*[-:]\s*',
            str(raw_line or ""),
        )
        if reasoning_match:
            candidate = reasoning_match.group(1).strip()
            if self._looks_like_candidate_fragment(candidate, source_text, require_source_match=True):
                values.append(candidate)
        return values

    def _looks_like_candidate_fragment(
        self,
        value: str,
        source_text: str,
        *,
        require_source_match: bool = False,
    ) -> bool:
        normalized = self._normalize_affiliation(value)
        if not normalized:
            return False
        if len(normalized) > 120:
            return False
        lowered = normalized.casefold()
        if lowered in {"yes", "no", "empty", "none"}:
            return False
        if any(
            token in lowered
            for token in (
                "looking at",
                "the user wants",
                "validator feedback",
                "previous output",
                "the affiliations",
                "the source text",
                "from this text",
                "i need to",
                "according to the instructions",
                "so i should output",
                "do not include",
                "return only",
                "author names with",
                "the text shows",
                "source text",
                "there are author names",
                "the pattern here is",
                "numbers like",
                "indicate affiliations",
                "superscript numbers",
            )
        ):
            return False
        if require_source_match and source_text and not self._contains_fuzzy(source_text, normalized):
            return False
        return True

    @staticmethod
    def _normalize_affiliation(value: Any) -> str:
        text = " ".join(str(value or "").replace("\n", " ").split()).strip()
        text = re.sub(r"^\d+\s+(?=[A-Za-z\u4e00-\u9fff])", "", text)
        text = re.sub(r"\s*([,;])\s*", r"\1 ", text)
        return text.strip(" ;,.\t\"'")

    @staticmethod
    def _normalize_page_text(value: Any) -> str:
        return " ".join(str(value or "").replace("\x00", " ").split())

    @staticmethod
    def _front_matter_text(page_text: str) -> str:
        normalized = str(page_text or "").strip()
        if not normalized:
            return ""
        cut_positions = []
        for pattern in (r"\babstract\b", r"\bfigure\s*\d+", r"\bkeywords?\b", r"\bintroduction\b"):
            match = re.search(pattern, normalized, flags=re.I)
            if match and match.start() > 120:
                cut_positions.append(match.start())
        if cut_positions:
            normalized = normalized[: min(cut_positions)]
        return normalized[:4000]

    @classmethod
    def _strip_title_from_front_matter(cls, page_text: str, title_original: str) -> str:
        normalized_page = str(page_text or "").strip()
        normalized_title = " ".join(str(title_original or "").split()).strip()
        if not normalized_page or not normalized_title:
            return normalized_page

        if normalized_title in normalized_page:
            normalized_page = normalized_page.replace(normalized_title, " ", 1)

        title_prefix = normalized_title.split(":", 1)[0].strip()
        if title_prefix and len(title_prefix) >= 5 and title_prefix in normalized_page[:400]:
            normalized_page = normalized_page.replace(title_prefix, " ", 1)

        return " ".join(normalized_page.split())

    @classmethod
    def _contains_fuzzy(cls, haystack: str, needle: str) -> bool:
        normalized_haystack = cls._normalize_match_text(haystack)
        normalized_needle = cls._normalize_match_text(needle)
        if not normalized_needle:
            return False
        if normalized_needle in normalized_haystack:
            return True
        needle_tokens = [token for token in normalized_needle.split() if len(token) > 2]
        if needle_tokens and all(token in normalized_haystack for token in needle_tokens[:8]):
            return True

        # PDF text extraction can join adjacent English words. Accept only a long,
        # multi-word candidate whose compact spelling appears verbatim in the source.
        if len(needle_tokens) < 2:
            return False
        compact_needle = "".join(needle_tokens)
        compact_haystack = re.sub(r"[^a-z0-9]+", "", normalized_haystack)
        return len(compact_needle) >= 8 and compact_needle in compact_haystack

    @staticmethod
    def _normalize_match_text(value: str) -> str:
        normalized = str(value or "").casefold()
        normalized = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", " ", normalized)
        return " ".join(normalized.split())

    @classmethod
    def _dedupe_key(cls, affiliation: str) -> str:
        return cls._normalize_match_text(affiliation)

    @staticmethod
    def _build_retry_feedback(reasons: Sequence[str], previous_output: str) -> str:
        lines = [
            "Your previous response was rejected.",
            "Return only raw affiliation names copied from the source text.",
            "Do not include analysis, instructions, or commentary.",
        ]
        reason_values = AffiliationEnricher._summarize_retry_reason_values(reasons)
        if reason_values:
            lines.append("Rejected candidate lines: " + "; ".join(reason_values[:8]))
        if any("review_rejected" in str(reason) for reason in reasons):
            lines.append("Some candidate values were not valid institutions. Keep only real institution names.")
        if any("looks_like_title_fragment" in str(reason) for reason in reasons):
            lines.append("Do not output method names, paper-title fragments, or system names.")
        if any("extract_invalid" in str(reason) for reason in reasons):
            lines.append("Your response format was invalid. Every non-empty line must be one affiliation name.")
        if previous_output:
            preview = " ".join(str(previous_output).split())[:240]
            lines.append("Previous response preview: " + preview)
        return "\n".join(lines)

    @staticmethod
    def _summarize_retry_reason_values(reasons: Sequence[str]) -> List[str]:
        values: List[str] = []
        for reason in reasons:
            text = str(reason or "")
            match = re.search(r"affiliation(?:_not_found)?=(.+)$", text)
            if match:
                value = match.group(1).strip().strip("'\"")
                if value:
                    values.append(value[:120])
        deduped: List[str] = []
        seen: set[str] = set()
        for value in values:
            key = value.casefold()
            if key not in seen:
                seen.add(key)
                deduped.append(value)
        return deduped

    def _emit_progress(self, event: str, payload: Dict[str, Any]) -> None:
        if not self.progress_callback:
            return
        try:
            self.progress_callback(event, payload)
        except Exception:
            return

    @staticmethod
    def _status_from_reasons(reasons: Sequence[str]) -> str:
        normalized = " ".join(str(reason or "").casefold() for reason in reasons)
        if "review_rejected" in normalized or "looks_like_title_fragment" in normalized:
            return "skipped_not_institution"
        if "no_text_evidence" in normalized:
            return "skipped_no_text_evidence"
        if "invalid_json" in normalized or "extract_invalid" in normalized or "review_" in normalized:
            return "skipped_structure_invalid"
        if "empty_or_low_quality_output" in normalized:
            return "skipped_low_confidence"
        return "skipped_low_confidence"

    @classmethod
    def _looks_like_title_fragment(cls, affiliation: str, title_original: str) -> bool:
        normalized_affiliation = cls._normalize_match_text(affiliation)
        normalized_title = cls._normalize_match_text(title_original)
        if not normalized_affiliation or not normalized_title:
            return False
        if normalized_affiliation == normalized_title:
            return True
        title_tokens = normalized_title.split()
        affiliation_tokens = normalized_affiliation.split()
        if not affiliation_tokens:
            return False
        if len(affiliation_tokens) <= 3 and normalized_affiliation in normalized_title:
            if len(affiliation_tokens) == 1 and len(affiliation_tokens[0]) < 5:
                return False
            return True
        if title_tokens[: len(affiliation_tokens)] == affiliation_tokens:
            return True
        return False
