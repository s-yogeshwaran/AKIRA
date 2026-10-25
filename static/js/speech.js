/**
 * AKIRA Voice & Speech Engine (speech.js)
 * Implements two-way voice:
 * 1. Speech-to-Text (Web Speech API Recognition)
 * 2. Text-to-Speech (Web Speech API Synthesis) with synchronized Karaoke highlighting.
 */

class SpeechEngine {
    constructor() {
        // Speech Recognition Setup
        const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;
        this.recognition = SpeechRec ? new SpeechRec() : null;
        this.isListening = false;

        // Speech Synthesis Setup
        this.synth = window.speechSynthesis;
        this.voices = [];
        this.selectedVoice = null;
        this.rate = 1.0;
        this.pitch = 1.0;

        // Playback state & sentence queue for Karaoke
        this.sentences = [];
        this.currentSentenceIndex = 0;
        this.isPlaying = false;
        this.isPaused = false;
        this.currentUtterance = null;
        this.rateChangeTimeout = null;

        // UI Callbacks
        this.onSentenceChange = null;
        this.onPlaybackEnd = null;
        this.onStatusChange = null;

        this.initVoices();
    }

    /**
     * Populate available system and browser voices
     */
    initVoices() {
        if (!this.synth) return;

        const loadVoices = () => {
            this.voices = this.synth.getVoices();
            if (this.voices && this.voices.length > 0) {
                // Default to an English voice (prefer US/UK/Natural)
                const englishVoice = this.voices.find(v => v.lang.startsWith("en") && (v.name.includes("Google") || v.name.includes("Natural") || v.name.includes("Samantha") || v.default))
                    || this.voices.find(v => v.lang.startsWith("en"))
                    || this.voices[0];
                this.selectedVoice = englishVoice;
            }
            if (this.onVoicesLoaded) {
                this.onVoicesLoaded(this.voices);
            }
        };

        loadVoices();
        if (this.synth.addEventListener) {
            this.synth.addEventListener("voiceschanged", loadVoices);
        } else if (this.synth.onvoiceschanged !== undefined) {
            this.synth.onvoiceschanged = loadVoices;
        }
    }

    getVoices() {
        return this.voices;
    }

    setVoiceByIndex(index) {
        if (this.voices[index]) {
            this.selectedVoice = this.voices[index];
        }
    }

    setRate(newRate, immediate = false) {
        const parsed = parseFloat(newRate);
        if (isNaN(parsed) || parsed <= 0) return;
        this.rate = parsed;

        if (this.rateChangeTimeout) {
            clearTimeout(this.rateChangeTimeout);
            this.rateChangeTimeout = null;
        }

        // If audio is currently playing, restart the current sentence with new rate
        if (this.isPlaying && !this.isPaused && this.synth) {
            const restart = () => {
                if (!this.isPlaying || this.isPaused || !this.synth) return;
                if (this.currentUtterance) {
                    this.currentUtterance.onend = null;
                    this.currentUtterance.onerror = null;
                }
                this.synth.cancel();
                // 40ms safety timeout allows browser audio subsystem to reset cleanly before next speak
                setTimeout(() => {
                    if (this.isPlaying && !this.isPaused) {
                        this.speakCurrentSentence();
                    }
                }, 40);
            };

            if (immediate) {
                restart();
            } else {
                this.rateChangeTimeout = setTimeout(restart, 120);
            }
        }
    }

    /**
     * Pre-process spoken queries to strip conversational prefixes like
     * "search for", "what is", "tell me about", "who is", "explain", "define".
     * Properly handles word boundaries and contractions ("what's", "who's").
     */
    static cleanSpokenQuery(query) {
        if (!query) return "";
        const prefixRegex = /^(?:please\s+)?(?:can\s+you\s+)?(?:search(?:\s+(?:for|about))?|what\s*(?:is|'s|are)(?:\s+\b(?:an?|the)\b)?|who\s*(?:is|was|were|'s)(?:\s+\b(?:an?|the)\b)?|tell\s+me(?:\s+about)?|explain(?:\s+about)?|define(?:\s+\b(?:an?|the)\b)?|look\s*up|info(?:rmation)?(?:\s+(?:about|on))?|find(?:\s+out)?(?:\s+about)?)\s+/i;
        let prev = "";
        let curr = query.trim();
        while (prev !== curr) {
            prev = curr;
            curr = curr.replace(prefixRegex, "").trim();
        }
        const cleaned = curr.replace(/[?.!]+$/, "").trim();
        return cleaned || query.trim();
    }

    /* -------------------------------------------------------------
     * 1. Speech-to-Text (Voice Search Input)
     * ------------------------------------------------------------- */
    startListening(onTranscript, onStatus, onError) {
        if (!this.recognition) {
            if (onError) onError("Voice search is not supported in this browser. Please use Google Chrome or Microsoft Edge.");
            return;
        }

        if (this.isListening) {
            this.stopListening();
            return;
        }

        // Configure recognition: dynamic language matching browser locale or en-IN
        const browserLocale = (typeof navigator !== "undefined" && (navigator.language || navigator.userLanguage)) || "en-IN";
        this.recognition.lang = browserLocale;
        this.recognition.continuous = false;
        this.recognition.interimResults = true;

        let hasFinalResult = false;
        let lastTranscript = "";

        this.recognition.onstart = () => {
            this.isListening = true;
            hasFinalResult = false;
            lastTranscript = "";
            if (onStatus) onStatus("Listening... speak your topic now.");
        };

        this.recognition.onresult = (event) => {
            let interimTranscript = "";
            let finalTranscript = "";

            for (let i = event.resultIndex; i < event.results.length; ++i) {
                const res = event.results[i];
                if (res.isFinal) {
                    finalTranscript += res[0].transcript;
                } else {
                    interimTranscript += res[0].transcript;
                }
            }

            if (interimTranscript) {
                lastTranscript = interimTranscript;
                if (onTranscript) onTranscript(interimTranscript, false);
            }

            if (finalTranscript.trim()) {
                hasFinalResult = true;
                this.stopListening();
                const cleaned = SpeechEngine.cleanSpokenQuery(finalTranscript);
                if (onTranscript) onTranscript(cleaned, true);
            }
        };

        this.recognition.onerror = (event) => {
            this.isListening = false;
            let msg = "Microphone error. Please try again.";
            if (event.error === "not-allowed") {
                msg = "Microphone access blocked. Please allow mic permissions in browser settings.";
            } else if (event.error === "no-speech") {
                msg = "No speech detected. Please try again.";
            }
            if (onError) onError(msg);
        };

        this.recognition.onend = () => {
            this.isListening = false;
            if (!hasFinalResult && lastTranscript.trim()) {
                hasFinalResult = true;
                const cleaned = SpeechEngine.cleanSpokenQuery(lastTranscript);
                if (onTranscript) onTranscript(cleaned, true);
            }
            if (onStatus) onStatus("Voice search ended.");
        };

        try {
            this.recognition.start();
        } catch (err) {
            if (onError) onError(err.message);
        }
    }

    stopListening() {
        if (this.recognition && this.isListening) {
            this.recognition.stop();
            this.isListening = false;
        }
    }

    /* -------------------------------------------------------------
     * 2. Text-to-Speech & Karaoke Synchronized Playback
     * ------------------------------------------------------------- */
    playSentences(sentences, startIndex = 0) {
        if (!this.synth) {
            alert("Text-to-speech is not supported by your browser.");
            return;
        }

        if (!sentences || sentences.length === 0) return;

        // Stop any active utterance
        this.stop();

        this.sentences = sentences;
        this.currentSentenceIndex = startIndex;
        this.isPlaying = true;
        this.isPaused = false;

        this.speakCurrentSentence();
    }

    speakCurrentSentence() {
        if (!this.isPlaying || this.isPaused) return;

        if (this.currentSentenceIndex >= this.sentences.length) {
            this.stop();
            if (this.onPlaybackEnd) this.onPlaybackEnd();
            return;
        }

        const sentenceText = this.sentences[this.currentSentenceIndex];
        if (!sentenceText || !sentenceText.trim()) {
            this.currentSentenceIndex++;
            this.speakCurrentSentence();
            return;
        }

        // Notify UI to apply Karaoke Highlight
        if (this.onSentenceChange) {
            this.onSentenceChange(this.currentSentenceIndex, this.sentences.length, sentenceText);
        }

        this.currentUtterance = new SpeechSynthesisUtterance(sentenceText);
        if (this.selectedVoice) {
            this.currentUtterance.voice = this.selectedVoice;
        }
        this.currentUtterance.rate = this.rate;
        this.currentUtterance.pitch = this.pitch;

        this.currentUtterance.onend = () => {
            if (this.isPlaying && !this.isPaused) {
                this.currentSentenceIndex++;
                // Small natural conversational pause between sentences
                setTimeout(() => {
                    this.speakCurrentSentence();
                }, 120);
            }
        };

        this.currentUtterance.onerror = (e) => {
            if (e.error !== "canceled" && e.error !== "interrupted") {
                console.warn("Speech synthesis error:", e);
            }
        };

        this.synth.speak(this.currentUtterance);
    }

    pause() {
        if (this.isPlaying && !this.isPaused) {
            this.synth.pause();
            this.isPaused = true;
            if (this.onStatusChange) this.onStatusChange("Paused");
        }
    }

    resume() {
        if (this.isPlaying && this.isPaused) {
            this.synth.resume();
            this.isPaused = false;
            if (this.onStatusChange) this.onStatusChange("Playing");
            // If Chromium stalled or canceled while paused, re-speak current sentence
            if (!this.synth.speaking) {
                this.speakCurrentSentence();
            }
        } else if (!this.isPlaying && this.sentences.length > 0) {
            this.playSentences(this.sentences, this.currentSentenceIndex);
        }
    }

    stop() {
        if (this.synth) {
            if (this.synth.paused) {
                this.synth.resume();
            }
            this.synth.cancel();
        }
        if (this.rateChangeTimeout) {
            clearTimeout(this.rateChangeTimeout);
            this.rateChangeTimeout = null;
        }
        this.isPlaying = false;
        this.isPaused = false;
        this.currentSentenceIndex = 0;
        this.currentUtterance = null;
        if (this.onStatusChange) this.onStatusChange("Stopped");
    }

    jumpToSentence(index) {
        if (index >= 0 && index < this.sentences.length) {
            this.playSentences(this.sentences, index);
        }
    }
}

window.SpeechEngine = SpeechEngine;

