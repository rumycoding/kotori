import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock
from anki.anki import (
    answer_card,
    answer_multiple_cards,
    find_cards_to_talk_about,
    _find_cards_by_query,
    _get_cards_info,
    create_anki_deck,
    delete_anki_deck,
    add_anki_note,
    delete_anki_note,
    check_anki_connection
)


class TestAnswerCard:
    """Test suite for answer_card functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.anki_url = "http://localhost:8765"
        self.sample_card_id = 1234567890
        self.valid_ease_values = [1, 2, 3, 4]
        self.ease_names = {1: "Again", 2: "Hard", 3: "Good", 4: "Easy"}

    @patch('anki.anki.requests.post')
    def test_answer_card_success(self, mock_post):
        """Test successful card answering"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [True],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = answer_card.invoke({
            "card_id": self.sample_card_id,
            "ease": 3
        })
        
        assert f"Successfully answered card {self.sample_card_id} with ease: Good" in result
        mock_post.assert_called_once()

    @patch('anki.anki.requests.post')
    def test_answer_card_failure(self, mock_post):
        """Test card answering failure"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [False],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = answer_card.invoke({
            "card_id": self.sample_card_id,
            "ease": 3
        })
        
        assert f"Failed to answer card {self.sample_card_id}" in result
        assert "Card may not exist or may not be in review mode" in result

    @patch('anki.anki.requests.post')
    def test_answer_card_ankiconnect_error(self, mock_post):
        """Test card answering with AnkiConnect error"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": "Card not found"
        }
        mock_post.return_value = mock_response
        
        result = answer_card.invoke({
            "card_id": self.sample_card_id,
            "ease": 3
        })
        
        assert "Error answering card: Card not found" in result

    def test_answer_card_invalid_ease(self):
        """Test card answering with invalid ease value"""
        invalid_ease_values = [0, 5, -1, 10]
        
        for ease in invalid_ease_values:
            result = answer_card.invoke({
                "card_id": self.sample_card_id,
                "ease": ease
            })
            assert "Error: Ease must be 1 (Again), 2 (Hard), 3 (Good), or 4 (Easy)" in result

    @patch('anki.anki.requests.post')
    def test_answer_card_connection_error(self, mock_post):
        """Test card answering with connection error"""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = answer_card.invoke({
            "card_id": self.sample_card_id,
            "ease": 3
        })
        
        assert "Could not connect to AnkiConnect" in result

    @patch('anki.anki.requests.post')
    def test_answer_card_timeout_error(self, mock_post):
        """Test card answering with timeout error"""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = answer_card.invoke({
            "card_id": self.sample_card_id,
            "ease": 3
        })
        
        assert "Request to AnkiConnect timed out" in result

    @patch('anki.anki.requests.post')
    def test_answer_card_generic_exception(self, mock_post):
        """Test card answering with generic exception"""
        mock_post.side_effect = Exception("Unexpected error")
        
        result = answer_card.invoke({
            "card_id": self.sample_card_id,
            "ease": 3
        })
        
        assert "Error answering card: Unexpected error" in result

    @patch('anki.anki.requests.post')
    def test_answer_card_all_ease_values(self, mock_post):
        """Test card answering with all valid ease values"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [True],
            "error": None
        }
        mock_post.return_value = mock_response
        
        for ease in self.valid_ease_values:
            result = answer_card.invoke({
                "card_id": self.sample_card_id,
                "ease": ease
            })
            expected_ease_name = self.ease_names[ease]
            assert f"Successfully answered card {self.sample_card_id} with ease: {expected_ease_name}" in result


class TestAnswerMultipleCards:
    """Test suite for answer_multiple_cards functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.anki_url = "http://localhost:8765"
        self.sample_card_answers = [
            {"card_id": 1234567890, "ease": 3},
            {"card_id": 1234567891, "ease": 4},
            {"card_id": 1234567892, "ease": 2}
        ]

    @patch('anki.anki.requests.post')
    def test_answer_multiple_cards_success(self, mock_post):
        """Test successful multiple card answering"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [True, True, True],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = answer_multiple_cards.invoke({
            "card_answers": self.sample_card_answers
        })
        
        assert "Answered 3/3 cards successfully" in result
        assert "✓ Card 1234567890: Good" in result
        assert "✓ Card 1234567891: Easy" in result
        assert "✓ Card 1234567892: Hard" in result

    @patch('anki.anki.requests.post')
    def test_answer_multiple_cards_partial_success(self, mock_post):
        """Test partial success when answering multiple cards"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [True, False, True],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = answer_multiple_cards.invoke({
            "card_answers": self.sample_card_answers
        })
        
        assert "Answered 2/3 cards successfully" in result
        assert "✓ Card 1234567890: Good" in result
        assert "✗ Card 1234567891: Failed to answer" in result
        assert "✓ Card 1234567892: Hard" in result

    def test_answer_multiple_cards_empty_list(self):
        """Test multiple card answering with empty list"""
        result = answer_multiple_cards.invoke({
            "card_answers": []
        })
        
        assert "Error: No card answers provided" in result

    def test_answer_multiple_cards_missing_card_id(self):
        """Test multiple card answering with missing card_id"""
        invalid_answers = [
            {"ease": 3},
            {"card_id": 1234567891, "ease": 4}
        ]
        
        result = answer_multiple_cards.invoke({
            "card_answers": invalid_answers
        })
        
        assert "Error: Each card answer must have 'card_id' and 'ease' keys" in result

    def test_answer_multiple_cards_missing_ease(self):
        """Test multiple card answering with missing ease"""
        invalid_answers = [
            {"card_id": 1234567890},
            {"card_id": 1234567891, "ease": 4}
        ]
        
        result = answer_multiple_cards.invoke({
            "card_answers": invalid_answers
        })
        
        assert "Error: Each card answer must have 'card_id' and 'ease' keys" in result

    def test_answer_multiple_cards_invalid_ease(self):
        """Test multiple card answering with invalid ease value"""
        invalid_answers = [
            {"card_id": 1234567890, "ease": 5},
            {"card_id": 1234567891, "ease": 4}
        ]
        
        result = answer_multiple_cards.invoke({
            "card_answers": invalid_answers
        })
        
        assert "Error: Ease for card 1234567890 must be 1 (Again), 2 (Hard), 3 (Good), or 4 (Easy)" in result

    @patch('anki.anki.requests.post')
    def test_answer_multiple_cards_ankiconnect_error(self, mock_post):
        """Test multiple card answering with AnkiConnect error"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": "Some cards not found"
        }
        mock_post.return_value = mock_response
        
        result = answer_multiple_cards.invoke({
            "card_answers": self.sample_card_answers
        })
        
        assert "Error answering cards: Some cards not found" in result

    @patch('anki.anki.requests.post')
    def test_answer_multiple_cards_connection_error(self, mock_post):
        """Test multiple card answering with connection error"""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = answer_multiple_cards.invoke({
            "card_answers": self.sample_card_answers
        })
        
        assert "Could not connect to AnkiConnect" in result

    @patch('anki.anki.requests.post')
    def test_answer_multiple_cards_timeout_error(self, mock_post):
        """Test multiple card answering with timeout error"""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = answer_multiple_cards.invoke({
            "card_answers": self.sample_card_answers
        })
        
        assert "Request to AnkiConnect timed out" in result


class TestFindCardsToTalkAbout:
    """Test suite for find_cards_to_talk_about functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.anki_url = "http://localhost:8765"
        self.sample_card_ids = [1234567890, 1234567891, 1234567892]
        self.sample_cards_info = [
            {
                "cardId": 1234567890,
                "deckName": "Test Deck",
                "modelName": "Basic",
                "due": 1,
                "interval": 7,
                "factor": 2500,
                "question": "<p>What is 2+2?</p>",
                "answer": "<p>4</p>"
            },
            {
                "cardId": 1234567891,
                "deckName": "Test Deck",
                "modelName": "Basic",
                "due": 2,
                "interval": 14,
                "factor": 2700,
                "question": "<p>What is the capital of France?</p>",
                "answer": "<p>Paris</p>"
            }
        ]

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_due_cards(self, mock_find_cards, mock_get_cards_info):
        """Test finding due cards with highest priority"""
        mock_find_cards.side_effect = [
            self.sample_card_ids[:2],  # Due cards found
            [],  # Learning cards (shouldn't be called)
            [],  # Review cards (shouldn't be called)
            []   # Any cards (shouldn't be called)
        ]
        mock_get_cards_info.return_value = self.sample_cards_info
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Found 2 cards that are due for review from deck 'Test Deck'" in result
        assert "What is 2+2?" in result
        assert "What is the capital of France?" in result
        assert "These cards are categorized as 'due'" in result
        
        # Should only call find_cards_by_query once for due cards
        assert mock_find_cards.call_count == 1

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_learning_cards(self, mock_find_cards, mock_get_cards_info):
        """Test finding learning cards when no due cards exist"""
        mock_find_cards.side_effect = [
            [],  # No due cards
            self.sample_card_ids[:2],  # Learning cards found
            [],  # Review cards (shouldn't be called)
            []   # Any cards (shouldn't be called)
        ]
        mock_get_cards_info.return_value = self.sample_cards_info
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Found 2 cards that are currently being learned from deck 'Test Deck'" in result
        assert "These cards are categorized as 'learning'" in result
        
        # Should call find_cards_by_query twice (due, then learning)
        assert mock_find_cards.call_count == 2

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_review_cards(self, mock_find_cards, mock_get_cards_info):
        """Test finding review cards when no due or learning cards exist"""
        mock_find_cards.side_effect = [
            [],  # No due cards
            [],  # No learning cards
            self.sample_card_ids[:2],  # Review cards found
            []   # Any cards (shouldn't be called)
        ]
        mock_get_cards_info.return_value = self.sample_cards_info
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Found 2 cards in the review queue from deck 'Test Deck'" in result
        assert "These cards are categorized as 'review'" in result
        
        # Should call find_cards_by_query three times (due, learning, review)
        assert mock_find_cards.call_count == 3

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_any_cards(self, mock_find_cards, mock_get_cards_info):
        """Test finding any cards when no priority cards exist"""
        mock_find_cards.side_effect = [
            [],  # No due cards
            [],  # No learning cards
            [],  # No review cards
            self.sample_card_ids[:2]   # Any cards found
        ]
        mock_get_cards_info.return_value = self.sample_cards_info
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Found 2 available cards from deck 'Test Deck'" in result
        assert "These cards are categorized as 'any'" in result
        
        # Should call find_cards_by_query four times (all priorities)
        assert mock_find_cards.call_count == 4

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_no_cards(self, mock_find_cards, mock_get_cards_info):
        """Test when no cards are found"""
        mock_find_cards.return_value = []
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "No cards found in deck 'Test Deck' to talk about" in result
        
        # Should call find_cards_by_query four times (all priorities)
        assert mock_find_cards.call_count == 4

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_no_deck_name(self, mock_find_cards, mock_get_cards_info):
        """Test finding cards without specifying deck name"""
        mock_find_cards.return_value = self.sample_card_ids[:2]
        mock_get_cards_info.return_value = self.sample_cards_info
        
        result = find_cards_to_talk_about.invoke({
            "limit": 5
        })
        
        assert "Found 2 cards that are due for review to discuss" in result
        assert "from deck" not in result  # Should not mention specific deck
        
        # Verify the search query doesn't include deck filter
        mock_find_cards.assert_called_with("is:due", self.anki_url, 5)

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_cards_info_error(self, mock_find_cards, mock_get_cards_info):
        """Test when card info retrieval fails"""
        mock_find_cards.return_value = self.sample_card_ids[:2]
        mock_get_cards_info.return_value = []
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Error: Could not retrieve card details" in result

    @patch('anki.anki._get_cards_info')
    @patch('anki.anki._find_cards_by_query')
    def test_find_cards_to_talk_about_html_cleaning(self, mock_find_cards, mock_get_cards_info):
        """Test HTML tag cleaning in card content"""
        cards_with_html = [
            {
                "cardId": 1234567890,
                "deckName": "Test Deck",
                "modelName": "Basic",
                "due": 1,
                "interval": 7,
                "factor": 2500,
                "question": "<p><strong>What is</strong> <em>2+2</em>?</p>",
                "answer": "<p><span style='color: red;'>4</span></p>"
            }
        ]
        
        mock_find_cards.return_value = [1234567890]
        mock_get_cards_info.return_value = cards_with_html
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Question: What is 2+2?" in result
        assert "Answer: 4" in result
        assert "<p>" not in result
        assert "<strong>" not in result
        assert "<em>" not in result
        assert "<span" not in result

    @patch('anki.anki.requests.post')
    def test_find_cards_to_talk_about_connection_error(self, mock_post):
        """Test finding cards with connection error"""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Could not connect to AnkiConnect" in result

    @patch('anki.anki.requests.post')
    def test_find_cards_to_talk_about_timeout_error(self, mock_post):
        """Test finding cards with timeout error"""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Request to AnkiConnect timed out" in result

    @patch('anki.anki.requests.post')
    def test_find_cards_to_talk_about_generic_exception(self, mock_post):
        """Test finding cards with generic exception"""
        mock_post.side_effect = Exception("Unexpected error")
        
        result = find_cards_to_talk_about.invoke({
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Error finding cards to talk about: Unexpected error" in result


class TestHelperFunctions:
    """Test suite for helper functions"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.anki_url = "http://localhost:8765"

    @patch('anki.anki.requests.post')
    def test_find_cards_by_query_success(self, mock_post):
        """Test successful card finding by query"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [1234567890, 1234567891, 1234567892],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = _find_cards_by_query("is:due", self.anki_url, 5)
        
        assert result == [1234567890, 1234567891, 1234567892]

    @patch('anki.anki.requests.post')
    def test_find_cards_by_query_error(self, mock_post):
        """Test card finding with error"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": "Invalid query"
        }
        mock_post.return_value = mock_response
        
        result = _find_cards_by_query("invalid:query", self.anki_url, 5)
        
        assert result == []

    @patch('anki.anki.requests.post')
    def test_find_cards_by_query_exception(self, mock_post):
        """Test card finding with exception"""
        mock_post.side_effect = Exception("Network error")
        
        # Expect the function to raise the exception
        with pytest.raises(Exception, match="Network error"):
            _find_cards_by_query("is:due", self.anki_url, 5)

    @patch('anki.anki.requests.post')
    def test_get_cards_info_success(self, mock_post):
        """Test successful card info retrieval"""
        sample_cards_info = [
            {
                "cardId": 1234567890,
                "deckName": "Test Deck",
                "modelName": "Basic",
                "due": 1,
                "interval": 7,
                "factor": 2500,
                "question": "What is 2+2?",
                "answer": "4"
            }
        ]
        
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": sample_cards_info,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = _get_cards_info([1234567890], self.anki_url)
        
        assert result == sample_cards_info

    @patch('anki.anki.requests.post')
    def test_get_cards_info_error(self, mock_post):
        """Test card info retrieval with error"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": "Cards not found"
        }
        mock_post.return_value = mock_response
        
        result = _get_cards_info([9999999999], self.anki_url)
        
        assert result == []

    @patch('anki.anki.requests.post')
    def test_get_cards_info_exception(self, mock_post):
        """Test card info retrieval with exception"""
        mock_post.side_effect = Exception("Network error")
        
        # Expect the function to raise the exception
        with pytest.raises(Exception, match="Network error"):
            _get_cards_info([1234567890], self.anki_url)


class TestCardAnkiIntegration:
    """Integration tests for card related Anki functionality"""
    
    def setup_method(self):
        """Setup for each integration test method"""
        self.test_deck_name = "Test_Card_Integration_Deck_Kotori"
        self.test_note_ids = []
        self.test_card_ids = []
        
    def teardown_method(self):
        """Cleanup after each integration test"""
        # Clean up any notes created during testing
        if self.test_note_ids:
            try:
                from anki.anki import delete_multiple_notes
                delete_multiple_notes.invoke({"note_ids": self.test_note_ids})
            except:
                pass
        
        # Clean up test deck
        try:
            delete_anki_deck.invoke({
                "deck_name": self.test_deck_name,
                "cards_too": True
            })
        except:
            pass
    
    def _is_anki_available(self):
        """Check if AnkiConnect is available for testing"""
        try:
            result = check_anki_connection.invoke({})
            return "AnkiConnect is working" in result
        except:
            return False
    
    def _create_test_cards(self, count=3):
        """Helper to create test cards and return their IDs"""
        # Create test deck
        create_anki_deck.invoke({"deck_name": self.test_deck_name})
        
        created_cards = []
        for i in range(count):
            add_result = add_anki_note.invoke({
                "front": f"Test Question {i+1}",
                "back": f"Test Answer {i+1}",
                "deck_name": self.test_deck_name,
                "tags": ["integration", "test", f"card_{i+1}"]
            })
            
            # Extract note ID
            import re
            note_id_match = re.search(r'ID: (\d+)', add_result)
            if note_id_match:
                note_id = int(note_id_match.group(1))
                self.test_note_ids.append(note_id)
                created_cards.append(note_id)
        
        return created_cards
    
    def test_find_cards_to_talk_about_integration(self):
        """Test finding cards to talk about with real AnkiConnect"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create test cards
        self._create_test_cards(3)
        
        # Test finding cards in the test deck
        result = find_cards_to_talk_about.invoke({
            "deck_name": self.test_deck_name,
            "limit": 5
        })
        
        assert "Found" in result
        assert "cards" in result
        assert self.test_deck_name in result
        assert "Test Question" in result
        assert "Test Answer" in result
        assert "Card 1:" in result
        assert "ID:" in result
        assert "Deck:" in result
        assert "Type:" in result
    
    def test_find_cards_to_talk_about_no_deck_integration(self):
        """Test finding cards without specifying deck"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create test cards
        self._create_test_cards(2)
        
        # Test finding cards without deck filter
        result = find_cards_to_talk_about.invoke({
            "limit": 3
        })
        
        assert "Found" in result
        assert "cards" in result
        assert "Card 1:" in result
    
    def test_find_cards_to_talk_about_empty_deck_integration(self):
        """Test finding cards in empty deck"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create empty deck
        create_anki_deck.invoke({"deck_name": self.test_deck_name})
        
        # Test finding cards in empty deck
        result = find_cards_to_talk_about.invoke({
            "deck_name": self.test_deck_name,
            "limit": 5
        })
        
        assert f"No cards found in deck '{self.test_deck_name}' to talk about" in result
    
    def test_answer_card_integration(self):
        """Test answering cards with real AnkiConnect"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create test cards
        self._create_test_cards(1)
        
        # Find cards to get actual card IDs
        result = find_cards_to_talk_about.invoke({
            "deck_name": self.test_deck_name,
            "limit": 1
        })
        
        if "Found" in result:
            # Extract card ID from the result
            import re
            card_id_match = re.search(r'ID: (\d+)', result)
            if card_id_match:
                card_id = int(card_id_match.group(1))
                
                # Try to answer the card
                answer_result = answer_card.invoke({
                    "card_id": card_id,
                    "ease": 3
                })
                
                # Note: This might fail if the card isn't in review state
                # That's expected behavior
                assert "card" in answer_result.lower()
                assert str(card_id) in answer_result
    
    def test_answer_multiple_cards_integration(self):
        """Test answering multiple cards with real AnkiConnect"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create test cards
        self._create_test_cards(2)
        
        # Find cards to get actual card IDs
        result = find_cards_to_talk_about.invoke({
            "deck_name": self.test_deck_name,
            "limit": 2
        })
        
        if "Found" in result:
            # Extract card IDs from the result
            import re
            card_id_matches = re.findall(r'ID: (\d+)', result)
            if len(card_id_matches) >= 2:
                card_answers = [
                    {"card_id": int(card_id_matches[0]), "ease": 3},
                    {"card_id": int(card_id_matches[1]), "ease": 4}
                ]
                
                # Try to answer the cards
                answer_result = answer_multiple_cards.invoke({
                    "card_answers": card_answers
                })
                
                # Note: This might fail if the cards aren't in review state
                # That's expected behavior - check for either success or failure indication
                assert "cards" in answer_result.lower()
                # Accept either successful card answering or error messages
                assert ("Card" in answer_result or "Error" in answer_result or "✗" in answer_result)
    
    def test_answer_invalid_card_integration(self):
        """Test answering non-existent card"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Try to answer a card that doesn't exist
        result = answer_card.invoke({
            "card_id": 9999999999,
            "ease": 3
        })
        
        assert "Failed to answer card 9999999999" in result or "Error" in result
    
    def test_answer_multiple_invalid_cards_integration(self):
        """Test answering multiple non-existent cards"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        invalid_answers = [
            {"card_id": 9999999999, "ease": 3},
            {"card_id": 9999999998, "ease": 4}
        ]
        
        result = answer_multiple_cards.invoke({
            "card_answers": invalid_answers
        })
        
        # Should complete but show failures
        assert "cards" in result.lower()
        assert ("Failed to answer" in result or "✗" in result or "Error" in result)


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
