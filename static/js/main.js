/**
 * AKIRA Main Application Controller (main.js)
 * Coordinates UI, Accessibility Settings, Voice Search, Audio Player & Study Tools.
 */

document.addEventListener("DOMContentLoaded", () => {
    // -------------------------------------------------------------
    // 1. State & Instances
    // -------------------------------------------------------------
    const speech = new SpeechEngine();
    let currentArticleData = null;
    let currentActiveTab = "recap"; // 'recap', 'takeaways', 'flashcards', 'full'

    // DOM Elements - Search
    const searchForm = document.getElementById("search-form");
    const searchInput = document.getElementById("search-input");
    const clearBtn = document.getElementById("clear-btn");
    const micBtn = document.getElementById("mic-btn");
    const searchSubmitBtn = document.getElementById("search-submit-btn");
    const topicChips = document.querySelectorAll(".topic-chip");

    // DOM Elements - Alerts & Article Display
    const alertCard = document.getElementById("alert-card");
    const alertTitle = document.getElementById("alert-title");
    const alertMessage = document.getElementById("alert-message");
    const disambigList = document.getElementById("disambig-list");

    const articleContainer = document.getElementById("article-container");
    const articleTitle = document.getElementById("article-title");
    const readingTimeBadge = document.getElementById("reading-time-badge");
    const wikiExternalLink = document.getElementById("wiki-external-link");
    const articleThumbWrapper = document.getElementById("article-thumb-wrapper");
    const articleThumb = document.getElementById("article-thumb");
    const bookmarkBtn = document.getElementById("bookmark-btn");
    const exportPdfBtn = document.getElementById("export-pdf-btn");
    const exportNotesBtn = document.getElementById("export-notes-btn");

    // DOM Elements - Tabs & Panels
    const tabButtons = document.querySelectorAll(".tab-btn");
    const tabPanels = document.querySelectorAll(".tab-panel");
    const recapPanel = document.getElementById("panel-recap");
    const takeawaysList = document.getElementById("takeaways-list");
    const flashcardsGrid = document.getElementById("flashcards-grid");
    const fullContentPanel = document.getElementById("panel-full");

    // DOM Elements - Audio Deck
    const audioDeck = document.getElementById("audio-deck");
    const playBtn = document.getElementById("audio-play-btn");
    const pauseBtn = document.getElementById("audio-pause-btn");
    const stopBtn = document.getElementById("audio-stop-btn");
    const speedSlider = document.getElementById("speed-slider");
    const speedVal = document.getElementById("speed-val");
    const voiceSelect = document.getElementById("voice-select");
    const audioStatusLabel = document.getElementById("audio-status-label");
    const audioProgressBar = document.getElementById("audio-progress-bar");

    // DOM Elements - Accessibility Controls
    const toggleDyslexiaBtn = document.getElementById("toggle-dyslexia");
    const fontDecreaseBtn = document.getElementById("font-decrease");
    const fontResetBtn = document.getElementById("font-reset");
    const fontIncreaseBtn = document.getElementById("font-increase");
    const themeSelect = document.getElementById("theme-select");

    // DOM Elements - Drawer
    const drawerOpenBtn = document.getElementById("drawer-open-btn");
    const drawerCloseBtn = document.getElementById("drawer-close-btn");
    const sideDrawer = document.getElementById("side-drawer");
    const drawerBackdrop = document.getElementById("drawer-backdrop");
    const drawerTabs = document.querySelectorAll(".drawer-tab");
    const historyList = document.getElementById("history-list");
    const bookmarksList = document.getElementById("bookmarks-list");
    const clearHistoryBtn = document.getElementById("clear-history-btn");

    // Toast Container
    const toastContainer = document.getElementById("toast-container");

    // -------------------------------------------------------------
    // 2. Toast Notification Helper
    // -------------------------------------------------------------
    function showToast(message, type = "info") {
        const toast = document.createElement("div");
        toast.className = `toast toast-${type}`;
        toast.setAttribute("role", "status");
        toast.textContent = message;
        toastContainer.appendChild(toast);
        setTimeout(() => {
            toast.style.opacity = "0";
            toast.style.transition = "opacity 0.3s ease";
            setTimeout(() => toast.remove(), 300);
        }, 3200);
    }

    // -------------------------------------------------------------
    // 3. Accessibility Preferences Management
    // -------------------------------------------------------------
    const savedTheme = localStorage.getItem("akira_theme") || "light";
    const savedDyslexia = localStorage.getItem("akira_dyslexia") === "true";
    const savedFontScale = localStorage.getItem("akira_font_scale") || "font-scale-md";

    // Apply saved accessibility states
    applyTheme(savedTheme);
    if (savedDyslexia) {
        document.body.classList.add("font-dyslexia");
        toggleDyslexiaBtn.classList.add("active");
        toggleDyslexiaBtn.setAttribute("aria-pressed", "true");
    }
    applyFontScale(savedFontScale);

    toggleDyslexiaBtn.addEventListener("click", () => {
        const isDyslexia = document.body.classList.toggle("font-dyslexia");
        toggleDyslexiaBtn.classList.toggle("active", isDyslexia);
        toggleDyslexiaBtn.setAttribute("aria-pressed", String(isDyslexia));
        localStorage.setItem("akira_dyslexia", String(isDyslexia));
        showToast(isDyslexia ? "Dyslexia-friendly reading font enabled" : "Standard font restored");
    });

    function applyTheme(theme) {
        document.body.classList.remove("theme-dark", "theme-high-contrast", "theme-sepia");
        if (theme === "dark") document.body.classList.add("theme-dark");
        else if (theme === "high-contrast") document.body.classList.add("theme-high-contrast");
        else if (theme === "sepia") document.body.classList.add("theme-sepia");
        themeSelect.value = theme;
        localStorage.setItem("akira_theme", theme);
    }

    themeSelect.addEventListener("change", (e) => {
        applyTheme(e.target.value);
        showToast(`Theme changed to ${e.target.options[e.target.selectedIndex].text}`);
    });

    function applyFontScale(scaleClass) {
        document.body.classList.remove("font-scale-sm", "font-scale-md", "font-scale-lg", "font-scale-xl");
        document.body.classList.add(scaleClass);
        localStorage.setItem("akira_font_scale", scaleClass);
    }

    fontDecreaseBtn.addEventListener("click", () => {
        if (document.body.classList.contains("font-scale-xl")) applyFontScale("font-scale-lg");
        else if (document.body.classList.contains("font-scale-lg")) applyFontScale("font-scale-md");
        else applyFontScale("font-scale-sm");
    });

    fontResetBtn.addEventListener("click", () => {
        applyFontScale("font-scale-md");
        showToast("Text size reset to default");
    });

    fontIncreaseBtn.addEventListener("click", () => {
        if (document.body.classList.contains("font-scale-sm")) applyFontScale("font-scale-md");
        else if (document.body.classList.contains("font-scale-md")) applyFontScale("font-scale-lg");
        else applyFontScale("font-scale-xl");
    });

    // -------------------------------------------------------------
    // 4. Voice Engine & Karaoke Highlighting Sync
    // -------------------------------------------------------------
    // Populate voice dropdown when available
    function populateVoiceList() {
        let voices = speech.getVoices();
        if (!voices || voices.length === 0) {
            if (window.speechSynthesis) {
                voices = window.speechSynthesis.getVoices();
            }
        }
        if (!voices || voices.length === 0) {
            voiceSelect.innerHTML = '<option value="">Default System Voice</option>';
            return;
        }

        voiceSelect.innerHTML = "";
        voices.forEach((voice, index) => {
            const opt = document.createElement("option");
            opt.value = index;
            opt.textContent = `${voice.name} (${voice.lang})`;
            if (speech.selectedVoice && speech.selectedVoice.name === voice.name) {
                opt.selected = true;
            }
            voiceSelect.appendChild(opt);
        });
    }

    speech.onVoicesLoaded = populateVoiceList;
    populateVoiceList();
    if (window.speechSynthesis && window.speechSynthesis.addEventListener) {
        window.speechSynthesis.addEventListener("voiceschanged", populateVoiceList);
    }

    voiceSelect.addEventListener("change", (e) => {
        speech.setVoiceByIndex(parseInt(e.target.value, 10));
    });

    const speedPresetBtns = document.querySelectorAll(".speed-preset-btn");

    function updateSpeedDisplay(rate) {
        const numRate = parseFloat(rate);
        speedVal.textContent = `${numRate.toFixed(numRate % 1 === 0 ? 1 : 2)}x`;
        speedSlider.value = numRate;
        speedPresetBtns.forEach(btn => {
            const btnSpeed = parseFloat(btn.getAttribute("data-speed"));
            btn.classList.toggle("active", Math.abs(btnSpeed - numRate) < 0.04);
        });
    }

    speedSlider.addEventListener("input", (e) => {
        const val = parseFloat(e.target.value);
        speech.setRate(val, false);
        updateSpeedDisplay(val);
    });

    speedPresetBtns.forEach(btn => {
        btn.addEventListener("click", () => {
            const val = parseFloat(btn.getAttribute("data-speed"));
            speech.setRate(val, true);
            updateSpeedDisplay(val);
        });
    });

    // Karaoke Sentence Highlighting Callback
    speech.onSentenceChange = (index, total, sentenceText) => {
        // Clear previous active highlights
        document.querySelectorAll(".karaoke-sentence.active-speech").forEach((el) => {
            el.classList.remove("active-speech");
        });

        // Highlight matching sentence in currently active panel
        const targetSentenceEl = document.querySelector(`.tab-panel.active [data-sentence-index="${index}"]`);
        if (targetSentenceEl) {
            targetSentenceEl.classList.add("active-speech");
            targetSentenceEl.scrollIntoView({ behavior: "smooth", block: "nearest" });
        }

        // Update audio deck progress & status
        const pct = Math.round(((index + 1) / total) * 100);
        audioProgressBar.style.width = `${pct}%`;
        audioStatusLabel.innerHTML = `<span>🔊 Reading sentence ${index + 1} of ${total}</span>`;
        playBtn.innerHTML = "⏸️";
        playBtn.setAttribute("aria-label", "Pause Speech");
    };

    speech.onPlaybackEnd = () => {
        document.querySelectorAll(".karaoke-sentence.active-speech").forEach((el) => {
            el.classList.remove("active-speech");
        });
        audioProgressBar.style.width = "0%";
        audioStatusLabel.innerHTML = "<span>✅ Finished reading</span>";
        playBtn.innerHTML = "▶️";
        playBtn.setAttribute("aria-label", "Play Audio");
    };

    speech.onStatusChange = (status) => {
        if (status === "Paused") {
            audioStatusLabel.innerHTML = "<span>⏸️ Paused</span>";
            playBtn.innerHTML = "▶️";
        } else if (status === "Playing") {
            audioStatusLabel.innerHTML = "<span>🔊 Playing</span>";
            playBtn.innerHTML = "⏸️";
        } else if (status === "Stopped") {
            audioStatusLabel.innerHTML = "<span>⏹️ Ready</span>";
            playBtn.innerHTML = "▶️";
            audioProgressBar.style.width = "0%";
            document.querySelectorAll(".karaoke-sentence.active-speech").forEach((el) => {
                el.classList.remove("active-speech");
            });
        }
    };

    // Audio Play/Pause/Stop Buttons
    playBtn.addEventListener("click", () => {
        if (!currentArticleData) {
            showToast("Please search for a topic first!");
            return;
        }

        if (speech.isPlaying && !speech.isPaused) {
            speech.pause();
        } else if (speech.isPlaying && speech.isPaused) {
            speech.resume();
        } else {
            // Start reading sentences based on current view
            const activeSentences = getActiveSentencesForPlayback();
            speech.playSentences(activeSentences, 0);
        }
    });

    pauseBtn.addEventListener("click", () => {
        if (speech.isPlaying) speech.pause();
    });

    stopBtn.addEventListener("click", () => {
        speech.stop();
    });

    function getActiveSentencesForPlayback() {
        if (!currentArticleData) return [];

        if (currentActiveTab === "recap") {
            return currentArticleData.sentences || [currentArticleData.summary];
        } else if (currentActiveTab === "takeaways") {
            return currentArticleData.takeaways || [];
        } else if (currentActiveTab === "flashcards") {
            return (currentArticleData.flashcards || []).map(c => `${c.term}: ${c.definition}`);
        } else {
            return currentArticleData.sentences || [currentArticleData.summary];
        }
    }

    // -------------------------------------------------------------
    // 5. Speech-to-Text (Voice Search Input)
    // -------------------------------------------------------------
    micBtn.addEventListener("click", () => {
        if (speech.isListening) {
            speech.stopListening();
            micBtn.classList.remove("listening");
            audioStatusLabel.textContent = "Voice search canceled.";
            return;
        }

        micBtn.classList.add("listening");
        audioStatusLabel.textContent = "Listening... Speak your topic.";

        speech.startListening(
            (transcript, isFinal = true) => {
                searchInput.value = transcript;
                clearBtn.style.display = "block";

                if (!isFinal) {
                    audioStatusLabel.innerHTML = `<span>🎙️ Hearing: "${transcript}..."</span>`;
                    return;
                }

                micBtn.classList.remove("listening");
                showToast(`Heard: "${transcript}"`);
                performSearch(transcript);
            },
            (statusMsg) => {
                audioStatusLabel.textContent = statusMsg;
            },
            (errorMsg) => {
                micBtn.classList.remove("listening");
                showToast(errorMsg, "warning");
                audioStatusLabel.textContent = errorMsg;
            }
        );
    });

    // -------------------------------------------------------------
    // 6. Search Submission & Results Rendering
    // -------------------------------------------------------------
    searchInput.addEventListener("input", () => {
        clearBtn.style.display = searchInput.value ? "block" : "none";
    });

    clearBtn.addEventListener("click", () => {
        searchInput.value = "";
        clearBtn.style.display = "none";
        searchInput.focus();
    });

    searchForm.addEventListener("submit", (e) => {
        e.preventDefault();
        const query = searchInput.value.trim();
        if (query) performSearch(query);
    });

    topicChips.forEach((chip) => {
        chip.addEventListener("click", () => {
            const topic = chip.getAttribute("data-topic") || chip.textContent.trim();
            searchInput.value = topic;
            clearBtn.style.display = "block";
            performSearch(topic);
        });
    });

    async function performSearch(query) {
        speech.stop();
        searchSubmitBtn.disabled = true;
        searchSubmitBtn.textContent = "Searching...";

        alertCard.style.display = "none";
        articleContainer.style.display = "none";

        try {
            const data = await API.search(query);
            searchSubmitBtn.disabled = false;
            searchSubmitBtn.innerHTML = "<span>🔍 Search</span>";

            if (data.status === "disambiguation") {
                renderDisambiguation(data);
            } else if (data.status === "not_found") {
                renderNotFound(data);
            } else if (data.status === "restricted") {
                renderRestricted(data);
            } else if (data.status === "success") {
                currentArticleData = data;
                renderArticle(data);
                loadHistory(); // refresh history panel
            } else {
                showToast(data.message || "An error occurred.", "danger");
            }
        } catch (err) {
            searchSubmitBtn.disabled = false;
            searchSubmitBtn.innerHTML = "<span>🔍 Search</span>";
            showToast("Network error while connecting to AKIRA backend.", "danger");
        }
    }

    function renderRestricted(data) {
        alertCard.style.display = "block";
        alertTitle.textContent = "Academic Content Safety Notice";
        alertMessage.textContent = data.message;
        disambigList.innerHTML = "";
        showToast(data.message, "warning");
        alertCard.scrollIntoView({ behavior: "smooth" });
    }

    function renderDisambiguation(data) {
        alertCard.style.display = "block";
        alertTitle.textContent = "Multiple Topics Found";
        alertMessage.textContent = data.message;
        disambigList.innerHTML = "";

        data.options.forEach((opt) => {
            const btn = document.createElement("button");
            btn.className = "disambig-item";
            btn.textContent = opt;
            btn.addEventListener("click", () => {
                searchInput.value = opt;
                performSearch(opt);
            });
            disambigList.appendChild(btn);
        });
        alertCard.scrollIntoView({ behavior: "smooth" });
    }

    function renderNotFound(data) {
        alertCard.style.display = "block";
        alertTitle.textContent = "Topic Not Found";
        alertMessage.textContent = data.message;
        disambigList.innerHTML = "";

        if (data.suggestions && data.suggestions.length > 0) {
            data.suggestions.forEach((sug) => {
                const btn = document.createElement("button");
                btn.className = "disambig-item";
                btn.textContent = sug;
                btn.addEventListener("click", () => {
                    searchInput.value = sug;
                    performSearch(sug);
                });
                disambigList.appendChild(btn);
            });
        }
        alertCard.scrollIntoView({ behavior: "smooth" });
    }

    function renderArticle(data) {
        articleContainer.style.display = "block";
        articleTitle.textContent = data.title;
        readingTimeBadge.textContent = data.estimated_read_time || "2 min audio";
        wikiExternalLink.href = data.url;

        // Thumbnail
        if (data.thumbnail) {
            articleThumb.src = data.thumbnail;
            articleThumb.alt = `Illustration of ${data.title}`;
            articleThumbWrapper.style.display = "block";
        } else {
            articleThumbWrapper.style.display = "none";
        }

        // Bookmark State
        updateBookmarkButtonState(data.is_bookmarked);

        // Export Download Links
        exportPdfBtn.onclick = () => {
            window.location.href = API.getPdfUrl(data.title);
        };
        exportNotesBtn.onclick = () => {
            window.location.href = API.getNotesUrl(data.title);
        };

        // Render Panel 1: Executive Audio Recap with Karaoke Spans
        renderRecapWithKaraoke(data.sentences || [data.summary]);

        // Render Panel 2: Key Bullet Takeaways
        renderTakeaways(data.takeaways || []);

        // Render Panel 3: Interactive Flashcards
        renderFlashcards(data.flashcards || []);

        // Render Panel 4: Full Article
        renderFullArticle(data);

        // Switch to default recap tab
        switchTab("recap");
        articleContainer.scrollIntoView({ behavior: "smooth", block: "start" });
    }

    function renderRecapWithKaraoke(sentences) {
        recapPanel.innerHTML = "";
        const p = document.createElement("p");
        p.className = "recap-content";

        sentences.forEach((sentence, idx) => {
            const span = document.createElement("span");
            span.className = "karaoke-sentence";
            span.setAttribute("data-sentence-index", idx);
            span.textContent = sentence + " ";
            // Clicking any sentence jumps audio playback directly to it
            span.addEventListener("click", () => {
                speech.jumpToSentence(idx);
            });
            p.appendChild(span);
        });

        recapPanel.appendChild(p);
    }

    function renderTakeaways(bullets) {
        takeawaysList.innerHTML = "";
        bullets.forEach((bullet, index) => {
            const li = document.createElement("li");
            li.className = "takeaway-item karaoke-sentence";
            li.setAttribute("data-sentence-index", index);
            li.setAttribute("tabindex", "0");
            li.setAttribute("role", "button");
            li.setAttribute("aria-label", `Takeaway ${index + 1}: ${bullet}`);

            const badge = document.createElement("span");
            badge.className = "takeaway-badge";
            badge.textContent = index + 1;

            const textSpan = document.createElement("span");
            textSpan.className = "takeaway-text";
            textSpan.textContent = bullet;

            li.appendChild(badge);
            li.appendChild(textSpan);

            li.addEventListener("click", () => {
                speech.playSentences(bullets, index);
            });

            takeawaysList.appendChild(li);
        });
    }

    function renderFlashcards(flashcards) {
        flashcardsGrid.innerHTML = "";
        if (!flashcards || flashcards.length === 0) {
            flashcardsGrid.innerHTML = "<p>No flashcards extracted for this topic.</p>";
            return;
        }

        flashcards.forEach((card, index) => {
            const cardEl = document.createElement("div");
            cardEl.className = "flashcard";
            cardEl.setAttribute("tabindex", "0");
            cardEl.setAttribute("role", "button");
            cardEl.setAttribute("aria-label", `Flashcard ${index + 1}: ${card.term}. Press space or enter to flip.`);

            cardEl.innerHTML = `
                <div class="flashcard-inner">
                    <div class="flashcard-front">
                        <span class="card-cat">${card.category || "Concept"}</span>
                        <h4 class="card-term">${card.term}</h4>
                        <div class="card-prompt">🔄 Click or press Space to reveal answer</div>
                    </div>
                    <div class="flashcard-back">
                        <div class="card-def-container">
                            <p class="card-def">${card.definition}</p>
                        </div>
                        <div class="card-footer">
                            <span class="card-cat">${card.hint || "Review"}</span>
                            <button class="card-flip-btn" type="button">Flip Back</button>
                        </div>
                    </div>
                </div>
            `;

            // Prevent scrolling/selecting inside the definition box from flipping the card
            const defBox = cardEl.querySelector(".card-def-container");
            if (defBox) {
                defBox.addEventListener("click", (e) => e.stopPropagation());
            }

            // Flip interactions
            const flip = () => cardEl.classList.toggle("flipped");
            cardEl.addEventListener("click", flip);
            cardEl.addEventListener("keydown", (e) => {
                if (e.key === " " || e.key === "Enter") {
                    e.preventDefault();
                    flip();
                }
            });

            flashcardsGrid.appendChild(cardEl);
        });
    }

    function renderFullArticle(data) {
        fullContentPanel.innerHTML = "";
        const sentences = data.sentences || [data.summary];
        const p = document.createElement("p");
        p.className = "recap-content";

        sentences.forEach((sentence, idx) => {
            const span = document.createElement("span");
            span.className = "karaoke-sentence";
            span.setAttribute("data-sentence-index", idx);
            span.textContent = sentence + " ";
            span.addEventListener("click", () => {
                speech.jumpToSentence(idx);
            });
            p.appendChild(span);
        });

        fullContentPanel.appendChild(p);
    }

    // -------------------------------------------------------------
    // 7. Tabs Switching
    // -------------------------------------------------------------
    tabButtons.forEach((btn) => {
        btn.addEventListener("click", () => {
            const tabId = btn.getAttribute("data-tab");
            switchTab(tabId);
        });
    });

    function switchTab(tabId) {
        currentActiveTab = tabId;
        tabButtons.forEach((b) => {
            const isActive = b.getAttribute("data-tab") === tabId;
            b.classList.toggle("active", isActive);
            b.setAttribute("aria-selected", String(isActive));
        });

        tabPanels.forEach((p) => {
            p.classList.toggle("active", p.id === `panel-${tabId}`);
        });

        // If audio is actively playing, let the karaoke highlight synchronize with the newly visible panel
        if (speech.isPlaying && speech.currentSentenceIndex >= 0) {
            document.querySelectorAll(".karaoke-sentence.active-speech").forEach(el => el.classList.remove("active-speech"));
            const targetSentenceEl = document.querySelector(`.tab-panel.active [data-sentence-index="${speech.currentSentenceIndex}"]`);
            if (targetSentenceEl) targetSentenceEl.classList.add("active-speech");
        }
    }

    // -------------------------------------------------------------
    // 8. Bookmarks & History Drawer Handling
    // -------------------------------------------------------------
    function updateBookmarkButtonState(isBookmarked) {
        if (isBookmarked) {
            bookmarkBtn.classList.add("bookmarked");
            bookmarkBtn.innerHTML = "<span>⭐ Bookmarked</span>";
        } else {
            bookmarkBtn.classList.remove("bookmarked");
            bookmarkBtn.innerHTML = "<span>☆ Bookmark</span>";
        }
    }

    bookmarkBtn.addEventListener("click", async () => {
        if (!currentArticleData) return;

        const isCurrently = bookmarkBtn.classList.contains("bookmarked");
        if (isCurrently) {
            // Find in bookmarks to delete
            const bData = await API.getBookmarks();
            const existing = (bData.bookmarks || []).find(b => b.title.toLowerCase() === currentArticleData.title.toLowerCase());
            if (existing) {
                await API.deleteBookmark(existing.id);
                updateBookmarkButtonState(false);
                showToast(`Removed "${currentArticleData.title}" from bookmarks.`);
                loadBookmarks();
            }
        } else {
            await API.saveBookmark({
                title: currentArticleData.title,
                summary: currentArticleData.summary,
                url: currentArticleData.url,
                takeaways: currentArticleData.takeaways,
            });
            updateBookmarkButtonState(true);
            showToast(`"${currentArticleData.title}" saved to bookmarks!`);
            loadBookmarks();
        }
    });

    function openDrawer() {
        sideDrawer.classList.add("open");
        drawerBackdrop.classList.add("active");
        loadHistory();
        loadBookmarks();
    }

    function closeDrawer() {
        sideDrawer.classList.remove("open");
        drawerBackdrop.classList.remove("active");
    }

    drawerOpenBtn.addEventListener("click", openDrawer);
    drawerCloseBtn.addEventListener("click", closeDrawer);
    drawerBackdrop.addEventListener("click", closeDrawer);

    // Switch between History and Bookmarks in drawer
    drawerTabs.forEach((tab) => {
        tab.addEventListener("click", () => {
            drawerTabs.forEach(t => t.classList.remove("active"));
            tab.classList.add("active");
            const target = tab.getAttribute("data-drawer-tab");
            historyList.style.display = target === "history" ? "flex" : "none";
            bookmarksList.style.display = target === "bookmarks" ? "flex" : "none";
            clearHistoryBtn.style.display = target === "history" ? "block" : "none";
        });
    });

    async function loadHistory() {
        try {
            const data = await API.getHistory();
            historyList.innerHTML = "";
            const items = data.history || [];
            if (items.length === 0) {
                historyList.innerHTML = "<li style='padding: 10px; color: var(--text-muted);'>No recent searches.</li>";
                return;
            }

            items.forEach((item) => {
                const li = document.createElement("li");
                li.className = "drawer-item";
                li.innerHTML = `
                    <div style="flex:1;">
                        <div class="drawer-item-title">${item.query}</div>
                        <div class="drawer-item-meta">${item.created_at || ""}</div>
                    </div>
                    <button class="drawer-item-del" title="Delete entry">&times;</button>
                `;

                li.querySelector("div").addEventListener("click", () => {
                    closeDrawer();
                    searchInput.value = item.query;
                    clearBtn.style.display = "block";
                    performSearch(item.query);
                });

                li.querySelector(".drawer-item-del").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    await API.deleteHistoryItem(item.id);
                    loadHistory();
                });

                historyList.appendChild(li);
            });
        } catch (err) {
            console.error(err);
        }
    }

    async function loadBookmarks() {
        try {
            const data = await API.getBookmarks();
            bookmarksList.innerHTML = "";
            const items = data.bookmarks || [];
            if (items.length === 0) {
                bookmarksList.innerHTML = "<li style='padding: 10px; color: var(--text-muted);'>No saved bookmarks yet.</li>";
                return;
            }

            items.forEach((item) => {
                const li = document.createElement("li");
                li.className = "drawer-item";
                li.innerHTML = `
                    <div style="flex:1;">
                        <div class="drawer-item-title">${item.title}</div>
                        <div class="drawer-item-meta">${item.created_at || ""}</div>
                    </div>
                    <button class="drawer-item-del" title="Remove bookmark">&times;</button>
                `;

                li.querySelector("div").addEventListener("click", () => {
                    closeDrawer();
                    searchInput.value = item.title;
                    clearBtn.style.display = "block";
                    performSearch(item.title);
                });

                li.querySelector(".drawer-item-del").addEventListener("click", async (e) => {
                    e.stopPropagation();
                    await API.deleteBookmark(item.id);
                    if (currentArticleData && currentArticleData.title === item.title) {
                        updateBookmarkButtonState(false);
                    }
                    loadBookmarks();
                });

                bookmarksList.appendChild(li);
            });
        } catch (err) {
            console.error(err);
        }
    }

    clearHistoryBtn.addEventListener("click", async () => {
        if (confirm("Clear all search history?")) {
            await API.clearHistory();
            loadHistory();
            showToast("Search history cleared.");
        }
    });

    // -------------------------------------------------------------
    // 9. Global Keyboard Accessibility Shortcuts
    // -------------------------------------------------------------
    document.addEventListener("keydown", (e) => {
        // Alt+S or '/' when not in input focuses search
        if ((e.key === "/" || (e.altKey && e.key.toLowerCase() === "s")) && document.activeElement !== searchInput) {
            e.preventDefault();
            searchInput.focus();
        }

        // Alt+M toggles voice search
        if (e.altKey && e.key.toLowerCase() === "m") {
            e.preventDefault();
            micBtn.click();
        }

        // Spacebar toggles audio play/pause when not in an input, button, or textarea
        if (e.key === " " && document.activeElement !== searchInput && !["INPUT", "BUTTON", "SELECT", "TEXTAREA"].includes(document.activeElement.tagName)) {
            e.preventDefault();
            playBtn.click();
        }

        // Escape closes drawer or stops audio
        if (e.key === "Escape") {
            if (sideDrawer.classList.contains("open")) {
                closeDrawer();
            } else if (speech.isPlaying) {
                speech.stop();
            }
        }
    });
});

