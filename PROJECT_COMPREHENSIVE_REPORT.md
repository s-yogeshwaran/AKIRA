# AKIRA: Comprehensive Project Master Report

## 1. Project Overview & Identity
* **Project Name:** AKIRA
* **Full Form / Acronym:** **A**ccessible **K**nowledge & **I**nformation **R**etrieval **A**ssistant
* **Domain:** Assistive Technology, Information Retrieval (IR), Natural Language Processing (NLP), Web Applications
* **License & Cost:** 100% Free & Open Source (Zero paid third-party APIs or subscription dependencies)

---

## 2. Problem Statement & Motivation
1. **Encyclopedic Information Overload:** Platforms like Wikipedia contain vast knowledge, but articles are 5,000–10,000 words long, filled with citation brackets (`[1]`, `[citation needed]`) and technical jargon that cause cognitive fatigue.
2. **Accessibility Barriers:** Visually impaired users, individuals with dyslexia, ADHD, or auditory learning preferences struggle with dense, text-only websites that lack interactive assistive reading aids.
3. **The "Passive Reading" Problem:** Students searching online encyclopedias have to manually extract key points and make study flashcards.
4. **Initial State vs. Final State:**
   * *Where we started:* A basic 20-line terminal script (`Search!.py`) with blocking audio and frequent crashes.
   * *Where we ended:* A modern, full-stack, accessible web application with two-way voice interaction, real-time karaoke text tracking, auto-generated study tools, an academic SafeSearch filter, database persistence, and PDF note export.

---

## 3. Technology Stack & Architecture

| Layer | Technology Used | Purpose / Justification |
| :--- | :--- | :--- |
| **Backend Framework** | Python 3 + **Flask** | Lightweight, modular REST API server; serves single-page app and processes text. |
| **Database** | **SQLite** (`akira.db`, `db.py`) | Built-in, zero-configuration relational DBMS storing search history and bookmarks with full CRUD. |
| **NLP & Text Engine** | Python (`re`, `wiki_service.py`) | Regex-based citation stripping, sentence splitting with abbreviation protection, concept extraction. |
| **Speech-to-Text (STT)**| Browser **Web Speech API** (`SpeechRecognition`) | Zero-latency, browser-native microphone recognition with Indian English (`en-IN`) support. |
| **Text-to-Speech (TTS)**| Browser **Web Speech API** (`SpeechSynthesis`) | Hardware-accelerated audio synthesis with real-time speed control and zero server bandwidth load. |
| **Frontend UI** | HTML5, Modern CSS3, Vanilla JavaScript | Fast, zero-build-step responsive interface with dark/light themes and WCAG accessibility standards. |
| **Document Export** | **ReportLab** (`pdf_service.py`) | Python PDF generation engine formatting multi-page study guides and flashcard tables. |
| **Data Source** | Wikipedia / Wikimedia REST API | Real-time encyclopedic article retrieval with compliant User-Agent headers. |

---

## 4. Key Modules & Features Implemented

### Module 1: Two-Way Voice & Audio Engine (`static/js/speech.js`)
* **Voice Search (Speech-to-Text):**
  * Microphone input with real-time visual transcription feedback in the search box.
  * Auto-detects local accent (`navigator.language || 'en-IN'`).
  * Cleans spoken conversational prefixes (*"what is"*, *"tell me about"*, *"search for"*) so natural queries like *"what is generative AI"* become clean search terms.
* **Audio Player (Text-to-Speech):**
  * Controls: **Play**, **Pause**, **Resume**, **Stop**.
  * **Dynamic Live Speed:** Dragging the slider or clicking preset chips (`0.75x`, `1.0x`, `1.25x`, `1.5x`) immediately updates playback speed without stutters or resets.
  * Voice picker dropdown with native system voices.
  * Keyboard shortcut: `Spacebar` toggles Play/Pause.

### Module 2: Synchronized "Karaoke" Sentence Tracking (`speech.js`, `main.js`)
* As the speech engine speaks each sentence, the corresponding text or bullet point on screen is highlighted in real-time with an active visual indicator.
* Enables readers with **dyslexia** or **reading difficulties** to track audio alongside text.
* Users can click on *any* specific sentence to start reading aloud from that exact spot.

### Module 3: Multi-Level Content Synthesis (`wiki_service.py`)
AKIRA breaks complex encyclopedic articles into 4 digestible tiers:
1. **Executive Audio Recap:** A concise 2–3 sentence summary optimized for a 1-minute audio brief.
2. **Key Takeaways:** 3–4 high-yield bullet points highlighting fundamental concepts and real-world significance.
3. **Study Flashcards:** 3–5 automatically generated interactive 3D flip-cards (Definition, Core Concept, Applications, Origins).
4. **Full Clean Text:** Complete article with citation brackets (`[1]`, `[edit]`) cleanly stripped.

### Module 4: Academic SafeSearch & Smart Auto-Resolution (`wiki_service.py`)
* **Academic Safety Filter:** Built-in regex filter that blocks NSFW, adult, vulgar, and slop suggestions/topics. Explicit searches cleanly return: *"This topic is restricted under academic content safety guidelines."*
* **Smart Auto-Resolution:** If a user types or speaks a minor query variation (e.g., `"generating AI"`), AKIRA detects high-confidence similarity and directly loads the canonical article (**`Generative AI`**) without failing.
* **Literary Safety Exceptions:** Whitelisted literary terms (e.g., *"Moby Dick"*, *"Philip K. Dick"*, *"Charles Dickens"*) so valid academic topics are never falsely censored.

### Module 5: Accessibility Suite (`static/css/accessibility.css`)
* **Dyslexia Font Mode:** One-click toggle applying high-legibility typographic styling (`OpenDyslexic` font rules, wider letter spacing, enhanced line-height).
* **High-Contrast Dark / Light Themes:** Accessible color palettes meeting WCAG contrast ratios.
* **Text Scaling:** Interactive font size controls (`A-`, `A`, `A+`).

### Module 6: Persistence & Study Tool Exports (`db.py`, `pdf_service.py`)
* **SQLite Persistence:**
  * Search history tracking with clear and delete functions.
  * Bookmarking articles with full summaries and takeaways saved in `akira.db`.
* **Study Guide PDF Export:** Streams a downloadable, multi-page PDF document containing topic overviews, takeaway bullet points, and flashcard review tables.
* **Markdown Notes Export:** Downloads a formatted `.md` file for note-taking apps like Notion or Obsidian.

---

## 7. Technical Flaws Encountered & Engineering Solutions

| Flaw / Bug | Root Cause | Engineering Solution |
| :--- | :--- | :--- |
| **403 API Block / JSONDecodeError** | Wikimedia API requires a descriptive `User-Agent`. | Configured `wikipedia.set_user_agent("AKIRA-AccessibleAssistant/1.0")`. |
| **"Topic Not Found" on abbreviations** | Python `wikipedia` library's `auto_suggest=True` altered words into typos (e.g., `"gen ai"` $\rightarrow$ `"gen a i"`). | Enforced `auto_suggest=False` and built a smart search resolver using whole-word confidence scoring. |
| **Inappropriate Suggestions** | Wikipedia search suggestions for generic queries returned adult/slop pages. | Built `is_restricted_topic()` blocklist with safe academic exception bypasses. |
| **Speed Slider Not Updating Audio** | Web Speech API only applies rate at utterance instantiation; dragging slider triggered 30+ cancel calls/sec. | Implemented 120ms debounced live re-speaking with presets (`0.75x`–`1.5x`). |
| **Microphone Mishearing Indian Accents** | Language was hardcoded to `en-US`. | Dynamically bound recognition to `navigator.language \|\| 'en-IN'` with live transcript display. |
| **Flashcard Layout Overflow** | Fixed `position: absolute` parent with 150-word text caused cards to overlap other elements. | Wrapped definitions in scrollable `.card-def-container` (`max-height: 140px`) with fixed 250px cards. |
| **ReportLab PDF Layout Crash** | Wrapping multi-page summaries in single-cell tables threw `LayoutError` when exceeding page frame height. | Converted summary callouts to styled multi-page flowable `ParagraphStyle` containers with XML escaping. |

---

## 8. Database Schema (`akira.db`)

```sql
-- Search History Table
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    query TEXT NOT NULL,
    mode TEXT DEFAULT 'standard',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_history_created_at ON history(created_at DESC);

-- Bookmarks Table
CREATE TABLE IF NOT EXISTS bookmarks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL UNIQUE,
    summary TEXT,
    url TEXT,
    takeaways TEXT, -- JSON-encoded array of bullet points
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_bookmarks_title ON bookmarks(title);
```

---

## 9. REST API Endpoints (`app.py`)

* `GET /` — Renders main single-page application.
* `GET /api/search?q=<topic>&mode=<standard|full>` — Fetches article, extracts summary, takeaways, flashcards, and thumbnail.
* `GET /api/history` — Returns recent searches.
* `DELETE /api/history` — Clears search history.
* `GET /api/bookmarks` — Returns all saved bookmarks.
* `POST /api/bookmarks` — Saves a bookmarked article (JSON payload).
* `DELETE /api/bookmarks/<id>` — Removes a bookmark.
* `GET /api/export-pdf?q=<topic>` — Generates and downloads a ReportLab PDF study guide.
* `GET /api/export-notes?q=<topic>` — Generates and downloads Markdown notes.
* `GET /api/health` — System status and database diagnostics.

---

## 10. Verification & Test Suite (`test_akira.py`)
The project features a **16-test automated test suite** running via Python's `unittest` framework with 100% pass rate:
* `test_database_crud`: Validates SQLite CRUD operations and conflict handling.
* `test_academic_content_safety_filter`: Validates NSFW blocking and literary exception preservation.
* `test_api_search_smart_auto_resolution`: Validates query variations (e.g., `"generating AI"` $\rightarrow$ `"Generative AI"`).
* `test_strip_conversational_prefix`: Validates conversational voice query preprocessing.
* `test_split_into_sentences_preserves_initials_and_abbrevs`: Validates that honorifics (`Dr.`, `Mr.`, `i.e.`, `U.S.`) are not split.
* `test_flashcard_generation_guarantees_minimum_cards`: Validates 3–5 unique study cards generated per topic.
* `test_generate_study_pdf_safety_and_multipage`: Validates XML character safety and multi-page layout stability.
* `test_client_javascript_speech_engine_clean_query`: Verifies frontend JavaScript runs without runtime errors using Node.js.

---

## 11. File Tree & Workspace Organization

```
d:\MCA\MCA Sem 3\m_project\
│
├── app.py                      # Flask REST API server and route handlers
├── db.py                       # SQLite database manager (CRUD operations)
├── wiki_service.py             # Wikipedia API client, NLP processor, and safety filter
├── pdf_service.py              # ReportLab PDF study sheet generator
├── requirements.txt            # Python dependencies (Flask, wikipedia, reportlab, etc.)
├── test_akira.py               # Comprehensive 16-test automated verification suite
├── akira.db                    # SQLite production database
│
├── static/
│   ├── css/
│   │   ├── style.css           # Modern responsive design, themes, player deck, flashcards
│   │   └── accessibility.css   # Dyslexia-friendly typography, contrast, karaoke styling
│   └── js/
│       ├── api.js              # REST client handling asynchronous fetch calls
│       ├── speech.js           # Web Speech API engine (STT voice search + TTS audio player)
│       └── main.js             # UI state coordinator, flashcard flipping, keyboard shortcuts
│
├── templates/
│   └── index.html              # Single-page web dashboard with semantic HTML
│
└── docs/                       # Project documentation & reference files
    ├── ABSTRACT.md             # 1-page academic abstract
    ├── PROJECT_COMPREHENSIVE_REPORT.md # Master project technical report
    ├── Abstract.internship.pdf # Original internship abstract
    ├── Intro.Internship.pdf    # Original project introduction
    ├── REquirement.pdf         # Original requirements document
    └── Search!.py              # Original CLI prototype (archived)
```
