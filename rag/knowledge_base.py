"""
Simple knowledge base for RAG.

Phase 2 uses keyword-based matching.
Phase 5 will upgrade to vector search with embeddings.

Usage:
    kb = get_knowledge_base()
    results = kb.search("what is the refund policy?")
"""

import json
import os
import re
from typing import Optional

from utils.logging import get_logger

logger = get_logger(__name__)


class KnowledgeBase:
    """
    Simple keyword-based knowledge base.

    Loads documents from a JSON file and provides
    keyword search functionality.
    """

    def __init__(self, documents: Optional[list[dict]] = None):
        """
        Initialize knowledge base.

        Args:
            documents: List of documents, each with:
                - "id": Unique identifier
                - "title": Document title
                - "content": Document content
                - "category": Category tag
                - "keywords": List of keywords for matching
        """
        self.documents = documents or []
        self._index: dict[str, list[int]] = {}  # keyword → doc indices
        self._build_index()

    def _build_index(self):
        """Build a keyword index for fast searching."""
        self._index = {}

        for i, doc in enumerate(self.documents):
            # Index all keywords
            keywords = doc.get("keywords", [])
            for kw in keywords:
                kw_lower = kw.lower()
                if kw_lower not in self._index:
                    self._index[kw_lower] = []
                self._index[kw_lower].append(i)

            # Also index words from title and content
            for text in [doc.get("title", ""), doc.get("content", "")]:
                words = re.findall(r'\b\w+\b', text.lower())
                for word in words:
                    if len(word) > 3:  # Skip short words
                        if word not in self._index:
                            self._index[word] = []
                        if i not in self._index[word]:
                            self._index[word].append(i)

        logger.info(
            "knowledge_base_indexed",
            num_documents=len(self.documents),
            index_size=len(self._index),
        )

    def search(self, query: str, top_k: int = 3) -> list[str]:
        """
        Search the knowledge base.

        Args:
            query: Search query
            top_k: Number of results to return

        Returns:
            List of relevant document content strings
        """
        query_words = re.findall(r'\b\w+\b', query.lower())

        # Score each document by number of matching keywords
        scores: dict[int, int] = {}
        for word in query_words:
            if word in self._index:
                for doc_idx in self._index[word]:
                    scores[doc_idx] = scores.get(doc_idx, 0) + 1
            # Also check for partial matches in the index
            for index_key in self._index:
                if word in index_key or index_key in word:
                    for doc_idx in self._index[index_key]:
                        scores[doc_idx] = scores.get(doc_idx, 0) + 1

        if not scores:
            return []

        # Sort by score (descending)
        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        # Return top_k results
        results = []
        for doc_idx, score in sorted_docs[:top_k]:
            content = self.documents[doc_idx].get("content", "")
            results.append(content)

        logger.info(
            "knowledge_search",
            query=query,
            num_results=len(results),
            top_score=sorted_docs[0][1] if sorted_docs else 0,
        )

        return results

    def add_document(self, doc: dict):
        """Add a new document to the knowledge base."""
        self.documents.append(doc)
        self._build_index()

    def load_from_json(self, path: str):
        """Load documents from a JSON file."""
        try:
            with open(path, "r") as f:
                data = json.load(f)

            if isinstance(data, list):
                self.documents = data
            elif isinstance(data, dict) and "documents" in data:
                self.documents = data["documents"]

            self._build_index()
            logger.info("knowledge_base_loaded", path=path, num_documents=len(self.documents))

        except FileNotFoundError:
            logger.warning("knowledge_base_file_not_found", path=path)
        except json.JSONDecodeError as e:
            logger.error("knowledge_base_json_error", path=path, error=str(e))


# ─────────────────────────────────────────────
# DEFAULT KNOWLEDGE BASE
# ─────────────────────────────────────────────

DEFAULT_DOCUMENTS = [
    {
        "id": "kb_001",
        "title": "Acme Corp Overview",
        "content": "Acme Corp is a leading provider of cloud-based business solutions. We offer three main plans: Basic, Premium, and Enterprise. Our headquarters is in San Francisco, and we serve over 10,000 customers worldwide.",
        "category": "company",
        "keywords": ["acme", "company", "overview", "about", "who"],
    },
    {
        "id": "kb_002",
        "title": "Refund Policy",
        "content": "We offer a 30-day money-back guarantee on all plans. If you're not satisfied, you can request a full refund within 30 days of purchase. After 30 days, we offer prorated refunds for annual plans. To request a refund, contact our billing department.",
        "category": "policy",
        "keywords": ["refund", "money back", "guarantee", "cancel", "return", "billing"],
    },
    {
        "id": "kb_003",
        "title": "API Access",
        "content": "API access is available on Premium and Enterprise plans. The API supports REST and WebSocket connections. Rate limits are 1000 requests per minute for Premium and unlimited for Enterprise. API documentation is available at docs.acmecorp.com.",
        "category": "technical",
        "keywords": ["api", "developer", "integration", "rest", "webhook", "technical"],
    },
    {
        "id": "kb_004",
        "title": "Data Security",
        "content": "All data is encrypted at rest using AES-256 and in transit using TLS 1.3. We are SOC 2 Type II certified and GDPR compliant. Enterprise plans include the option for on-premise deployment. Data backups are performed every 6 hours.",
        "category": "security",
        "keywords": ["security", "encryption", "gdpr", "compliance", "soc", "data", "privacy"],
    },
    {
        "id": "kb_005",
        "title": "Support Hours",
        "content": "Basic plan includes email support with 24-hour response time. Premium plan includes priority support with 4-hour response time, available Monday to Friday 8am to 8pm EST. Enterprise plan includes 24/7 dedicated support with 1-hour response time.",
        "category": "support",
        "keywords": ["support", "hours", "help", "contact", "response time", "phone"],
    },
    {
        "id": "kb_006",
        "title": "Free Trial",
        "content": "We offer a 14-day free trial for the Premium plan. No credit card required to start. You get full access to all Premium features during the trial. At the end of the trial, you can choose to upgrade or downgrade to any plan.",
        "category": "sales",
        "keywords": ["free trial", "trial", "demo", "try", "test", "no credit card"],
    },
    {
        "id": "kb_007",
        "title": "Migration Assistance",
        "content": "We offer free migration assistance for all plans. Our team will help you import your data from your current provider. Premium and Enterprise plans include dedicated migration specialists. Typical migration takes 2-5 business days.",
        "category": "support",
        "keywords": ["migration", "import", "switch", "transfer data", "move", "migrate"],
    },
    {
        "id": "kb_008",
        "title": "Custom Integrations",
        "content": "Custom integrations are available on Premium and Enterprise plans. We support Salesforce, HubSpot, Slack, and Zapier integrations out of the box. Enterprise plans include custom API development. Integration setup typically takes 1-3 business days.",
        "category": "technical",
        "keywords": ["integration", "salesforce", "hubspot", "slack", "zapier", "connect"],
    },
]


# ─────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────

_knowledge_base: Optional[KnowledgeBase] = None


def get_knowledge_base() -> KnowledgeBase:
    """
    Get or create the knowledge base singleton.

    Loads from JSON file if configured, otherwise uses default documents.
    """
    global _knowledge_base

    if _knowledge_base is None:
        _knowledge_base = KnowledgeBase(documents=DEFAULT_DOCUMENTS)

        # Load additional documents from file if configured
        from config import config
        if config.knowledge_base_path and os.path.exists(config.knowledge_base_path):
            _knowledge_base.load_from_json(config.knowledge_base_path)

    return _knowledge_base