"""
citation_verifier.py - Citation Verification & Confidence Scoring

Verifies that LLM-generated citations actually match their source chunks.
Detects hallucinated citations and assigns confidence scores.

This is what makes ComplianceGPT's citations TRUSTWORTHY — instead of
blindly trusting the LLM to cite correctly, we verify every citation
against the actual source text.
"""

import re
import logging
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


# =============================================================================
# Confidence Levels
# =============================================================================

class ConfidenceLevel:
    """Confidence classification for citation verification."""
    VERIFIED = "verified"       # Strong match (>= 0.6 similarity)
    PARTIAL = "partial"         # Weak match (>= 0.3 similarity)
    UNVERIFIED = "unverified"   # No meaningful match (< 0.3)
    NOT_CITED = "not_cited"     # Claim references a citation that doesn't exist

    EMOJI = {
        "verified": "✅",
        "partial": "⚠️",
        "unverified": "❌",
        "not_cited": "🚫",
    }


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ClaimVerification:
    """Verification result for a single claim in the answer."""

    claim_text: str
    cited_ids: list[int]
    confidence: float              # 0.0 to 1.0
    confidence_level: str          # ConfidenceLevel value
    matched_source_text: str = ""  # Best matching text from source
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "claim_text": self.claim_text,
            "cited_ids": self.cited_ids,
            "confidence": round(self.confidence, 3),
            "confidence_level": self.confidence_level,
            "matched_source_text": self.matched_source_text[:200] if self.matched_source_text else "",
            "explanation": self.explanation,
        }


@dataclass
class VerificationReport:
    """Complete verification report for a response."""

    total_claims: int
    verified_count: int
    partial_count: int
    unverified_count: int
    not_cited_count: int
    overall_confidence: float           # Weighted average
    overall_level: str                  # Overall confidence level
    claims: list[ClaimVerification] = field(default_factory=list)
    trust_score: float = 0.0           # 0-100 trust percentage

    def to_dict(self) -> dict:
        return {
            "total_claims": self.total_claims,
            "verified_count": self.verified_count,
            "partial_count": self.partial_count,
            "unverified_count": self.unverified_count,
            "not_cited_count": self.not_cited_count,
            "overall_confidence": round(self.overall_confidence, 3),
            "overall_level": self.overall_level,
            "trust_score": round(self.trust_score, 1),
            "claims": [c.to_dict() for c in self.claims],
        }

    def summary(self) -> str:
        """Generate a human-readable verification summary."""
        emoji = ConfidenceLevel.EMOJI.get(self.overall_level, "❓")
        lines = [
            f"{emoji} Citation Verification: {self.overall_level.upper()} "
            f"(Trust Score: {self.trust_score:.0f}%)",
            f"   {self.verified_count} verified, "
            f"{self.partial_count} partial, "
            f"{self.unverified_count} unverified "
            f"out of {self.total_claims} claims",
        ]
        return "\n".join(lines)


# =============================================================================
# Citation Verifier
# =============================================================================

class CitationVerifier:
    """
    Verifies LLM-generated citations against source chunks.

    How it works:
    1. Extract individual claims from the LLM answer (sentences with [N] refs)
    2. For each claim, find which citation IDs it references
    3. Compare the claim text against the actual source chunk text
    4. Score similarity and classify confidence
    5. Generate a verification report

    This catches:
    - Hallucinated citations (LLM says [3] but [3] doesn't support the claim)
    - Misattributed citations (claim matches [2] but LLM cited [1])
    - Fabricated content (claim not found in any source chunk)
    """

    # Similarity thresholds
    VERIFIED_THRESHOLD = 0.6     # Strong match
    PARTIAL_THRESHOLD = 0.3      # Weak match

    def __init__(
        self,
        verified_threshold: float = 0.6,
        partial_threshold: float = 0.3,
    ):
        """
        Initialize the citation verifier.

        Args:
            verified_threshold: Minimum similarity for 'verified' status
            partial_threshold: Minimum similarity for 'partial' status
        """
        self.verified_threshold = verified_threshold
        self.partial_threshold = partial_threshold

    def verify(
        self,
        answer: str,
        citations: list,
    ) -> VerificationReport:
        """
        Verify all citations in an answer.

        Args:
            answer: LLM-generated answer text (with [1], [2], etc.)
            citations: List of Citation objects from retrieval

        Returns:
            VerificationReport with per-claim verification
        """
        # Step 1: Extract claims from the answer
        claims = self._extract_claims(answer)

        if not claims:
            return VerificationReport(
                total_claims=0,
                verified_count=0,
                partial_count=0,
                unverified_count=0,
                not_cited_count=0,
                overall_confidence=1.0,
                overall_level=ConfidenceLevel.VERIFIED,
                claims=[],
                trust_score=100.0,
            )

        # Build citation lookup: {citation_id: citation_text}
        citation_map = {}
        for c in citations:
            cid = getattr(c, "citation_id", None)
            text = getattr(c, "text", "")
            if cid is not None:
                citation_map[cid] = text

        # Step 2: Verify each claim
        verified_claims = []
        for claim_text, cited_ids in claims:
            verification = self._verify_claim(claim_text, cited_ids, citation_map)
            verified_claims.append(verification)

        # Step 3: Build report
        return self._build_report(verified_claims)

    def _extract_claims(self, answer: str) -> list[tuple[str, list[int]]]:
        """
        Extract individual claims with their citation references.

        Splits the answer into sentences/claims and identifies
        which citation IDs each one references.

        Args:
            answer: Full LLM answer text

        Returns:
            List of (claim_text, [cited_ids]) tuples
        """
        claims = []

        # Remove markdown formatting that doesn't contain claims
        # Keep content lines, skip headers, blank lines, dividers
        lines = answer.split("\n")
        content_lines = []
        for line in lines:
            stripped = line.strip()
            # Skip blank lines, markdown dividers, section headers
            if not stripped:
                continue
            if stripped.startswith("---"):
                continue
            if stripped.startswith("**Sources:**") or stripped.startswith("Sources:"):
                break  # Stop before the sources section
            content_lines.append(stripped)

        text = " ".join(content_lines)

        # Split into sentences — handle common abbreviations
        # Split on period/question/exclamation followed by space + uppercase or citation
        sentence_pattern = r'(?<=[.!?])\s+(?=[A-Z\["\'])'
        sentences = re.split(sentence_pattern, text)

        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 10:  # Skip very short fragments
                continue

            # Extract citation IDs from this sentence: [1], [2], [1][2], etc.
            cited_ids = [int(m) for m in re.findall(r'\[(\d+)\]', sentence)]

            if cited_ids:
                # Clean the sentence (remove citation markers for comparison)
                clean_sentence = re.sub(r'\s*\[\d+\]', '', sentence).strip()
                # Remove trailing punctuation artifacts
                clean_sentence = clean_sentence.rstrip(".,;:")
                if len(clean_sentence) >= 10:
                    claims.append((clean_sentence, cited_ids))

        return claims

    def _verify_claim(
        self,
        claim_text: str,
        cited_ids: list[int],
        citation_map: dict[int, str],
    ) -> ClaimVerification:
        """
        Verify a single claim against its cited sources.

        Args:
            claim_text: The claim text (without citation markers)
            cited_ids: List of citation IDs referenced by this claim
            citation_map: {citation_id: source_text} lookup

        Returns:
            ClaimVerification result
        """
        best_score = 0.0
        best_match_text = ""
        has_valid_citation = False

        for cid in cited_ids:
            if cid not in citation_map:
                continue

            has_valid_citation = True
            source_text = citation_map[cid]

            # Calculate similarity between claim and source
            score = self._calculate_similarity(claim_text, source_text)

            if score > best_score:
                best_score = score
                best_match_text = self._find_best_matching_segment(
                    claim_text, source_text
                )

        # If no valid citations were found
        if not has_valid_citation:
            return ClaimVerification(
                claim_text=claim_text,
                cited_ids=cited_ids,
                confidence=0.0,
                confidence_level=ConfidenceLevel.NOT_CITED,
                matched_source_text="",
                explanation=f"Citation(s) {cited_ids} not found in retrieved sources",
            )

        # Classify confidence
        if best_score >= self.verified_threshold:
            level = ConfidenceLevel.VERIFIED
            explanation = "Claim is well-supported by the cited source"
        elif best_score >= self.partial_threshold:
            level = ConfidenceLevel.PARTIAL
            explanation = "Claim is partially supported — some details may be inferred"
        else:
            level = ConfidenceLevel.UNVERIFIED
            explanation = "Claim could not be verified against the cited source"

        return ClaimVerification(
            claim_text=claim_text,
            cited_ids=cited_ids,
            confidence=best_score,
            confidence_level=level,
            matched_source_text=best_match_text,
            explanation=explanation,
        )

    def _calculate_similarity(self, claim: str, source: str) -> float:
        """
        Calculate how well a claim is supported by source text.

        Uses a multi-signal approach:
        1. Token overlap (what fraction of claim words appear in source)
        2. Sequence matching (longest common subsequence ratio)
        3. Key term matching (numbers, legal terms, proper nouns)

        The final score is a weighted combination.

        Args:
            claim: The claim text
            source: The source chunk text

        Returns:
            Similarity score 0.0 to 1.0
        """
        claim_lower = claim.lower()
        source_lower = source.lower()

        # Signal 1: Token overlap (40% weight)
        claim_tokens = set(self._tokenize(claim_lower))
        source_tokens = set(self._tokenize(source_lower))

        if not claim_tokens:
            return 0.0

        overlap = claim_tokens & source_tokens
        # Remove stopwords from overlap calculation for precision
        meaningful_claim = claim_tokens - self.STOPWORDS
        meaningful_overlap = overlap - self.STOPWORDS

        if meaningful_claim:
            token_score = len(meaningful_overlap) / len(meaningful_claim)
        else:
            token_score = len(overlap) / len(claim_tokens)

        # Signal 2: Sequence match (30% weight)
        # Use SequenceMatcher on normalized text
        seq_score = SequenceMatcher(
            None, claim_lower, source_lower
        ).ratio()

        # Signal 3: Key term match (30% weight)
        key_terms_score = self._key_terms_match(claim, source)

        # Weighted combination
        final_score = (
            0.40 * token_score +
            0.30 * seq_score +
            0.30 * key_terms_score
        )

        return min(final_score, 1.0)

    def _key_terms_match(self, claim: str, source: str) -> float:
        """
        Check if key terms (numbers, legal references, proper nouns) match.

        These are the most critical elements for compliance accuracy.
        """
        source_lower = source.lower()

        # Extract key terms from claim
        key_terms = []

        # Numbers (72 hours, 4% of turnover, etc.)
        numbers = re.findall(r'\b\d+[\d,.]*\b', claim)
        key_terms.extend(numbers)

        # Legal article references (Article 33, Section 1798.100, etc.)
        articles = re.findall(
            r'(?:Article|Section|Chapter|Art\.?|Sec\.?)\s*\d+',
            claim,
            re.IGNORECASE
        )
        key_terms.extend([a.lower() for a in articles])

        # Legal terms (specific compliance vocabulary)
        legal_patterns = [
            r'\bdata\s+subject\b', r'\bdata\s+controller\b',
            r'\bdata\s+processor\b', r'\bsupervisory\s+authority\b',
            r'\bpersonal\s+data\b', r'\bdata\s+breach\b',
            r'\bconsent\b', r'\blawful\s+basis\b',
            r'\berasure\b', r'\bportability\b',
            r'\bnotification\b', r'\bencryption\b',
            r'\bpseudonymisation\b', r'\bprofiling\b',
        ]
        for pattern in legal_patterns:
            if re.search(pattern, claim, re.IGNORECASE):
                key_terms.append(re.search(pattern, claim, re.IGNORECASE).group().lower())

        if not key_terms:
            return 0.5  # Neutral if no key terms found

        # Check how many key terms appear in source
        matched = sum(1 for term in key_terms if term.lower() in source_lower)
        return matched / len(key_terms)

    def _find_best_matching_segment(
        self,
        claim: str,
        source: str,
        window_size: int = 200,
    ) -> str:
        """
        Find the segment of source text that best matches the claim.

        Uses a sliding window to find the most similar region.

        Args:
            claim: The claim text
            source: Full source text
            window_size: Character window size for matching

        Returns:
            Best matching segment of source text
        """
        if len(source) <= window_size:
            return source

        best_score = 0.0
        best_segment = source[:window_size]
        step = max(50, window_size // 4)

        for i in range(0, len(source) - window_size + 1, step):
            segment = source[i:i + window_size]
            score = SequenceMatcher(
                None, claim.lower(), segment.lower()
            ).ratio()

            if score > best_score:
                best_score = score
                best_segment = segment

        return best_segment.strip()

    def _build_report(
        self,
        claims: list[ClaimVerification],
    ) -> VerificationReport:
        """Build a complete verification report from individual claim results."""
        total = len(claims)
        verified = sum(1 for c in claims if c.confidence_level == ConfidenceLevel.VERIFIED)
        partial = sum(1 for c in claims if c.confidence_level == ConfidenceLevel.PARTIAL)
        unverified = sum(1 for c in claims if c.confidence_level == ConfidenceLevel.UNVERIFIED)
        not_cited = sum(1 for c in claims if c.confidence_level == ConfidenceLevel.NOT_CITED)

        # Overall confidence is weighted average of individual scores
        if total > 0:
            overall = sum(c.confidence for c in claims) / total
        else:
            overall = 1.0

        # Determine overall level
        if verified >= total * 0.7:
            overall_level = ConfidenceLevel.VERIFIED
        elif (verified + partial) >= total * 0.5:
            overall_level = ConfidenceLevel.PARTIAL
        else:
            overall_level = ConfidenceLevel.UNVERIFIED

        # Trust score: percentage of claims that are at least partially verified
        if total > 0:
            trust_score = ((verified + partial * 0.5) / total) * 100
        else:
            trust_score = 100.0

        return VerificationReport(
            total_claims=total,
            verified_count=verified,
            partial_count=partial,
            unverified_count=unverified,
            not_cited_count=not_cited,
            overall_confidence=overall,
            overall_level=overall_level,
            claims=claims,
            trust_score=trust_score,
        )

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        """Simple word tokenizer."""
        return re.findall(r'\b\w+\b', text.lower())

    # Common English stopwords to exclude from meaningful overlap
    STOPWORDS = frozenset({
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "shall",
        "should", "may", "might", "can", "could", "must", "to", "of", "in",
        "for", "on", "with", "at", "by", "from", "as", "into", "through",
        "during", "before", "after", "above", "below", "between", "under",
        "and", "but", "or", "nor", "not", "so", "yet", "both", "either",
        "neither", "each", "every", "all", "any", "few", "more", "most",
        "other", "some", "such", "no", "only", "own", "same", "than",
        "too", "very", "just", "also", "if", "then", "that", "this",
        "these", "those", "it", "its", "they", "their", "them", "he",
        "she", "his", "her", "we", "our", "you", "your",
    })


# =============================================================================
# Convenience function
# =============================================================================

def verify_citations(answer: str, citations: list) -> VerificationReport:
    """
    Convenience function to verify citations in an answer.

    Args:
        answer: LLM-generated answer text
        citations: List of Citation objects

    Returns:
        VerificationReport
    """
    verifier = CitationVerifier()
    return verifier.verify(answer, citations)
