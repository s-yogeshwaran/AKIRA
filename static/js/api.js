/**
 * AKIRA API Client (api.js)
 * Clean, promise-based HTTP client for backend REST endpoints.
 */

const API = {
    /**
     * Search Wikipedia article and fetch structured takeaways & flashcards
     */
    async search(query, mode = "standard") {
        const url = `/api/search?q=${encodeURIComponent(query)}&mode=${encodeURIComponent(mode)}`;
        const res = await fetch(url);
        return await res.json();
    },

    /**
     * Retrieve recent search history
     */
    async getHistory(limit = 20) {
        const res = await fetch(`/api/history?limit=${limit}`);
        return await res.json();
    },

    /**
     * Clear all search history
     */
    async clearHistory() {
        const res = await fetch("/api/history", { method: "DELETE" });
        return await res.json();
    },

    /**
     * Delete a single history entry
     */
    async deleteHistoryItem(id) {
        const res = await fetch(`/api/history/${id}`, { method: "DELETE" });
        return await res.json();
    },

    /**
     * Retrieve all saved bookmarks
     */
    async getBookmarks() {
        const res = await fetch("/api/bookmarks");
        return await res.json();
    },

    /**
     * Save article bookmark
     */
    async saveBookmark(data) {
        const res = await fetch("/api/bookmarks", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data),
        });
        return await res.json();
    },

    /**
     * Remove article bookmark
     */
    async deleteBookmark(id) {
        const res = await fetch(`/api/bookmarks/${id}`, { method: "DELETE" });
        return await res.json();
    },

    /**
     * Get download URL for generated study PDF
     */
    getPdfUrl(query) {
        return `/api/export-pdf?q=${encodeURIComponent(query)}`;
    },

    /**
     * Get download URL for study notes sheet
     */
    getNotesUrl(query) {
        return `/api/export-notes?q=${encodeURIComponent(query)}`;
    },
};

window.API = API;

