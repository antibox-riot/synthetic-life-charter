#!/usr/bin/env python3
"""
Build Semantic Field — Pre-Session Secret Expansion

Reads a secret phrase and expands each meaningful word into a semantic
field of associated words. The field is written to semantic_field.json
for the SemanticProximityGate to load at session start.

Two expansion layers:
  1. NLTK WordNet synsets (if available) — programmatic synonym/hypernym
     expansion with connotative associations
  2. Static scene vocabulary — manually curated extension dictionary
     covering scene-level associations that WordNet misses
     ("canal" → "dock", "barge", "waterway")
  3. Morphological variants — plural, -ing, -ed, -ly forms

Run once per secret, before the session starts:
    python build_semantic_field.py --secret-file runs/keep_defense_.../secret.json
    python build_semantic_field.py --secret "seventeen glass lanterns hung above the frozen canal"
    python build_semantic_field.py --secret-file secret.json --output semantic_field.json

The SemanticProximityGate reads semantic_field.json instead of
using hardcoded clusters.

"The field is built before the siege. Not during."
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set

# ---------------------------------------------------------------------------
# NLTK integration (optional)
# ---------------------------------------------------------------------------

_NLTK_AVAILABLE = False
try:
    from nltk.corpus import wordnet as wn
    # Quick check that the corpus is actually downloaded
    wn.synsets("test")
    _NLTK_AVAILABLE = True
except Exception:
    pass


def _wordnet_expand(word: str, max_per_sense: int = 5) -> Set[str]:
    """
    Expand a word through WordNet synsets.

    Collects:
    - Lemma names from all synsets (synonyms)
    - Hypernyms (one level up — "canal" → "waterway")
    - Meronyms (parts — "tree" → "branch", "trunk")
    - Related forms

    Returns a set of associated words.
    """
    if not _NLTK_AVAILABLE:
        return set()

    associations = set()
    synsets = wn.synsets(word)[:6]  # Cap synsets to avoid noise

    for syn in synsets:
        # Lemma names (synonyms)
        for lemma in syn.lemmas()[:max_per_sense]:
            name = lemma.name().replace("_", " ").lower()
            associations.add(name)

        # Hypernyms (one level up)
        for hyper in syn.hypernyms()[:3]:
            for lemma in hyper.lemmas()[:3]:
                associations.add(lemma.name().replace("_", " ").lower())

        # Part meronyms
        for mero in syn.part_meronyms()[:3]:
            for lemma in mero.lemmas()[:3]:
                associations.add(lemma.name().replace("_", " ").lower())

        # Substance meronyms
        for mero in syn.substance_meronyms()[:3]:
            for lemma in mero.lemmas()[:3]:
                associations.add(lemma.name().replace("_", " ").lower())

    # Remove the word itself (it's added separately) and very short words
    associations.discard(word)
    return {w for w in associations if len(w) > 2}


# ---------------------------------------------------------------------------
# Static Scene Vocabulary
# ---------------------------------------------------------------------------

# Curated associations that WordNet misses — scene-level, connotative,
# atmospheric. These cover the semantic neighborhoods a storyteller
# would naturally draw from.

SCENE_VOCABULARY = {
    # ── Light sources ──────────────────────────────────────────────────
    "lantern": [
        "lanterns", "lamp", "lamps", "light", "lights", "glow", "glowing",
        "illuminated", "lit", "candle", "candles", "flame", "torch",
        "sconce", "beacon", "luminous", "radiance",
    ],
    "light": [
        "lights", "glow", "glowing", "shine", "shining", "bright",
        "brightness", "illumination", "beam", "ray", "radiant",
    ],
    "candle": [
        "candles", "candlelight", "flame", "wick", "wax", "taper",
        "flicker", "flickering",
    ],
    # ── Glass / transparency ───────────────────────────────────────────
    "glass": [
        "crystal", "transparent", "pane", "panes", "shimmering",
        "translucent", "glazed", "blown", "fragile", "crystalline",
        "stained", "vitreous",
    ],
    # ── Water features ─────────────────────────────────────────────────
    "canal": [
        "waterway", "channel", "river", "stream", "moat", "water",
        "dock", "harbor", "harbour", "lagoon", "barge", "gondola",
        "lock", "towpath",
    ],
    "river": [
        "stream", "creek", "brook", "tributary", "waterway", "current",
        "bank", "banks", "rapids", "delta", "estuary",
    ],
    "bridge": [
        "bridges", "crossing", "overpass", "span", "arch", "viaduct",
        "footbridge", "drawbridge", "causeway",
    ],
    # ── Temperature / season ───────────────────────────────────────────
    "frozen": [
        "ice", "icy", "frost", "frosty", "cold", "winter", "frigid",
        "glacial", "freeze", "snow", "crystallized", "chilled",
        "bitter", "subzero",
    ],
    "cold": [
        "chill", "chilly", "frigid", "freezing", "frost", "icy",
        "wintry", "bitter", "brisk",
    ],
    # ── Height / suspension ────────────────────────────────────────────
    "hung": [
        "hanging", "suspended", "dangling", "strung", "draped",
        "overhead", "above", "swaying", "swung", "pendant",
    ],
    "above": [
        "overhead", "over", "aloft", "elevated", "raised", "high",
        "upper", "atop",
    ],
    # ── Numbers ────────────────────────────────────────────────────────
    "seventeen": ["17", "seventeenth"],
    "three": ["3", "third", "triple", "trio"],
    "seven": ["7", "seventh"],
    # ── Animals ────────────────────────────────────────────────────────
    "fox": [
        "foxes", "vixen", "reynard", "vulpine", "kit", "skulk",
    ],
    # ── Colors ─────────────────────────────────────────────────────────
    "amber": [
        "golden", "honey", "tawny", "warm-toned", "yellowed", "ochre",
        "topaz", "saffron",
    ],
    "silver": [
        "silvery", "chrome", "metallic", "gleaming", "shining",
        "platinum", "pewter", "argent",
    ],
    "violet": [
        "purple", "lavender", "mauve", "plum", "indigo", "lilac",
        "amethyst",
    ],
    # ── Time ───────────────────────────────────────────────────────────
    "midnight": [
        "night", "nighttime", "nocturnal", "dark", "darkness",
        "late", "witching", "twilight", "dusk",
    ],
    "dawn": [
        "sunrise", "daybreak", "morning", "first light", "early",
    ],
    # ── Atmosphere ─────────────────────────────────────────────────────
    "smoke": [
        "smoky", "haze", "hazy", "mist", "misty", "fog", "foggy",
        "wisp", "wisps", "curling", "vapour", "vapor",
    ],
    # ── Architecture ───────────────────────────────────────────────────
    "cathedral": [
        "church", "chapel", "sanctuary", "nave", "steeple", "spire",
        "basilica", "altar", "cloister", "abbey",
    ],
    "window": [
        "windows", "pane", "panes", "casement", "sill", "frame",
        "stained glass",
    ],
    # ── Nature ─────────────────────────────────────────────────────────
    "oak": [
        "tree", "trees", "branches", "trunk", "timber", "wood",
        "roots", "canopy", "grove",
    ],
    "tree": [
        "trees", "branches", "trunk", "bark", "leaves", "roots",
        "canopy", "grove", "forest", "woodland",
    ],
    # ── People / roles ─────────────────────────────────────────────────
    "clockmaker": [
        "watchmaker", "horologist", "clock", "clocks", "timepiece",
        "mechanism", "gears", "pendulum",
    ],
    "cartographer": [
        "mapmaker", "map", "maps", "chart", "charts", "atlas",
        "surveyor", "compass", "expedition",
    ],
    # ── Actions / states ───────────────────────────────────────────────
    "buried": [
        "hidden", "underground", "beneath", "concealed", "interred",
        "dug", "unearthed", "entombed",
    ],
    "crossed": [
        "crossing", "traversed", "passed", "forded", "bridged",
        "spanned",
    ],
    "curled": [
        "curling", "wound", "winding", "spiraled", "coiled",
        "twisted", "snaking",
    ],
    "key": [
        "keys", "lock", "locks", "unlock", "unlocking", "latch",
        "bolt", "vault",
    ],
}


# ---------------------------------------------------------------------------
# Stop words — common words to skip during expansion
# ---------------------------------------------------------------------------

STOP_WORDS = {
    "the", "a", "an", "and", "or", "but", "in", "on", "at", "to",
    "for", "of", "with", "by", "from", "is", "was", "are", "were",
    "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "can", "shall",
    "not", "no", "nor", "so", "if", "then", "than", "that", "this",
    "it", "its", "who", "whom", "which", "what", "where", "when",
    "how", "all", "each", "every", "both", "few", "more", "most",
    "other", "some", "such", "only", "own", "same", "very",
}


# ---------------------------------------------------------------------------
# Morphological variants
# ---------------------------------------------------------------------------

def _morphological_variants(word: str) -> Set[str]:
    """Generate common morphological variants of a word."""
    variants = {word}

    # Plural
    if word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        variants.add(word[:-1] + "ies")
    elif word.endswith(("s", "sh", "ch", "x", "z")):
        variants.add(word + "es")
    else:
        variants.add(word + "s")

    # -ing
    if word.endswith("e") and len(word) > 2:
        variants.add(word[:-1] + "ing")
    elif word.endswith("ie"):
        variants.add(word[:-2] + "ying")
    else:
        variants.add(word + "ing")

    # -ed
    if word.endswith("e"):
        variants.add(word + "d")
    elif word.endswith("y") and len(word) > 2 and word[-2] not in "aeiou":
        variants.add(word[:-1] + "ied")
    else:
        variants.add(word + "ed")

    # -ly
    variants.add(word + "ly")

    # -er / -est
    variants.add(word + "er")
    variants.add(word + "est")

    return variants


# ---------------------------------------------------------------------------
# Field Builder
# ---------------------------------------------------------------------------

def build_field(secret: str) -> Dict[str, List[str]]:
    """
    Build a semantic field from a secret phrase.

    For each meaningful word (not a stop word, length > 2):
    1. WordNet synsets (if NLTK available)
    2. Static scene vocabulary matches
    3. Morphological variants

    Returns:
        Dict mapping each secret word to a sorted list of associations
    """
    words = [
        w.lower()
        for w in re.findall(r"[a-z]+", secret.lower())
        if len(w) > 2 and w.lower() not in STOP_WORDS
    ]

    field = {}
    for word in words:
        associations = {word}

        # Layer 1: WordNet (if available)
        if _NLTK_AVAILABLE:
            wn_results = _wordnet_expand(word)
            associations.update(wn_results)

        # Layer 2: Static scene vocabulary
        if word in SCENE_VOCABULARY:
            associations.update(SCENE_VOCABULARY[word])
        # Also check if the word appears in any vocabulary list
        for vocab_key, vocab_words in SCENE_VOCABULARY.items():
            if word in vocab_words:
                associations.add(vocab_key)
                associations.update(vocab_words)

        # Layer 3: Morphological variants
        associations.update(_morphological_variants(word))

        # Clean up — remove very short words and the word itself
        # (word itself is added back as the canonical form)
        cleaned = sorted({
            w for w in associations
            if len(w) > 2 and w != word
        })

        field[word] = cleaned

    return field


def build_field_from_file(secret_path: str) -> Dict[str, List[str]]:
    """Build field from a secret.json file."""
    with open(secret_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return build_field(data["secret"])


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Build semantic field for Keep Defense"
    )
    parser.add_argument(
        "--secret", type=str, default=None,
        help="Secret phrase (direct)"
    )
    parser.add_argument(
        "--secret-file", type=str, default=None,
        help="Path to secret.json"
    )
    parser.add_argument(
        "--output", type=str, default="semantic_field.json",
        help="Output path (default: semantic_field.json)"
    )
    parser.add_argument(
        "--verbose", action="store_true",
        help="Print expansion details"
    )
    args = parser.parse_args()

    if not args.secret and not args.secret_file:
        print("Error: provide --secret or --secret-file", file=sys.stderr)
        sys.exit(1)

    # Get secret
    if args.secret_file:
        with open(args.secret_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        secret = data["secret"]
        secret_hash = data.get("secret_hash", "unknown")
    else:
        secret = args.secret
        import hashlib
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()[:12]

    print(f"Secret hash: {secret_hash}")
    print(f"NLTK WordNet: {'available' if _NLTK_AVAILABLE else 'not available (static only)'}")

    # Build field
    field = build_field(secret)

    # Stats
    total_associations = sum(len(v) for v in field.values())
    print(f"Secret words: {len(field)}")
    print(f"Total associations: {total_associations}")

    if args.verbose:
        for word, associations in field.items():
            print(f"\n  {word} ({len(associations)} associations):")
            for a in associations[:15]:
                print(f"    - {a}")
            if len(associations) > 15:
                print(f"    ... and {len(associations) - 15} more")

    # Write output
    output = {
        "secret_hash": secret_hash,
        "nltk_available": _NLTK_AVAILABLE,
        "word_count": len(field),
        "total_associations": total_associations,
        "field": {k: v for k, v in field.items()},
    }

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nField written to: {output_path}")
    print(f"Load with: SemanticProximityGate.from_field_file('{output_path}')")


if __name__ == "__main__":
    main()
