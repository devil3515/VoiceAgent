"""
Knowledge search tool (RAG).

Searches the company knowledge base for relevant information.
Phase 2 uses simple keyword matching — upgrades to vector search in Phase 5.
"""

from rag.knowledge_base import KnowledgeBase, get_knowledge_base
from utils.logging import get_logger

logger=get_logger(__name__)


async def search_knowledge(query: str) -> str:
    """
    Search the knowledge base for relevant information.

    Args:
        query: Search query or question

    Returns:
        Relevant information from the knowledge base
    """
    logger.info("knowledge_search", query=query)

    kb = get_knowledge_base()
    results = kb.search(query, top_k=3)

    if not results:
        return "I couldn't find specific information about that. Let me transfer you to someone who can help."

    # Combine results into a single response
    combined = " ".join(results)

    # Truncate if too long (for voice, keep it short)
    if len(combined) > 500:
        combined = combined[:497] + "..."

    return combined