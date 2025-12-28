"""
table_linearizer.py - Table to Text Conversion

Converts extracted tables into readable text format while preserving structure.
"""

from typing import Optional
import re
import logging

# Flexible imports for different execution contexts
try:
    from src.utils.logger import setup_logger
    logger = setup_logger(__name__)
except ImportError:
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)


class TableLinearizer:
    """
    Converts table elements to readable text format.
    
    Handles various table formats from Unstructured.io output
    and converts them to a consistent, searchable text representation.
    """
    
    def __init__(self, format_style: str = "markdown"):
        """
        Initialize the table linearizer.
        
        Args:
            format_style: Output format ('markdown', 'text', 'structured')
        """
        self.format_style = format_style
    
    def linearize(self, table_content: str, table_html: Optional[str] = None) -> str:
        """
        Convert table content to linear text.
        
        Args:
            table_content: Raw table text content
            table_html: Optional HTML representation of the table
            
        Returns:
            Linearized text representation
        """
        if table_html:
            return self._linearize_html_table(table_html)
        else:
            return self._linearize_text_table(table_content)
    
    def _linearize_html_table(self, html: str) -> str:
        """Convert HTML table to text format."""
        try:
            # Simple HTML table parsing
            rows = re.findall(r'<tr[^>]*>(.*?)</tr>', html, re.DOTALL | re.IGNORECASE)
            
            table_data = []
            for row in rows:
                cells = re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>', row, re.DOTALL | re.IGNORECASE)
                # Clean HTML tags from cells
                cleaned_cells = [self._clean_html(cell) for cell in cells]
                table_data.append(cleaned_cells)
            
            if not table_data:
                return html  # Return original if parsing fails
            
            return self._format_table_data(table_data)
            
        except Exception as e:
            logger.warning(f"Failed to parse HTML table: {e}")
            return html
    
    def _linearize_text_table(self, text: str) -> str:
        """Convert plain text table to structured format."""
        lines = text.strip().split('\n')
        
        # Try to detect if it's already a formatted table
        if any('|' in line for line in lines):
            return self._parse_pipe_table(lines)
        elif any('\t' in line for line in lines):
            return self._parse_tab_table(lines)
        else:
            # Just clean up spacing and return
            return self._clean_text_table(text)
    
    def _parse_pipe_table(self, lines: list[str]) -> str:
        """Parse pipe-delimited table."""
        table_data = []
        for line in lines:
            if line.strip() and not line.strip().startswith('---'):
                cells = [cell.strip() for cell in line.split('|') if cell.strip()]
                if cells:
                    table_data.append(cells)
        
        return self._format_table_data(table_data)
    
    def _parse_tab_table(self, lines: list[str]) -> str:
        """Parse tab-delimited table."""
        table_data = []
        for line in lines:
            if line.strip():
                cells = [cell.strip() for cell in line.split('\t')]
                table_data.append(cells)
        
        return self._format_table_data(table_data)
    
    def _clean_text_table(self, text: str) -> str:
        """Clean up plain text table representation."""
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        # Add line breaks for readability
        text = re.sub(r'([.!?])\s+', r'\1\n', text)
        return text.strip()
    
    def _format_table_data(self, table_data: list[list[str]]) -> str:
        """Format table data based on style."""
        if not table_data:
            return ""
        
        if self.format_style == "markdown":
            return self._to_markdown(table_data)
        elif self.format_style == "structured":
            return self._to_structured(table_data)
        else:
            return self._to_text(table_data)
    
    def _to_markdown(self, table_data: list[list[str]]) -> str:
        """Convert to markdown table format."""
        if not table_data:
            return ""
        
        lines = []
        
        # Header row
        header = table_data[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("| " + " | ".join(["---"] * len(header)) + " |")
        
        # Data rows
        for row in table_data[1:]:
            # Pad row if needed
            while len(row) < len(header):
                row.append("")
            lines.append("| " + " | ".join(row[:len(header)]) + " |")
        
        return "\n".join(lines)
    
    def _to_structured(self, table_data: list[list[str]]) -> str:
        """Convert to structured key-value format."""
        if not table_data or len(table_data) < 2:
            return self._to_text(table_data)
        
        lines = []
        headers = table_data[0]
        
        for i, row in enumerate(table_data[1:], 1):
            lines.append(f"Row {i}:")
            for j, cell in enumerate(row):
                header = headers[j] if j < len(headers) else f"Column {j+1}"
                if cell.strip():
                    lines.append(f"  - {header}: {cell}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _to_text(self, table_data: list[list[str]]) -> str:
        """Convert to plain text format."""
        lines = []
        for row in table_data:
            lines.append(" | ".join(row))
        return "\n".join(lines)
    
    def _clean_html(self, html: str) -> str:
        """Remove HTML tags from text."""
        # Remove tags
        text = re.sub(r'<[^>]+>', '', html)
        # Decode entities
        text = text.replace('&nbsp;', ' ')
        text = text.replace('&amp;', '&')
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&quot;', '"')
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text)
        return text.strip()


def linearize_table(
    content: str,
    html: Optional[str] = None,
    format_style: str = "markdown"
) -> str:
    """
    Convenience function to linearize a table.
    
    Args:
        content: Table content text
        html: Optional HTML representation
        format_style: Output format style
        
    Returns:
        Linearized table text
    """
    linearizer = TableLinearizer(format_style=format_style)
    return linearizer.linearize(content, html)
