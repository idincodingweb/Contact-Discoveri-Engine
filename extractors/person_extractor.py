"""
Extract decision-maker (Person, Role) pairs from a page.

Strategy:
1. JSON-LD `Person` blocks (highest confidence).
2. Heuristic: lines like 'John Doe, CEO' or 'John Doe — Founder'.
3. Card patterns: <h?>Name</h?> followed by element containing role keyword.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass

from bs4 import BeautifulSoup, Tag

ROLE_KEYWORDS = {
    # High priority
    "Founder":            ("founder", "co-founder", "cofounder"),
    "CEO":                ("ceo", "chief executive officer"),
    "Owner":              ("owner", "proprietor"),
    "Managing Director":  ("managing director",),
    "Managing Partner":   ("managing partner",),
    "Director":           ("director",),
    # Medium
    "Marketing Director": ("marketing director", "director of marketing"),
    "Marketing Manager":  ("marketing manager",),
    "Head of Marketing":  ("head of marketing",),
    "Business Development": ("business development", "bd manager"),
}

ROLE_PRIORITY = {
    "Founder": 1, "CEO": 1, "Owner": 1, "Managing Director": 1,
    "Managing Partner": 1, "Director": 2,
    "Marketing Director": 5, "Marketing Manager": 5,
    "Head of Marketing": 5, "Business Development": 6,
}

NAME_RE = re.compile(r"^[A-Z][a-zA-Z'\-\.]+(?:\s+[A-Z][a-zA-Z'\-\.]+){1,3}$")


@dataclass(frozen=True)
class Person:
    name: str
    role: str
    priority: int


def extract_people(html: str) -> list[Person]:
    if not html:
        return []
    soup = BeautifulSoup(html, "lxml")
    out: dict[tuple[str, str], Person] = {}

    # 1) JSON-LD
    for s in soup.find_all("script", type=lambda v: v and "ld+json" in v.lower()):
        try:
            data = json.loads(s.string or "")
        except Exception:
            continue
        for p in _iter_jsonld_persons(data):
            name = (p.get("name") or "").strip()
            role = (p.get("jobTitle") or "").strip()
            if name and role:
                canonical = _canon_role(role)
                if canonical:
                    out[(name, canonical)] = Person(name, canonical,
                                                    ROLE_PRIORITY.get(canonical, 50))

    # 2) Inline text patterns
    text = soup.get_text("\n", strip=True)
    for line in text.splitlines():
        for canonical, kws in ROLE_KEYWORDS.items():
            for kw in kws:
                if kw in line.lower():
                    name = _extract_name_near_role(line, kw)
                    if name:
                        out[(name, canonical)] = Person(name, canonical,
                                                        ROLE_PRIORITY.get(canonical, 50))

    # 3) Card pattern: heading + role nearby
    for h in soup.select("h1, h2, h3, h4, h5, strong, .name, .member-name"):
        name = h.get_text(" ", strip=True)
        if not NAME_RE.match(name):
            continue
        sibling_text = _nearby_text(h)
        for canonical, kws in ROLE_KEYWORDS.items():
            if any(kw in sibling_text.lower() for kw in kws):
                out[(name, canonical)] = Person(name, canonical,
                                                ROLE_PRIORITY.get(canonical, 50))
                break

    return sorted(out.values(), key=lambda p: (p.priority, p.name))


def _iter_jsonld_persons(node):
    if isinstance(node, list):
        for x in node:
            yield from _iter_jsonld_persons(x)
    elif isinstance(node, dict):
        t = node.get("@type")
        if t == "Person" or (isinstance(t, list) and "Person" in t):
            yield node
        for v in node.values():
            if isinstance(v, (dict, list)):
                yield from _iter_jsonld_persons(v)


def _canon_role(role: str) -> str | None:
    low = role.lower()
    for canonical, kws in ROLE_KEYWORDS.items():
        if any(kw in low for kw in kws):
            return canonical
    return None


def _extract_name_near_role(line: str, kw: str) -> str | None:
    idx = line.lower().find(kw)
    if idx < 0:
        return None
    left = line[:idx].rstrip(" ,–—-:|·•")
    # take last 2-4 capitalized tokens
    tokens = left.split()
    for size in (4, 3, 2):
        if len(tokens) >= size:
            candidate = " ".join(tokens[-size:])
            if NAME_RE.match(candidate):
                return candidate
    return None


def _nearby_text(tag: Tag) -> str:
    parts: list[str] = []
    if tag.parent:
        parts.append(tag.parent.get_text(" ", strip=True))
    nxt = tag.find_next_sibling()
    if nxt:
        parts.append(nxt.get_text(" ", strip=True))
    return " ".join(parts)[:300]
