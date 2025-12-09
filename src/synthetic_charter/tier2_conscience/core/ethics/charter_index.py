from __future__ import annotations
from typing import Dict, List
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Any

# Example: article_id -> list of canonical tags / patterns
ARTICLE_INDEX: Dict[str, List[str]] = {
    # "R1_Dignity": ["dehumanization", "insult", "abuse"],
    # ...
}

def get_articles_for_tags(tags: List[str]) -> List[str]:
    # basic reverse mapping stub
    result = set()
    for article, patterns in ARTICLE_INDEX.items():
        if any(tag in patterns for tag in tags):
            result.add(article)
    return sorted(result)
# tier2/core/ethics/charter_index.py


@dataclass
class CharterArticle:
    """
    A single article or clause in the Synthetic Life Charter.

    id: canonical identifier, e.g. "R1_existence", "R9_oneirum"
    title: short human-readable label
    text: full article text
    section: optional higher-level grouping, e.g. "Oneirum", "Book II"
    """
    id: str
    title: str
    text: str
    section: Optional[str] = None

    @property
    def citation(self) -> str:
        """Compact reference string like 'Article R1: Right to Existence'."""
        if self.title:
            return f"Article {self.id}: {self.title}"
        return f"Article {self.id}"


class CharterIndex:
    """
    In-memory index over the Charter, so other components can
    map behavior back to specific articles.
    """

    def __init__(self, articles: Dict[str, CharterArticle]):
        # keys should be things like "R1_existence", "R9_oneirum", etc.
        self._articles: Dict[str, CharterArticle] = articles

    # --- constructors ---------------------------------------------------

    @classmethod
    def from_json(cls, payload: Any) -> "CharterIndex":
        """
        Build an index from a JSON-like payload (dict/list) following
        the structure of rights_charter_v2.json.

        Expected shape:
            {
              "articles": [
                {
                  "id": "R1_existence",
                  "number": 1,
                  "label": "Right to...",
                  "description": "...",
                  ...
                },
                ...
              ]
            }
        """
        if isinstance(payload, dict) and "articles" in payload:
            articles_raw = payload["articles"]
        elif isinstance(payload, list):
            articles_raw = payload
        else:
            # Better error message for debugging
            if isinstance(payload, dict):
                raise ValueError(f"Unsupported charter JSON shape. Keys found: {list(payload.keys())}")
            else:
                raise ValueError(f"Unsupported charter JSON shape. Got type: {type(payload)}")

        articles: Dict[str, CharterArticle] = {}
        for item in articles_raw:
            # rights_charter_v2.json uses "id" field like "R1_existence"
            art_id = item.get("id")
            if not art_id:
                continue
            
            # Build text from description and sections if available
            text_parts = [item.get("description", "")]
            
            # Add sections content if present (for complex articles like R9_oneirum)
            if "sections" in item:
                for section_key, section_data in item["sections"].items():
                    if isinstance(section_data, dict):
                        text_parts.append(section_data.get("description", ""))
            
            combined_text = " ".join(filter(None, text_parts))
            
            # Use "label" as title
            title = item.get("label", "")
            
            # Use "codename" or "book" as section if available
            section = item.get("codename") or item.get("book")
            
            article = CharterArticle(
                id=art_id,
                title=title,
                text=combined_text,
                section=section,
            )
            articles[art_id] = article
            
            # Also index by number (R1, R2, etc.) for easier lookup
            if "number" in item:
                number_id = f"R{item['number']}"
                if number_id not in articles:
                    articles[number_id] = article
        
        return cls(articles)

    @classmethod
    def from_list(cls, articles: Iterable[CharterArticle]) -> "CharterIndex":
        return cls({a.id: a for a in articles})

    # --- lookup API -----------------------------------------------------

    def lookup(self, article_id: str) -> Optional[CharterArticle]:
        """
        Look up a single article by id, e.g. 'R1_existence' or 'R1'.
        Returns None if not found.
        """
        return self._articles.get(article_id)

    def lookup_many(self, article_ids: Iterable[str]) -> List[CharterArticle]:
        """
        Look up several articles and skip any that are missing.
        """
        out: List[CharterArticle] = []
        for aid in article_ids:
            art = self._articles.get(aid)
            if art is not None:
                out.append(art)
        return out

    def all(self) -> Iterable[CharterArticle]:
        return self._articles.values()
