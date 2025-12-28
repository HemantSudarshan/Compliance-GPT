"""
change_detector.py - Regulatory Change Detection

Compares document versions to detect changes in regulation text.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from difflib import SequenceMatcher, unified_diff

# Flexible imports
try:
    from src.utils.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


@dataclass
class Change:
    """Represents a change between document versions."""
    
    change_type: str  # 'added', 'removed', 'modified'
    section: str
    old_text: Optional[str] = None
    new_text: Optional[str] = None
    similarity: float = 0.0
    page_number: Optional[int] = None
    
    def to_dict(self) -> dict:
        return {
            "change_type": self.change_type,
            "section": self.section,
            "old_text": self.old_text,
            "new_text": self.new_text,
            "similarity": self.similarity,
            "page_number": self.page_number
        }


@dataclass
class ComparisonReport:
    """Report comparing two document versions."""
    
    regulation: str
    old_version: str
    new_version: str
    total_changes: int
    additions: int
    removals: int
    modifications: int
    changes: list[Change] = field(default_factory=list)
    similarity_score: float = 0.0
    
    def to_dict(self) -> dict:
        return {
            "regulation": self.regulation,
            "old_version": self.old_version,
            "new_version": self.new_version,
            "total_changes": self.total_changes,
            "summary": {
                "additions": self.additions,
                "removals": self.removals,
                "modifications": self.modifications
            },
            "similarity_score": self.similarity_score,
            "changes": [c.to_dict() for c in self.changes]
        }
    
    def summary(self) -> str:
        return f"""
Change Detection Report: {self.regulation}
{'=' * 50}
Old Version: {self.old_version}
New Version: {self.new_version}
Overall Similarity: {self.similarity_score:.1%}

Changes Summary:
  ✅ Additions:     {self.additions}
  ❌ Removals:      {self.removals}
  ✏️ Modifications: {self.modifications}
  📊 Total:         {self.total_changes}
"""


class ChangeDetector:
    """
    Detects changes between regulation document versions.
    
    Compares parsed chunks to identify additions, removals, and modifications.
    """
    
    def __init__(self, similarity_threshold: float = 0.8):
        """
        Initialize the change detector.
        
        Args:
            similarity_threshold: Threshold for considering text as modified vs new (0-1)
        """
        self.similarity_threshold = similarity_threshold
    
    def compare_documents(
        self,
        old_chunks_path: str | Path,
        new_chunks_path: str | Path
    ) -> ComparisonReport:
        """
        Compare two document versions.
        
        Args:
            old_chunks_path: Path to old version's chunks JSON
            new_chunks_path: Path to new version's chunks JSON
            
        Returns:
            ComparisonReport with detailed changes
        """
        old_chunks = self._load_chunks(old_chunks_path)
        new_chunks = self._load_chunks(new_chunks_path)
        
        logger.info(f"Comparing {len(old_chunks)} old chunks with {len(new_chunks)} new chunks")
        
        # Build text lookup for old version
        old_texts = {self._normalize_text(c.get("text", "")): c for c in old_chunks}
        new_texts = {self._normalize_text(c.get("text", "")): c for c in new_chunks}
        
        changes = []
        additions = 0
        removals = 0
        modifications = 0
        
        # Find additions and modifications
        for norm_text, chunk in new_texts.items():
            if norm_text in old_texts:
                # Exact match - no change
                continue
            
            # Check for similar text (modification)
            best_match, best_score = self._find_best_match(norm_text, old_texts.keys())
            
            if best_match and best_score >= self.similarity_threshold:
                # Modification
                old_chunk = old_texts[best_match]
                changes.append(Change(
                    change_type="modified",
                    section=f"Chunk {chunk.get('chunk_index', 'N/A')}",
                    old_text=old_chunk.get("text", "")[:500],
                    new_text=chunk.get("text", "")[:500],
                    similarity=best_score,
                    page_number=chunk.get("page_numbers", [None])[0]
                ))
                modifications += 1
            else:
                # Addition
                changes.append(Change(
                    change_type="added",
                    section=f"Chunk {chunk.get('chunk_index', 'N/A')}",
                    new_text=chunk.get("text", "")[:500],
                    page_number=chunk.get("page_numbers", [None])[0]
                ))
                additions += 1
        
        # Find removals
        for norm_text, chunk in old_texts.items():
            if norm_text not in new_texts:
                # Check if this was a modification source
                _, best_score = self._find_best_match(norm_text, new_texts.keys())
                
                if best_score < self.similarity_threshold:
                    # Pure removal
                    changes.append(Change(
                        change_type="removed",
                        section=f"Chunk {chunk.get('chunk_index', 'N/A')}",
                        old_text=chunk.get("text", "")[:500],
                        page_number=chunk.get("page_numbers", [None])[0]
                    ))
                    removals += 1
        
        # Calculate overall similarity
        all_old_text = " ".join(c.get("text", "") for c in old_chunks)
        all_new_text = " ".join(c.get("text", "") for c in new_chunks)
        overall_similarity = SequenceMatcher(None, all_old_text, all_new_text).ratio()
        
        report = ComparisonReport(
            regulation=old_chunks[0].get("regulation", "Unknown") if old_chunks else "Unknown",
            old_version=str(old_chunks_path),
            new_version=str(new_chunks_path),
            total_changes=additions + removals + modifications,
            additions=additions,
            removals=removals,
            modifications=modifications,
            changes=changes,
            similarity_score=overall_similarity
        )
        
        return report
    
    def _load_chunks(self, path: str | Path) -> list[dict]:
        """Load chunks from JSON file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return data.get("chunks", [])
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        return " ".join(text.lower().split())
    
    def _find_best_match(
        self,
        text: str,
        candidates: list[str]
    ) -> tuple[Optional[str], float]:
        """Find the best matching text from candidates."""
        best_match = None
        best_score = 0.0
        
        for candidate in candidates:
            score = SequenceMatcher(None, text, candidate).ratio()
            if score > best_score:
                best_score = score
                best_match = candidate
        
        return best_match, best_score
    
    def generate_diff(
        self,
        old_text: str,
        new_text: str,
        context_lines: int = 3
    ) -> str:
        """
        Generate a unified diff between two texts.
        
        Args:
            old_text: Old version text
            new_text: New version text
            context_lines: Number of context lines in diff
            
        Returns:
            Unified diff string
        """
        old_lines = old_text.splitlines(keepends=True)
        new_lines = new_text.splitlines(keepends=True)
        
        diff = unified_diff(
            old_lines,
            new_lines,
            fromfile="old_version",
            tofile="new_version",
            n=context_lines
        )
        
        return "".join(diff)


def compare_regulation_versions(
    old_path: str,
    new_path: str,
    output_path: Optional[str] = None
) -> ComparisonReport:
    """
    Convenience function to compare regulation versions.
    
    Args:
        old_path: Path to old chunks JSON
        new_path: Path to new chunks JSON
        output_path: Optional path to save report
        
    Returns:
        ComparisonReport
    """
    detector = ChangeDetector()
    report = detector.compare_documents(old_path, new_path)
    
    if output_path:
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report.to_dict(), f, indent=2)
        logger.info(f"Saved comparison report to {output_path}")
    
    return report


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        old_file = sys.argv[1]
        new_file = sys.argv[2]
        output = sys.argv[3] if len(sys.argv) > 3 else None
        
        print(f"Comparing: {old_file} vs {new_file}")
        report = compare_regulation_versions(old_file, new_file, output)
        print(report.summary())
        
        if report.changes:
            print("\nTop Changes:")
            for i, change in enumerate(report.changes[:5], 1):
                print(f"  {i}. [{change.change_type.upper()}] {change.section}")
    else:
        print("Usage: python change_detector.py <old_chunks.json> <new_chunks.json> [output.json]")
