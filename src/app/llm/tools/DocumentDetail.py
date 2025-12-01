"""
DocumentDetail Tool - Fetches full content from specific documents.

Retrieves detailed content from documentation files based on doc IDs
identified through DocumentSummary.

Source: docs/context/zh-TW/*.md (Details sections)
"""
import dspy
from pathlib import Path
from typing import Dict, List, Union
from functools import lru_cache


# Mapping of doc IDs to file names
DOC_ID_MAP = {
    "01": "01_mission_and_vision.md",
    "02": "02_business_model.md",
    "03": "03_platform_features.md",
    "04": "04_values_and_culture.md",
    "05": "05_tech_infrastructure.md",
    "06": "06_membership_program.md",
    "07": "07_event_categories.md",
    "08": "08_customer_service.md",
    "09": "09_contact_information.md",
}


@lru_cache(maxsize=32)
def _load_document_detail(doc_id: str) -> str:
    """
    Load detail section from a specific document.
    Cached to avoid repeated file reads.

    Args:
        doc_id: Document ID (01-05)

    Returns:
        Detail content from the document
    """
    context_dir = Path(__file__).parent.parent.parent.parent.parent / "docs" / "context" / "zh-TW"

    if doc_id not in DOC_ID_MAP:
        raise ValueError(f"Invalid doc_id: {doc_id}. Valid IDs: {list(DOC_ID_MAP.keys())}")

    file_path = context_dir / DOC_ID_MAP[doc_id]

    if not file_path.exists():
        raise FileNotFoundError(f"Document file not found: {file_path}")

    content = file_path.read_text(encoding="utf-8")

    # Extract Details section (between ## Details and end of file)
    if "## Details" in content:
        details_start = content.find("## Details")
        details = content[details_start:].strip()
    else:
        # Fallback: Return full content if no Details section
        details = f"## Details\n\n{content}"

    return f"**[{doc_id}] {DOC_ID_MAP[doc_id]}**\n\n{details}"


def _get_document_detail(doc_ids: Union[str, List[str]]) -> Dict[str, str]:
    """
    Retrieves detailed content from specified documents.

    Args:
        doc_ids: Single doc ID ("01") or list (["01", "04"])

    Returns:
        Dictionary with combined content and list of fetched docs
    """
    try:
        # Normalize to list
        if isinstance(doc_ids, str):
            doc_ids_list = [doc_ids]
        else:
            doc_ids_list = doc_ids

        # Validate all doc IDs
        invalid_ids = [doc_id for doc_id in doc_ids_list if doc_id not in DOC_ID_MAP]
        if invalid_ids:
            return {
                "content": f"Error: Invalid document IDs: {invalid_ids}. "
                          f"Valid IDs are: {list(DOC_ID_MAP.keys())}",
                "fetched_docs": []
            }

        # Load all requested documents
        details = []
        for doc_id in doc_ids_list:
            detail_content = _load_document_detail(doc_id)
            details.append(detail_content)

        combined_content = "\n\n---\n\n".join(details)

        return {
            "content": combined_content,
            "fetched_docs": doc_ids_list
        }

    except Exception as e:
        return {
            "content": f"Error loading document details: {e}",
            "fetched_docs": []
        }


# Create DSPy Tool
DocumentDetail = dspy.Tool(
    func=_get_document_detail,
    name="document_detail",
    desc="""Fetch detailed content from specific documentation files.

Parameters:
- doc_ids: Document ID(s) to fetch - use "01" through "09"
           Can be single string ("01") or list (["01", "04", "06"])

Available documents:
- 01: Mission & Vision (company mission, vision, support for creators)
- 02: Business Model (revenue sources, commercial partnerships, value proposition)
- 03: Platform Features (event discovery, ticketing, AI assistant, user experience)
- 04: Values & Culture (core values, company culture, ShowEasy.ai overview)
- 05: Tech Infrastructure (AI systems, cloud architecture, security, OMO integration)
- 06: Membership Program (tiers, benefits, pricing, upgrade strategy)
- 07: Event Categories (activity types, Hong Kong originals, Meta Stages)
- 08: Customer Service (service philosophy, tone, handling difficult situations)
- 09: Contact Information (support channels, office location, escalation procedures)

Use this tool AFTER DocumentSummary to get full details for relevant documents.

Examples:
- Membership question: doc_ids="02"
- Platform + contact: doc_ids=["01", "05"]
- Ticket policies: doc_ids=["01", "04"]"""
)
