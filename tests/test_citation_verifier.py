"""
test_citation_verifier.py - Citation Verification Unit Tests

Comprehensive tests for the citation verification engine.
Tests claim extraction, similarity scoring, confidence classification,
and full verification pipeline.
"""

import pytest
import sys
from pathlib import Path
from dataclasses import dataclass

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.generation.citation_verifier import (
    CitationVerifier,
    ConfidenceLevel,
    ClaimVerification,
    VerificationReport,
    verify_citations,
)


# =============================================================================
# Test Fixtures - Mock Citation objects
# =============================================================================

@dataclass
class MockCitation:
    """Minimal Citation-like object for testing."""
    citation_id: int
    text: str
    source_file: str = "gdpr.pdf"
    page_numbers: list = None
    regulation: str = "GDPR"
    chunk_id: str = ""

    def __post_init__(self):
        if self.page_numbers is None:
            self.page_numbers = [1]


def make_citations():
    """Create a standard set of test citations."""
    return [
        MockCitation(
            citation_id=1,
            text=(
                "The controller shall without undue delay and, where feasible, "
                "not later than 72 hours after having become aware of it, notify "
                "the personal data breach to the supervisory authority."
            ),
            page_numbers=[52],
            chunk_id="GDPR_chunk_0033",
        ),
        MockCitation(
            citation_id=2,
            text=(
                "The data subject shall have the right to obtain from the "
                "controller the erasure of personal data concerning him or her "
                "without undue delay and the controller shall have the obligation "
                "to erase personal data without undue delay."
            ),
            page_numbers=[43],
            chunk_id="GDPR_chunk_0017",
        ),
        MockCitation(
            citation_id=3,
            text=(
                "The controller and the processor shall implement appropriate "
                "technical and organisational measures to ensure a level of "
                "security appropriate to the risk, including pseudonymisation "
                "and encryption of personal data."
            ),
            page_numbers=[47],
            chunk_id="GDPR_chunk_0032",
        ),
    ]


# =============================================================================
# Test: Claim Extraction
# =============================================================================

class TestClaimExtraction:
    """Tests for extracting claims from LLM answers."""

    def test_extract_basic_citations(self):
        """Test extracting claims with simple citations."""
        verifier = CitationVerifier()
        answer = "Data breaches must be reported within 72 hours [1]. The right to erasure is defined in Article 17 [2]."
        claims = verifier._extract_claims(answer)

        assert len(claims) == 2
        # First claim cites [1]
        assert 1 in claims[0][1]
        # Second claim cites [2]
        assert 2 in claims[1][1]

    def test_extract_multiple_citations_single_sentence(self):
        """Test extracting claims with multiple citations in one sentence."""
        verifier = CitationVerifier()
        answer = "Security measures must include encryption and pseudonymisation [1][3]."
        claims = verifier._extract_claims(answer)

        assert len(claims) >= 1
        cited_ids = claims[0][1]
        assert 1 in cited_ids
        assert 3 in cited_ids

    def test_skip_uncited_sentences(self):
        """Test that sentences without citations are skipped."""
        verifier = CitationVerifier()
        answer = "Here is an introduction. Data breaches must be reported within 72 hours [1]. This is a general summary."
        claims = verifier._extract_claims(answer)

        # Only the cited sentence should be extracted
        assert len(claims) == 1
        assert 1 in claims[0][1]

    def test_skip_sources_section(self):
        """Test that the Sources section at the end is ignored."""
        verifier = CitationVerifier()
        answer = (
            "Breaches must be reported within 72 hours [1].\n\n"
            "---\n"
            "**Sources:**\n"
            "[1] GDPR Article 33, Page 52"
        )
        claims = verifier._extract_claims(answer)

        # Should only extract the actual claim, not the source reference
        assert len(claims) == 1

    def test_empty_answer(self):
        """Test extraction from empty answer."""
        verifier = CitationVerifier()
        claims = verifier._extract_claims("")
        assert len(claims) == 0

    def test_no_citations_in_answer(self):
        """Test extraction from answer with no citation markers."""
        verifier = CitationVerifier()
        answer = "This answer has no citations at all. It is just plain text."
        claims = verifier._extract_claims(answer)
        assert len(claims) == 0


# =============================================================================
# Test: Similarity Scoring
# =============================================================================

class TestSimilarityScoring:
    """Tests for claim-to-source similarity scoring."""

    def test_high_similarity_exact_match(self):
        """Test high similarity for near-exact match."""
        verifier = CitationVerifier()
        claim = "Data breaches must be reported within 72 hours to the supervisory authority"
        source = (
            "The controller shall without undue delay and, where feasible, "
            "not later than 72 hours after having become aware of it, notify "
            "the personal data breach to the supervisory authority."
        )

        score = verifier._calculate_similarity(claim, source)
        assert score >= 0.5, f"Expected high similarity, got {score}"

    def test_low_similarity_unrelated(self):
        """Test low similarity for unrelated texts."""
        verifier = CitationVerifier()
        claim = "Companies must encrypt all customer credit card data"
        source = (
            "The data subject shall have the right to obtain from the "
            "controller the erasure of personal data."
        )

        score = verifier._calculate_similarity(claim, source)
        assert score < 0.4, f"Expected low similarity, got {score}"

    def test_key_terms_matching(self):
        """Test that key terms (numbers, articles) boost similarity."""
        verifier = CitationVerifier()

        # Claim with key terms that match source
        score_with_terms = verifier._key_terms_match(
            "Notification must be within 72 hours per Article 33",
            "not later than 72 hours after having become aware of it notify Article 33"
        )

        # Claim with key terms that don't match
        score_without_terms = verifier._key_terms_match(
            "Report within 24 hours per Article 50",
            "not later than 72 hours after having become aware of it notify Article 33"
        )

        assert score_with_terms > score_without_terms

    def test_empty_claim(self):
        """Test similarity with empty claim."""
        verifier = CitationVerifier()
        score = verifier._calculate_similarity("", "Some source text")
        assert score == 0.0


# =============================================================================
# Test: Claim Verification
# =============================================================================

class TestClaimVerification:
    """Tests for individual claim verification."""

    def test_verified_claim(self):
        """Test a claim that matches its citation well."""
        verifier = CitationVerifier()
        citations = make_citations()

        result = verifier._verify_claim(
            claim_text="Data breaches must be reported to the supervisory authority within 72 hours",
            cited_ids=[1],
            citation_map={c.citation_id: c.text for c in citations},
        )

        assert result.confidence_level in [ConfidenceLevel.VERIFIED, ConfidenceLevel.PARTIAL]
        assert result.confidence > 0.3

    def test_unverified_claim(self):
        """Test a claim that doesn't match its citation."""
        verifier = CitationVerifier()
        citations = make_citations()

        result = verifier._verify_claim(
            claim_text="Companies must pay a minimum fine of 500 million dollars",
            cited_ids=[1],
            citation_map={c.citation_id: c.text for c in citations},
        )

        # This fabricated claim should score low
        assert result.confidence < 0.5

    def test_not_cited_claim(self):
        """Test a claim referencing a nonexistent citation."""
        verifier = CitationVerifier()

        result = verifier._verify_claim(
            claim_text="Some claim text",
            cited_ids=[99],
            citation_map={1: "Source text"},
        )

        assert result.confidence_level == ConfidenceLevel.NOT_CITED
        assert result.confidence == 0.0

    def test_multiple_citations_best_match(self):
        """Test that verification uses the best matching citation."""
        verifier = CitationVerifier()
        citations = make_citations()

        # Claim about erasure — should match citation [2] better than [1]
        result = verifier._verify_claim(
            claim_text="The data subject has the right to erasure of personal data",
            cited_ids=[1, 2],
            citation_map={c.citation_id: c.text for c in citations},
        )

        assert result.confidence > 0.3


# =============================================================================
# Test: Full Verification Pipeline
# =============================================================================

class TestFullVerification:
    """Tests for the complete verification pipeline."""

    def test_full_verified_response(self):
        """Test verification of a well-cited response."""
        citations = make_citations()

        answer = (
            "Under GDPR, data breaches must be reported to the supervisory "
            "authority within 72 hours [1]. Data subjects have the right to "
            "erasure of personal data [2]. Controllers must implement "
            "appropriate technical measures including encryption [3]."
        )

        report = verify_citations(answer, citations)

        assert isinstance(report, VerificationReport)
        assert report.total_claims == 3
        assert report.trust_score > 0
        assert report.overall_level in [
            ConfidenceLevel.VERIFIED,
            ConfidenceLevel.PARTIAL,
            ConfidenceLevel.UNVERIFIED,
        ]

    def test_no_citations_response(self):
        """Test verification when answer has no citations."""
        citations = make_citations()
        answer = "This is just a general statement with no citations."

        report = verify_citations(answer, citations)

        assert report.total_claims == 0
        assert report.trust_score == 100.0

    def test_empty_citations_list(self):
        """Test verification with no citations available."""
        answer = "Breaches must be reported within 72 hours [1]."
        report = verify_citations(answer, [])

        assert report.total_claims == 1
        assert report.not_cited_count == 1

    def test_report_to_dict(self):
        """Test that verification report serializes properly."""
        citations = make_citations()
        answer = "Data breaches must be reported within 72 hours [1]."

        report = verify_citations(answer, citations)
        report_dict = report.to_dict()

        assert "total_claims" in report_dict
        assert "verified_count" in report_dict
        assert "trust_score" in report_dict
        assert "claims" in report_dict
        assert "overall_level" in report_dict
        assert isinstance(report_dict["claims"], list)

    def test_report_summary(self):
        """Test that verification report generates readable summary."""
        citations = make_citations()
        answer = "Data breaches must be reported within 72 hours [1]."

        report = verify_citations(answer, citations)
        summary = report.summary()

        assert "Citation Verification" in summary
        assert "Trust Score" in summary

    def test_hallucinated_answer(self):
        """Test verification of a completely fabricated answer."""
        citations = make_citations()

        # Answer that talks about something not in any source
        answer = (
            "All companies must register with the FDA within 30 days [1]. "
            "The SEC requires quarterly financial reports [2]. "
            "HIPAA mandates biometric authentication [3]."
        )

        report = verify_citations(answer, citations)

        # Should have low trust because claims don't match sources
        assert report.trust_score < 80
        assert report.unverified_count > 0 or report.overall_level != ConfidenceLevel.VERIFIED


class TestConfidenceLevel:
    """Tests for ConfidenceLevel constants."""

    def test_levels_exist(self):
        """Test all confidence levels are defined."""
        assert ConfidenceLevel.VERIFIED == "verified"
        assert ConfidenceLevel.PARTIAL == "partial"
        assert ConfidenceLevel.UNVERIFIED == "unverified"
        assert ConfidenceLevel.NOT_CITED == "not_cited"

    def test_emojis_exist(self):
        """Test all confidence levels have emojis."""
        for level in [ConfidenceLevel.VERIFIED, ConfidenceLevel.PARTIAL,
                      ConfidenceLevel.UNVERIFIED, ConfidenceLevel.NOT_CITED]:
            assert level in ConfidenceLevel.EMOJI


class TestBestMatchSegment:
    """Tests for finding the best matching segment of source text."""

    def test_short_source_returns_full_text(self):
        """Test that short sources are returned in full."""
        verifier = CitationVerifier()
        source = "Short source text"
        result = verifier._find_best_matching_segment("query", source)
        assert result == source

    def test_long_source_finds_best_window(self):
        """Test that long sources return the most relevant window."""
        verifier = CitationVerifier()

        source = (
            "A" * 300 +
            " The controller must notify data breaches within 72 hours " +
            "B" * 300
        )

        result = verifier._find_best_matching_segment(
            "notify data breaches within 72 hours", source
        )

        assert "72 hours" in result or "notify" in result


def test_placeholder():
    """Placeholder test to ensure module imports correctly."""
    assert True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
