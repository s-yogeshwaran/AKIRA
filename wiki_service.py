"""
AKIRA Wikipedia & NLP Service (wiki_service.py)
Handles safe Wikipedia querying, media fetching, text cleaning,
multi-level synthesis (executive summary, bullet takeaways),
and auto-generation of revision flashcards.
"""

import re
import difflib
import warnings
import requests
import bs4
import wikipedia
from typing import Dict, List, Any, Optional

# Suppress harmless BeautifulSoup parser warning from third-party wikipedia library
warnings.filterwarnings("ignore", category=bs4.GuessedAtParserWarning)
warnings.filterwarnings("ignore", category=UserWarning, module="wikipedia")

# Set compliant User-Agent per Wikimedia API Policy
USER_AGENT = "AKIRA-AccessibleAssistant/1.0 (educational-use; MCA-Project; mailto:akira.assistant@example.edu)"
wikipedia.set_user_agent(USER_AGENT)

# Common encyclopedic abbreviations to prevent improper sentence splitting
ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "sr", "jr", "st", "gen", "gov", "pres",
    "sen", "rep", "capt", "col", "lt", "maj", "rev", "hon", "vs", "etc",
    "al", "approx", "est", "dept", "fig", "no", "vol",
    "jan", "feb", "mar", "apr", "jun", "jul", "aug", "sep", "sept", "oct", "nov", "dec"
}

# In-memory query cache for instant retrieval of repeat queries
_CACHE: Dict[str, Dict[str, Any]] = {}

# Conversational voice prefixes to strip from natural speech queries
CONVERSATIONAL_PREFIX_PATTERN = re.compile(
    r"^(?:please\s+)?(?:can\s+you\s+)?(?:search(?:\s+(?:for|about))?|what\s*(?:is|'s|are)(?:\s+\b(?:an?|the)\b)?|who\s*(?:is|was|were|'s)(?:\s+\b(?:an?|the)\b)?|tell\s+me(?:\s+about)?|explain(?:\s+about)?|define(?:\s+\b(?:an?|the)\b)?|look\s*up|info(?:rmation)?(?:\s+(?:about|on))?|find(?:\s+out)?(?:\s+about)?)\s+",
    flags=re.IGNORECASE,
)

# Academic Content Safety Filter: Blocklist of NSFW, adult, pornography, vulgarity, slop, offensive terms
ACADEMIC_RESTRICTED_PATTERNS = [
    r"\bporn(?:o|ography|ographic)?\b",
    r"\bxxx\b",
    r"\bnsfw\b",
    r"\berotic(?:a)?\b",
    r"\bslop\b",
    r"\bhentai\b",
    r"\bpedophil\w*\b",
    r"\bpaedophil\w*\b",
    r"\bincest\b",
    r"\bmilf\b",
    r"\bblowjob\b",
    r"\bhandjob\b",
    r"\bmasturbat\w*\b",
    r"\borgasm\w*\b",
    r"\bpenis\b",
    r"\bvagina\b",
    r"\bdildo\b",
    r"\bejaculat\w*\b",
    r"\bfuck\w*\b",
    r"\bshit\w*\b",
    r"\bcunt\w*\b",
    r"\basshole\w*\b",
    r"\bdick\b",
    r"\bpussy\b",
    r"\bwhore\w*\b",
    r"\bslut\w*\b",
    r"\brape\b",
    r"\brapist\w*\b",
    r"\bvulgar\w*\b",
]

# Legitimate historical, scientific, or literary subjects that should never be falsely blocked
SAFE_ACADEMIC_EXCEPTIONS = {
    "moby dick",
    "moby-dick",
    "philip k. dick",
    "philip k dick",
    "dick cheney",
    "dick van dyke",
    "dick clark",
    "charles dickens",
    "dickens",
    "emily dickinson",
    "dickinson",
    "oilseed rape",
    "rapeseed",
}

_RESTRICTED_REGEX = re.compile("|".join(ACADEMIC_RESTRICTED_PATTERNS), flags=re.IGNORECASE)


def strip_conversational_prefix(query: str) -> str:
    """
    Remove spoken conversational query prefixes such as 'search for', 'what is', 'tell me about',
    'what's', 'define', 'who was', preserving proper nouns and articles correctly.
    Recursively strips nested prefixes like 'can you tell me what is'.
    """
    if not query:
        return ""
    prev = ""
    curr = query.strip()
    while prev != curr:
        prev = curr
        curr = CONVERSATIONAL_PREFIX_PATTERN.sub("", curr).strip()
    cleaned = curr.rstrip("?.! ")
    return cleaned if cleaned else query.strip()


def is_restricted_topic(text: str) -> bool:
    """
    Return True if text contains prohibited NSFW, adult, slop, or vulgar content.
    Exempts legitimate historical, literary, and scientific subjects.
    """
    if not text:
        return False
    lower_text = text.lower().strip()
    if any(exc in lower_text for exc in SAFE_ACADEMIC_EXCEPTIONS):
        return False
    return bool(_RESTRICTED_REGEX.search(lower_text))


def filter_safe_topics(topics: List[str]) -> List[str]:
    """
    Filter a list of topics/suggestions to remove any containing blocked keywords.
    """
    if not topics:
        return []
    return [t for t in topics if not is_restricted_topic(t)]


def is_high_confidence_match(query: str, candidate: str) -> bool:
    """
    Evaluate if a Wikipedia search candidate is a high-confidence match for the query.
    Handles typos, pluralizations, and grammatical variants (e.g. 'generating AI' -> 'Generative AI').
    Does not falsely match arbitrary substrings (e.g. 'cat' in 'Education' or 'car' in 'Madagascar').
    """
    if not query or not candidate:
        return False
    q = query.lower().strip()
    c = candidate.lower().strip()
    if q == c:
        return True

    # Exact phrase with word boundary (minimum 3 chars)
    if len(q) >= 3 and re.search(r"\b" + re.escape(q) + r"\b", c):
        return True
    if len(c) >= 3 and re.search(r"\b" + re.escape(c) + r"\b", q):
        return True

    # Sequence similarity for full strings
    ratio = difflib.SequenceMatcher(None, q, c).ratio()
    if ratio >= 0.78:
        return True

    # Stem overlap for multi-word or long queries
    q_words = [w for w in re.findall(r"\w+", q) if len(w) >= 2]
    c_words = [w for w in re.findall(r"\w+", c) if len(w) >= 2]
    if not q_words or not c_words:
        return False

    matched = 0
    for qw in q_words:
        for cw in c_words:
            if qw == cw:
                matched += 1
                break
            min_stem = min(len(qw), len(cw))
            if min_stem >= 4 and (qw.startswith(cw[:4]) or cw.startswith(qw[:4])):
                matched += 1
                break

    return (matched / len(q_words)) >= 0.75


def clean_wikipedia_text(raw_text: str) -> str:
    """
    Remove citation markers, footnote references, and redundant formatting.
    Example: '[1]', '[citation needed]', '[edit]', '== References =='.
    """
    if not raw_text:
        return ""

    # Truncate trailing bibliography and reference lists if present
    text = re.split(
        r"(?:\n|^|\s+)={2,}\s*(?:See also|References|External links|Notes|Further reading|Bibliography)\s*={2,}",
        raw_text,
        flags=re.IGNORECASE,
    )[0]

    # Remove [1], [12], [a], [edit], [citation needed], [note 1], [dead link], etc.
    text = re.sub(
        r"\[(?:\d+|[a-z]|edit|note\s*\d+|citation needed|page needed|who\?|when\?|which\?|clarification needed|better source needed|dead link)[^\]]*\]",
        "",
        text,
        flags=re.IGNORECASE,
    )

    # Remove wiki section headers like == Early Life ==
    text = re.sub(r"={2,}\s*[^=]+\s*={2,}", "", text)

    # Replace non-breaking space with regular space
    text = text.replace("\xa0", " ")

    # Remove space before punctuation (e.g. 'word .' -> 'word.')
    text = re.sub(r"\s+([.,;:!?])", r"\1", text)

    # Remove excessive blank lines and spaces
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def split_into_sentences(text: str) -> List[str]:
    """
    Split text into clean, individual sentences for karaoke audio tracking.
    Accurately handles honorifics, abbreviations, acronyms, and names with initials.
    """
    if not text:
        return []

    t = text.strip()

    # Step 1: Protect acronyms like U.S., U.K., e.g., i.e.
    t = re.sub(
        r"\b([A-Za-z]\.[A-Za-z]\.(?:[A-Za-z]\.)?)",
        lambda m: m.group(1).replace(".", "<DOT>"),
        t,
        flags=re.IGNORECASE,
    )

    # Step 2: Protect initials like 'J. K. Rowling' or 'George W. Bush'
    t = re.sub(r"\b([A-Z])\.(?=\s+[A-Z])", r"\1<DOT>", t)

    # Step 3: Protect common abbreviations followed by dot
    for ab in sorted(ABBREVIATIONS, key=len, reverse=True):
        pattern = rf"\b({re.escape(ab)})\."
        t = re.sub(pattern, r"\1<DOT>", t, flags=re.IGNORECASE)

    # Step 4: Split on sentence boundary punctuation followed by whitespace and capital/quote/number
    raw_sentences = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])", t)

    sentences = []
    for s in raw_sentences:
        clean_s = s.replace("<DOT>", ".").strip()
        if clean_s:
            sentences.append(clean_s)

    return sentences if sentences else [text.strip()]


def fetch_page_thumbnail(title: str) -> Optional[str]:
    """
    Fetch the primary page thumbnail image URL via the MediaWiki Action API.
    """
    try:
        url = "https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "titles": title,
            "prop": "pageimages",
            "pithumbsize": 600,
            "format": "json",
        }
        headers = {"User-Agent": USER_AGENT}
        resp = requests.get(url, params=params, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            pages = data.get("query", {}).get("pages", {})
            for page in pages.values():
                thumb = page.get("thumbnail", {})
                if thumb and thumb.get("source"):
                    return thumb.get("source")
    except Exception:
        pass
    return None


def generate_flashcards(title: str, summary_sentences: List[str], full_content: str) -> List[Dict[str, Any]]:
    """
    Auto-extract 3 to 5 structured study flashcards covering definition,
    mechanics, origin/context, and key applications.
    Guarantees at least 3 flashcards even for brief topics.
    """
    cards: List[Dict[str, Any]] = []
    used_definitions = set()

    # Card 1: Core Definition
    if summary_sentences:
        def_text = summary_sentences[0]
        cards.append({
            "id": 1,
            "term": f"What is {title}?",
            "question": f"Define {title}",
            "definition": def_text,
            "category": "Definition",
            "hint": f"Basic identification of {title}",
        })
        used_definitions.add(def_text)

    # Card 2: Key Mechanism / Characteristic
    char_sentence = ""
    for s in summary_sentences[1:]:
        s_lower = s.lower()
        if s not in used_definitions and any(w in s_lower for w in ["characterized", "features", "consists", "includes", "known for", "designed to", "operates"]):
            char_sentence = s
            break
    if not char_sentence and len(summary_sentences) > 1 and summary_sentences[1] not in used_definitions:
        char_sentence = summary_sentences[1]

    if char_sentence:
        cards.append({
            "id": 2,
            "term": "Key Characteristics & Core Concept",
            "question": f"What are the central characteristics or mechanisms of {title}?",
            "definition": char_sentence,
            "category": "Core Concept",
            "hint": "Functionality & Structure",
        })
        used_definitions.add(char_sentence)

    # Card 3: Significance & Practical Applications
    app_sentence = ""
    for s in summary_sentences[1:]:
        s_lower = s.lower()
        if s not in used_definitions and any(w in s_lower for w in ["used in", "used for", "applications", "widely", "important", "modern", "significance", "impact"]):
            app_sentence = s
            break
    if not app_sentence and len(summary_sentences) > 2 and summary_sentences[2] not in used_definitions:
        app_sentence = summary_sentences[2]

    if app_sentence:
        cards.append({
            "id": len(cards) + 1,
            "term": "Practical Applications & Significance",
            "question": f"How is {title} applied in practice or why is it significant?",
            "definition": app_sentence,
            "category": "Applications",
            "hint": "Real-world utility",
        })
        used_definitions.add(app_sentence)

    # Card 4: Historical Context or Background
    hist_sentence = ""
    for s in summary_sentences:
        s_lower = s.lower()
        if s not in used_definitions and any(w in s_lower for w in ["developed", "created", "discovered", "founded", "history", "originally", "century", "first proposed", "invented"]):
            hist_sentence = s
            break
    if not hist_sentence and len(summary_sentences) > 3 and summary_sentences[3] not in used_definitions:
        hist_sentence = summary_sentences[3]

    if hist_sentence:
        cards.append({
            "id": len(cards) + 1,
            "term": "Origins & Background",
            "question": f"What is the historical origin or background of {title}?",
            "definition": hist_sentence,
            "category": "Origins",
            "hint": "Context & Discovery",
        })
        used_definitions.add(hist_sentence)

    # Additional concept card from section headers or prominent terms if available
    if full_content:
        pattern = re.compile(rf"\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\s+(?:is|refers to|means|represents)\s+([^.\n]+?\.)")
        matches = pattern.findall(full_content)
        for term, meaning in matches:
            full_def = f"{term} {meaning.strip()}"
            if term.lower() not in title.lower() and len(term) > 3 and len(meaning) > 20 and full_def not in used_definitions:
                cards.append({
                    "id": len(cards) + 1,
                    "term": term,
                    "question": f"What does '{term}' mean in the context of {title}?",
                    "definition": full_def,
                    "category": "Key Term",
                    "hint": "Domain Terminology",
                })
                used_definitions.add(full_def)
                if len(cards) >= 5:
                    break

    # Fallback to guarantee at least 3 cards if article is very brief
    if len(cards) < 3 and summary_sentences:
        for s in summary_sentences:
            if s not in used_definitions:
                cards.append({
                    "id": len(cards) + 1,
                    "term": f"Core Insight #{len(cards) + 1}",
                    "question": f"Key point regarding {title}",
                    "definition": s,
                    "category": "Key Concept",
                    "hint": "Core Knowledge",
                })
                used_definitions.add(s)
                if len(cards) >= 3:
                    break

    # If still fewer than 3 cards, provide structured review cards with distinct text
    if len(cards) < 3 and summary_sentences:
        first_sentence = summary_sentences[0]
        review_defs = [
            (
                "Essential Knowledge & Scope",
                f"What is the foundational significance of {title}?",
                f"{title} serves as a foundational subject where {first_sentence}",
                "Significance",
            ),
            (
                "Topic Synthesis & Review",
                f"How is {title} systematically summarized?",
                f"In overview: " + " ".join(summary_sentences[:2]),
                "Review",
            ),
        ]
        for term, q, d, cat in review_defs:
            if d not in used_definitions and len(cards) < 3:
                cards.append({
                    "id": len(cards) + 1,
                    "term": term,
                    "question": q,
                    "definition": d,
                    "category": cat,
                    "hint": "Core Concept",
                })
                used_definitions.add(d)

    # Re-index ids 1..N
    for i, c in enumerate(cards):
        c["id"] = i + 1

    return cards[:5]


def extract_takeaways(sentences: List[str], max_bullets: int = 4) -> List[str]:
    """
    Produce high-yield, informative bullet takeaways from article sentences.
    """
    if not sentences:
        return []

    bullets = []
    # Always include the initial defining sentence
    bullets.append(sentences[0])

    # Select subsequent high-information sentences
    for s in sentences[1:]:
        if len(bullets) >= max_bullets:
            break
        # Avoid duplicate sentences or very brief snippets
        if s not in bullets and len(s) > 20:
            bullets.append(s)

    return bullets


def search_wikipedia(query: str, mode: str = "standard") -> Dict[str, Any]:
    """
    Main retrieval orchestrator:
    - Resolves queries safely with smart auto-resolution for inexact titles.
    - Strictly filters out inappropriate, NSFW, and vulgar content.
    - Gracefully handles DisambiguationError, PageError, and MediaWiki rate limits.
    - Cleans content and splits into sentences for karaoke audio.
    - Generates executive summary, bullet takeaways, and study flashcards.
    """
    clean_query = query.strip()
    if not clean_query:
        return {
            "status": "error",
            "message": "Search query cannot be empty. Please enter a topic.",
        }

    # Pre-process query to strip natural speech conversational prefixes
    stripped = strip_conversational_prefix(clean_query)
    if stripped:
        clean_query = stripped

    # Academic content safety gate: reject explicitly restricted topics immediately
    if is_restricted_topic(clean_query):
        return {
            "status": "restricted",
            "query": clean_query,
            "message": "This topic is restricted under academic content safety guidelines.",
        }

    cache_key = f"{clean_query.lower()}_{mode}"
    if cache_key in _CACHE:
        return _CACHE[cache_key]

    try:
        # Step 1: Attempt exact title match
        # CRITICAL: Always use auto_suggest=False to prevent word mangling
        page = None
        try:
            page = wikipedia.page(clean_query, auto_suggest=False)
        except wikipedia.exceptions.DisambiguationError as e:
            safe_options = filter_safe_topics(e.options)
            if not safe_options:
                return {
                    "status": "restricted",
                    "query": clean_query,
                    "message": "This topic is restricted under academic content safety guidelines.",
                }
            return {
                "status": "disambiguation",
                "query": clean_query,
                "message": f"Multiple encyclopedic entries match '{clean_query}'. Please select the specific topic:",
                "options": safe_options[:10],
            }
        except (wikipedia.exceptions.PageError, Exception):
            page = None

        # Step 2: Handle inexact title via Smart Auto-Resolution & Safe Suggestions
        safe_suggestions: List[str] = []
        if not page:
            raw_suggestions = []
            try:
                raw_suggestions = wikipedia.search(clean_query, results=10)
            except Exception:
                raw_suggestions = []

            safe_suggestions = filter_safe_topics(raw_suggestions)

            # Smart Auto-Resolution: If top safe search result is a high-confidence match, load directly
            if safe_suggestions:
                top_result = safe_suggestions[0]
                if is_high_confidence_match(clean_query, top_result):
                    try:
                        resolved_page = wikipedia.page(top_result, auto_suggest=False)
                        if not is_restricted_topic(resolved_page.title):
                            page = resolved_page
                    except wikipedia.exceptions.DisambiguationError as e:
                        safe_options = filter_safe_topics(e.options)
                        if safe_options:
                            return {
                                "status": "disambiguation",
                                "query": clean_query,
                                "message": f"Multiple encyclopedic entries match '{clean_query}'. Please select the specific topic:",
                                "options": safe_options[:10],
                            }
                    except Exception:
                        page = None

        # If still no page resolved, return clean safe suggestions
        if not page:
            if safe_suggestions:
                return {
                    "status": "not_found",
                    "query": clean_query,
                    "message": f"No exact article found for '{clean_query}'. Did you mean one of these?",
                    "suggestions": safe_suggestions[:6],
                }
            return {
                "status": "not_found",
                "query": clean_query,
                "message": f"No Wikipedia article found matching '{clean_query}'. Please try a different query.",
                "suggestions": [],
            }

        # Step 3: Check resolved page title against safety filter
        if is_restricted_topic(page.title):
            return {
                "status": "restricted",
                "query": clean_query,
                "message": "This topic is restricted under academic content safety guidelines.",
            }

        # Step 4: Extract and clean page content
        title = page.title
        url = page.url
        raw_summary = page.summary
        raw_content = page.content if mode == "full" else raw_summary

        clean_summary_text = clean_wikipedia_text(raw_summary)
        clean_content_text = clean_wikipedia_text(raw_content)

        sentences = split_into_sentences(clean_summary_text)
        if not sentences:
            sentences = [clean_summary_text] if clean_summary_text else ["No details available."]

        # 2-minute executive audio recap (first 2-3 sentences)
        executive_summary = " ".join(sentences[:3])

        # High-yield bullet takeaways
        takeaways = extract_takeaways(sentences, max_bullets=4)

        # Revision study flashcards
        flashcards = generate_flashcards(title, sentences, clean_content_text)

        # Thumbnail image
        thumbnail = fetch_page_thumbnail(title)

        result = {
            "status": "success",
            "title": title,
            "url": url,
            "summary": clean_summary_text,
            "executive_summary": executive_summary,
            "sentences": sentences,
            "takeaways": takeaways,
            "flashcards": flashcards,
            "thumbnail": thumbnail,
            "full_content": clean_content_text if mode == "full" else None,
            "total_sentences": len(sentences),
            "estimated_read_time": f"{max(1, len(clean_summary_text.split()) // 130)} min audio",
        }

        # Save in cache under both search query and resulting title
        _CACHE[cache_key] = result
        _CACHE[f"{title.lower()}_{mode}"] = result
        return result

    except wikipedia.exceptions.DisambiguationError as e:
        safe_options = filter_safe_topics(e.options)
        return {
            "status": "disambiguation",
            "query": clean_query,
            "message": f"Multiple results found for '{clean_query}'. Please choose an option:",
            "options": safe_options[:10],
        }
    except Exception as e:
        err_msg = str(e)
        if "429" in err_msg or "Too Many Requests" in err_msg:
            return {
                "status": "error",
                "query": clean_query,
                "message": "Wikimedia API rate limit reached. Please wait a few seconds and try again.",
            }
        return {
            "status": "error",
            "query": clean_query,
            "message": f"An error occurred while fetching information: {err_msg}",
        }
