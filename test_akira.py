"""
AKIRA Comprehensive Automated Test Suite (test_akira.py)
Validates Database operations, Wikipedia & NLP service, PDF generation, and Flask API endpoints.
Includes regression checks for sentence splitting, XML escaping, conflict resolution, and isolation.
"""

import os
import unittest
import json
import tempfile
import db
import wiki_service
import pdf_service
import app


class AkiraTestCase(unittest.TestCase):
    def setUp(self):
        # Create a temporary SQLite database for complete test isolation
        self.temp_db_fd, self.temp_db_path = tempfile.mkstemp(suffix=".db")
        app.app.config["TESTING"] = True
        app.app.config["DB_PATH"] = self.temp_db_path
        db.init_db(db_path=self.temp_db_path)

        # Configure Flask test client
        self.client = app.app.test_client()

    def tearDown(self):
        # Close and remove temporary database
        os.close(self.temp_db_fd)
        if os.path.exists(self.temp_db_path):
            try:
                os.remove(self.temp_db_path)
            except Exception:
                pass

    # -------------------------------------------------------------
    # 1. Database CRUD Tests
    # -------------------------------------------------------------
    def test_database_crud(self):
        # Test search history
        h_id1 = db.add_search("Machine Learning", mode="standard", db_path=self.temp_db_path)
        h_id2 = db.add_search("Deep Learning", mode="quick", db_path=self.temp_db_path)
        self.assertGreater(h_id1, 0)
        self.assertGreater(h_id2, 0)

        history = db.get_history(limit=10, db_path=self.temp_db_path)
        self.assertEqual(len(history), 2)
        self.assertEqual(history[0]["query"], "Deep Learning")

        # Test single item deletion
        deleted = db.delete_history_item(h_id1, db_path=self.temp_db_path)
        self.assertTrue(deleted)
        self.assertEqual(len(db.get_history(db_path=self.temp_db_path)), 1)

        # Test clear history
        db.clear_history(db_path=self.temp_db_path)
        self.assertEqual(len(db.get_history(db_path=self.temp_db_path)), 0)

        # Test bookmarks
        b_id1 = db.add_bookmark(
            title="Neural Network",
            summary="Computing systems inspired by biological neural networks.",
            url="https://en.wikipedia.org/wiki/Artificial_neural_network",
            takeaways=["Model human brain", "Core of deep learning"],
            db_path=self.temp_db_path,
        )
        self.assertGreater(b_id1, 0)
        self.assertTrue(db.is_bookmarked("Neural Network", db_path=self.temp_db_path))

        # Test bookmark conflict update (ensure it returns valid id > 0, not 0)
        b_id2 = db.add_bookmark(
            title="Neural Network",
            summary="Updated summary of neural networks.",
            url="https://en.wikipedia.org/wiki/Artificial_neural_network",
            takeaways=["Updated takeaway"],
            db_path=self.temp_db_path,
        )
        self.assertEqual(b_id1, b_id2)
        self.assertGreater(b_id2, 0)

        bookmarks = db.get_bookmarks(db_path=self.temp_db_path)
        self.assertEqual(len(bookmarks), 1)
        self.assertEqual(bookmarks[0]["title"], "Neural Network")
        self.assertEqual(bookmarks[0]["summary"], "Updated summary of neural networks.")
        self.assertIn("Updated takeaway", bookmarks[0]["takeaways"])

        # Test bookmark deletion
        del_b = db.delete_bookmark(b_id1, db_path=self.temp_db_path)
        self.assertTrue(del_b)
        self.assertFalse(db.is_bookmarked("Neural Network", db_path=self.temp_db_path))

    # -------------------------------------------------------------
    # 2. Wikipedia & NLP Service Unit Tests
    # -------------------------------------------------------------
    def test_clean_wikipedia_text(self):
        raw = "Artificial Intelligence (AI)[1][2] is a branch of computer science.[edit][citation needed] == History == It began in 1956. == References == [1] Book"
        cleaned = wiki_service.clean_wikipedia_text(raw)
        self.assertNotIn("[1]", cleaned)
        self.assertNotIn("[edit]", cleaned)
        self.assertNotIn("[citation needed]", cleaned)
        self.assertNotIn("== History ==", cleaned)
        self.assertNotIn("== References ==", cleaned)
        self.assertNotIn("Book", cleaned)
        self.assertIn("Artificial Intelligence (AI)", cleaned)

    def test_split_into_sentences_preserves_initials_and_abbrevs(self):
        sample = "Dr. Alan Turing was born in London. The U.S. government works on AI. J. K. Rowling wrote books. Short. Yes."
        sentences = wiki_service.split_into_sentences(sample)
        self.assertEqual(len(sentences), 5)
        self.assertEqual(sentences[0], "Dr. Alan Turing was born in London.")
        self.assertEqual(sentences[1], "The U.S. government works on AI.")
        self.assertEqual(sentences[2], "J. K. Rowling wrote books.")
        self.assertEqual(sentences[3], "Short.")
        self.assertEqual(sentences[4], "Yes.")

    def test_flashcard_generation_guarantees_minimum_cards(self):
        title = "Cloud Computing"
        sentences = [
            "Cloud computing is the on-demand availability of computer system resources.",
            "Key features include high scalability and virtualization.",
        ]
        cards = wiki_service.generate_flashcards(title, sentences, " ".join(sentences))
        self.assertGreaterEqual(len(cards), 3)
        self.assertEqual(cards[0]["category"], "Definition")
        self.assertIn(title, cards[0]["question"])
        # Verify no duplicate definitions across cards
        defs = [c["definition"] for c in cards]
        self.assertEqual(len(defs), len(set(defs)))

    def test_extract_takeaways(self):
        sentences = [
            "Sentence one is the foundation of knowledge.",
            "Sentence two explains the core architecture and design.",
            "Sentence three explores modern applications and adoption.",
        ]
        bullets = wiki_service.extract_takeaways(sentences, max_bullets=3)
        self.assertEqual(len(bullets), 3)
        self.assertEqual(bullets[0], sentences[0])

    def test_academic_content_safety_filter(self):
        # Restricted keywords should be identified
        self.assertTrue(wiki_service.is_restricted_topic("Generative AI pornography"))
        self.assertTrue(wiki_service.is_restricted_topic("AI slop"))
        self.assertTrue(wiki_service.is_restricted_topic("xxx video"))
        self.assertTrue(wiki_service.is_restricted_topic("erotica novels"))

        # Clean academic keywords should NOT be flagged
        self.assertFalse(wiki_service.is_restricted_topic("generating AI"))
        self.assertFalse(wiki_service.is_restricted_topic("Generative AI"))
        self.assertFalse(wiki_service.is_restricted_topic("Quantum computing"))
        self.assertFalse(wiki_service.is_restricted_topic("Classroom dynamics"))
        self.assertFalse(wiki_service.is_restricted_topic("Assessments"))

        # Historical, literary, and scientific subjects must NOT be falsely blocked
        self.assertFalse(wiki_service.is_restricted_topic("Moby Dick"))
        self.assertFalse(wiki_service.is_restricted_topic("Philip K. Dick"))
        self.assertFalse(wiki_service.is_restricted_topic("Dick Cheney"))
        self.assertFalse(wiki_service.is_restricted_topic("Charles Dickens"))
        self.assertFalse(wiki_service.is_restricted_topic("Emily Dickinson"))

        # Suggestion filtering should strip restricted topics
        raw_list = ["Generative AI", "Generative AI pornography", "AI art", "AI slop", "Text-to-image"]
        safe_list = wiki_service.filter_safe_topics(raw_list)
        self.assertNotIn("Generative AI pornography", safe_list)
        self.assertNotIn("AI slop", safe_list)
        self.assertIn("Generative AI", safe_list)
        self.assertIn("AI art", safe_list)

    def test_strip_conversational_prefix(self):
        self.assertEqual(wiki_service.strip_conversational_prefix("what is generative AI"), "generative AI")
        self.assertEqual(wiki_service.strip_conversational_prefix("what's generative AI"), "generative AI")
        self.assertEqual(wiki_service.strip_conversational_prefix("tell me about quantum computing?"), "quantum computing")
        self.assertEqual(wiki_service.strip_conversational_prefix("search for Alan Turing"), "Alan Turing")
        self.assertEqual(wiki_service.strip_conversational_prefix("explain black holes."), "black holes")
        self.assertEqual(wiki_service.strip_conversational_prefix("who was Isaac Newton?"), "Isaac Newton")
        self.assertEqual(wiki_service.strip_conversational_prefix("who's Alan Turing"), "Alan Turing")
        self.assertEqual(wiki_service.strip_conversational_prefix("can you tell me what is Alan Turing"), "Alan Turing")
        self.assertEqual(wiki_service.strip_conversational_prefix("define artificial intelligence"), "artificial intelligence")
        self.assertEqual(wiki_service.strip_conversational_prefix("what is an algorithm"), "algorithm")
        self.assertEqual(wiki_service.strip_conversational_prefix("what is the speed of light"), "speed of light")
        self.assertEqual(wiki_service.strip_conversational_prefix("Alan Turing"), "Alan Turing")

    def test_high_confidence_match(self):
        # Legitimate matches
        self.assertTrue(wiki_service.is_high_confidence_match("generating AI", "Generative AI"))
        self.assertTrue(wiki_service.is_high_confidence_match("quantum computer", "Quantum computing"))
        self.assertTrue(wiki_service.is_high_confidence_match("neural network", "Artificial neural network"))
        self.assertTrue(wiki_service.is_high_confidence_match("artifical inteligence", "Artificial intelligence"))

        # Rejection of arbitrary substrings and false positives
        self.assertFalse(wiki_service.is_high_confidence_match("cat", "Education"))
        self.assertFalse(wiki_service.is_high_confidence_match("car", "Madagascar"))
        self.assertFalse(wiki_service.is_high_confidence_match("art", "Smart"))
        self.assertFalse(wiki_service.is_high_confidence_match("ten", "Sentence"))
        self.assertFalse(wiki_service.is_high_confidence_match("cat", "Rat"))
        self.assertFalse(wiki_service.is_high_confidence_match("xyzabc123", "Artificial intelligence"))

    def test_client_javascript_speech_engine_clean_query(self):
        import subprocess
        node_script = """
        global.window = {};
        require('./static/js/speech.js');
        const clean = window.SpeechEngine.cleanSpokenQuery;
        if (clean('what is generative AI') !== 'generative AI') process.exit(1);
        if (clean("what's generative AI") !== 'generative AI') process.exit(2);
        if (clean('can you tell me what is Alan Turing') !== 'Alan Turing') process.exit(3);
        if (clean('define artificial intelligence') !== 'artificial intelligence') process.exit(4);
        console.log('JS_SPEECH_OK');
        """
        result = subprocess.run(["node", "-e", node_script], capture_output=True, text=True, check=True)
        self.assertIn("JS_SPEECH_OK", result.stdout)

    # -------------------------------------------------------------
    # 3. PDF Service Tests (XML Safety & Long Content)
    # -------------------------------------------------------------
    def test_generate_study_pdf_safety_and_multipage(self):
        test_data = {
            "title": "Quantum Computing & <Physics>",
            "summary": "Quantum computing uses <qubits> & superposition. " * 150,  # Multi-page summary test
            "url": "https://en.wikipedia.org/wiki/Quantum_computing?ref=1&test=2",
            "takeaways": [
                "Utilizes qubits <state> capable of superposition & entanglement.",
                "Exponential speedup for problems where N < 1000.",
            ],
            "flashcards": [
                {
                    "term": "<Qubit>",
                    "question": "What is a <Qubit>?",
                    "definition": "The basic unit of quantum information & state.",
                }
            ],
        }
        pdf_buf = pdf_service.generate_study_pdf(test_data)
        pdf_bytes = pdf_buf.getvalue()
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    # -------------------------------------------------------------
    # 4. Flask API Endpoint Integration Tests
    # -------------------------------------------------------------
    def test_api_health(self):
        res = self.client.get("/api/health")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "healthy")

    def test_frontend_renders(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        html = res.data.decode("utf-8")
        self.assertIn("AKIRA", html)
        self.assertIn("Accessible Knowledge & Information Retrieval Assistant", html)
        self.assertNotIn("MCA", html)
        self.assertNotIn("MCA Sem 3", html)
        self.assertNotIn("MCA SEM 3", html)
        self.assertIn("speech.js", html)

    def test_api_search_empty_query(self):
        res = self.client.get("/api/search?q=")
        self.assertEqual(res.status_code, 400)

    def test_api_search_restricted_topic(self):
        res = self.client.get("/api/search?q=Generative+AI+pornography")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "restricted")
        self.assertIn("academic content safety guidelines", data["message"])

    def test_api_search_smart_auto_resolution(self):
        res = self.client.get("/api/search?q=generating+AI")
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["title"], "Generative AI")

    def test_api_bookmarks_and_history_endpoints_isolated(self):
        # Save bookmark via API
        payload = {
            "title": "Test Isolated Article",
            "summary": "Testing isolated database state.",
            "url": "https://en.wikipedia.org/wiki/Test",
            "takeaways": ["Takeaway 1", "Takeaway 2"],
        }
        res_post = self.client.post("/api/bookmarks", data=json.dumps(payload), content_type="application/json")
        self.assertEqual(res_post.status_code, 200)
        b_id = res_post.get_json()["id"]
        self.assertGreater(b_id, 0)

        # Fetch bookmarks
        res_get = self.client.get("/api/bookmarks")
        self.assertEqual(res_get.status_code, 200)
        bookmarks = res_get.get_json()["bookmarks"]
        self.assertTrue(any(b["title"] == "Test Isolated Article" for b in bookmarks))

        # Delete bookmark
        res_del = self.client.delete(f"/api/bookmarks/{b_id}")
        self.assertEqual(res_del.status_code, 200)

        # Clear history on isolated database
        res_hist_clear = self.client.delete("/api/history")
        self.assertEqual(res_hist_clear.status_code, 200)


if __name__ == "__main__":
    unittest.main(verbosity=2)
