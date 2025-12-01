"""
DocumentSummary Tool - Provides high-level index of all documentation.

Returns summaries from all context documents to help the LLM decide
which documents need detailed retrieval.

Source: docs/context/zh-TW/*.md (Summary sections)
"""
import dspy
from pathlib import Path
from typing import Dict
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_all_summaries() -> str:
    """
    Load summary sections from all context documents.

    Returns:
        Combined summaries from all markdown files
    """
    context_dir = Path(__file__).parent.parent.parent.parent.parent / "docs" / "context" / "zh-TW"

    # Get all markdown files except README
    md_files = sorted([f for f in context_dir.glob("*.md") if f.name != "README.md"])

    summaries = []
    for md_file in md_files:
        doc_id = md_file.stem.split("_")[0]  # Extract "01" from "01_platform_overview"
        content = md_file.read_text(encoding="utf-8")

        # Extract Summary section (between ## Summary and next ##)
        if "## Summary" in content:
            summary_start = content.find("## Summary")
            summary_end = content.find("\n## ", summary_start + 10)
            if summary_end == -1:
                summary_end = len(content)
            summary = content[summary_start:summary_end].strip()
        else:
            # Fallback: First 10 lines as summary
            lines = content.split("\n")[:10]
            summary = f"## Summary\nDocument ID: {doc_id}\n" + "\n".join(lines)

        summaries.append(f"**[{doc_id}] {md_file.stem}**\n{summary}")

    return "\n\n---\n\n".join(summaries)


def _get_document_summary() -> Dict[str, str]:
    """
    Retrieves summaries of all available documentation.

    Returns:
        Dictionary with combined summaries
    """
    try:
        summaries = _load_all_summaries()
        return {"summaries": summaries}
    except Exception as e:
        return {"summaries": f"Error loading document summaries: {e}"}


# Create DSPy Tool
DocumentSummary = dspy.Tool(
    func=_get_document_summary,
    name="document_summary",
    desc="""Get high-level summaries of all available documentation.

Use this tool FIRST when users ask questions about:
- Platform features or policies
- Membership information
- Ticket purchasing
- Customer service
- Contact information
- General platform questions

This tool returns summaries of all documents, allowing you to identify which
documents contain relevant information before fetching full details.

Always use this before DocumentDetail to avoid loading unnecessary content."""
)
