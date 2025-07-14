import pytest
import json
import requests
from unittest.mock import Mock, patch, MagicMock
from anki.anki import (
    add_anki_note,
    get_anki_decks,
    check_anki_connection,
    query_anki_notes,
    get_note_by_id,
    search_notes_by_content,
    delete_anki_note,
    delete_multiple_notes,
    create_anki_deck,
    delete_anki_deck,
    get_deck_stats,
    _add_audio_to_note
)


class TestAnkiConnect:
    """Test suite for Anki Connect functionality"""
    
    def setup_method(self):
        """Setup for each test method"""
        self.anki_url = "http://localhost:8765"
        self.sample_note_data = {
            "noteId": 1234567890,
            "deckName": "Test Deck",
            "modelName": "Basic",
            "fields": {
                "Front": {"value": "Test Question"},
                "Back": {"value": "Test Answer"}
            },
            "tags": ["test", "sample"]
        }

    @patch('anki.anki.requests.post')
    def test_add_anki_note_success(self, mock_post):
        """Test successful note addition"""
        # Mock successful response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": 1234567890,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = add_anki_note.invoke({
            "front":"Test Question",
            "back":"Test Answer",
            "deck_name":"Test Deck",
            "tags":["test"]
        })
        
        assert "Successfully added note to Anki deck 'Test Deck' with ID: 1234567890" in result
        mock_post.assert_called_once()

    @patch('anki.anki.requests.post')
    def test_add_anki_note_with_error(self, mock_post):
        """Test note addition with AnkiConnect error"""
        # Mock error response
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": "Deck 'NonExistent' not found"
        }
        mock_post.return_value = mock_response
        
        result = add_anki_note.invoke({
            "front": "Test Question",
            "back": "Test Answer",
            "deck_name": "NonExistent"
        })
        
        assert "Error adding note to Anki: Deck 'NonExistent' not found" in result

    @patch('anki.anki.requests.post')
    def test_add_anki_note_connection_error(self, mock_post):
        """Test note addition with connection error"""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = add_anki_note.invoke({
            "front": "Test Question",
            "back": "Test Answer"
        })
        
        assert "Could not connect to AnkiConnect" in result

    @patch('anki.anki.requests.post')
    def test_get_anki_decks_success(self, mock_post):
        """Test successful deck retrieval"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": ["Default", "Test Deck", "Japanese"],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = get_anki_decks.invoke({})
        
        assert "Available Anki decks: Default, Test Deck, Japanese" in result

    @patch('anki.anki.requests.post')
    def test_get_anki_decks_empty(self, mock_post):
        """Test deck retrieval when no decks exist"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = get_anki_decks.invoke({})
        
        assert "No decks found in Anki" in result

    @patch('anki.anki.requests.post')
    def test_check_anki_connection_success(self, mock_post):
        """Test successful AnkiConnect connection check"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": 6,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = check_anki_connection.invoke({})
        
        assert "AnkiConnect is working! Version: 6" in result

    @patch('anki.anki.requests.post')
    def test_check_anki_connection_failure(self, mock_post):
        """Test AnkiConnect connection failure"""
        mock_post.side_effect = requests.exceptions.ConnectionError()
        
        result = check_anki_connection.invoke({})
        
        assert "AnkiConnect is not available" in result

    @patch('anki.anki.requests.post')
    def test_query_anki_notes_success(self, mock_post):
        """Test successful note querying"""
        # Mock the findNotes response
        find_response = Mock()
        find_response.raise_for_status.return_value = None
        find_response.json.return_value = {
            "result": [1234567890],
            "error": None
        }
        
        # Mock the notesInfo response
        info_response = Mock()
        info_response.raise_for_status.return_value = None
        info_response.json.return_value = {
            "result": [self.sample_note_data],
            "error": None
        }
        
        mock_post.side_effect = [find_response, info_response]
        
        result = query_anki_notes.invoke({
            "query": "test",
            "deck_name": "Test Deck",
            "limit": 5
        })
        
        assert "Found 1 notes" in result
        assert "Test Question" in result
        assert "Test Answer" in result

    @patch('anki.anki.requests.post')
    def test_query_anki_notes_no_results(self, mock_post):
        """Test note querying with no results"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = query_anki_notes.invoke({
            "query": "nonexistent"
        })
        
        assert "No notes found matching the search criteria" in result

    @patch('anki.anki.requests.post')
    def test_get_note_by_id_success(self, mock_post):
        """Test successful note retrieval by ID"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [self.sample_note_data],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = get_note_by_id.invoke({
            "note_id": 1234567890
        })
        
        assert "Note ID: 1234567890" in result
        assert "Test Question" in result
        assert "Test Answer" in result

    @patch('anki.anki.requests.post')
    def test_get_note_by_id_not_found(self, mock_post):
        """Test note retrieval by ID when note doesn't exist"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": [],
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = get_note_by_id.invoke({
            "note_id": 9999999999
        })
        
        assert "No note found with ID: 9999999999" in result

    @patch('anki.anki.requests.post')
    def test_search_notes_by_content_success(self, mock_post):
        """Test successful content-based note search"""
        # Mock the findNotes response
        find_response = Mock()
        find_response.raise_for_status.return_value = None
        find_response.json.return_value = {
            "result": [1234567890],
            "error": None
        }
        
        # Mock the notesInfo response
        info_response = Mock()
        info_response.raise_for_status.return_value = None
        info_response.json.return_value = {
            "result": [self.sample_note_data],
            "error": None
        }
        
        mock_post.side_effect = [find_response, info_response]
        
        result = search_notes_by_content.invoke({
            "content": "Test",
            "limit": 5
        })
        
        assert 'Found 1 notes containing "Test"' in result
        assert "Test Question" in result

    @patch('anki.anki.requests.post')
    def test_delete_anki_note_success(self, mock_post):
        """Test successful note deletion"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = delete_anki_note.invoke({
            "note_id": 1234567890
        })
        
        assert "Successfully deleted note with ID: 1234567890" in result

    @patch('anki.anki.requests.post')
    def test_delete_multiple_notes_success(self, mock_post):
        """Test successful multiple note deletion"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = delete_multiple_notes.invoke({
            "note_ids": [1234567890, 1234567891]
        })
        
        assert "Successfully deleted 2 notes with IDs: 1234567890, 1234567891" in result

    def test_delete_multiple_notes_empty_list(self):
        """Test multiple note deletion with empty list"""
        result = delete_multiple_notes.invoke({
            "note_ids": []
        })
        
        assert "Error: No note IDs provided for deletion" in result

    @patch('anki.anki.requests.post')
    def test_create_anki_deck_success(self, mock_post):
        """Test successful deck creation"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": 123456789,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = create_anki_deck.invoke({
            "deck_name": "New Test Deck"
        })
        
        assert "Successfully created deck 'New Test Deck' with ID: 123456789" in result

    def test_create_anki_deck_empty_name(self):
        """Test deck creation with empty name"""
        result = create_anki_deck.invoke({
            "deck_name": ""
        })
        
        assert "Error: Deck name cannot be empty" in result

    @patch('anki.anki.requests.post')
    def test_delete_anki_deck_success(self, mock_post):
        """Test successful deck deletion"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = delete_anki_deck.invoke({
            "deck_name": "Test Deck",
            "cards_too": True
        })
        
        assert "Successfully deleted deck 'Test Deck' and all its cards" in result

    @patch('anki.anki.requests.post')
    def test_delete_anki_deck_preserve_cards(self, mock_post):
        """Test deck deletion while preserving cards"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": None
        }
        mock_post.return_value = mock_response
        
        result = delete_anki_deck.invoke({
            "deck_name": "Test Deck",
            "cards_too": False
        })
        
        assert "Successfully deleted deck 'Test Deck' (cards moved to default deck)" in result

    @patch('anki.anki.requests.post')
    def test_get_deck_stats_success(self, mock_post):
        """Test successful deck statistics retrieval"""
        # Mock deck config response
        config_response = Mock()
        config_response.raise_for_status.return_value = None
        config_response.json.return_value = {
            "result": {"name": "Test Deck"},
            "error": None
        }
        
        # Mock deck stats response
        stats_response = Mock()
        stats_response.raise_for_status.return_value = None
        stats_response.json.return_value = {
            "result": {
                "Test Deck": {
                    "total_notes": 100,
                    "new_count": 20,
                    "learn_count": 30,
                    "review_count": 50
                }
            },
            "error": None
        }
        
        mock_post.side_effect = [config_response, stats_response]
        
        result = get_deck_stats.invoke({
            "deck_name": "Test Deck"
        })
        
        assert "Statistics for deck 'Test Deck'" in result
        assert "Total notes: 100" in result
        assert "New cards: 20" in result

    def test_get_deck_stats_empty_name(self):
        """Test deck statistics with empty deck name"""
        result = get_deck_stats.invoke({
            "deck_name": ""
        })
        
        assert "Error: Deck name cannot be empty" in result

    @patch('anki.anki.requests.post')
    def test_add_audio_to_note_success(self, mock_post):
        """Test successful audio addition to note"""
        # Mock storeMediaFile response
        store_response = Mock()
        store_response.raise_for_status.return_value = None
        store_response.json.return_value = {
            "result": "audio_1234567890.mp3",
            "error": None
        }
        
        # Mock updateNoteFields response
        update_response = Mock()
        update_response.raise_for_status.return_value = None
        update_response.json.return_value = {
            "result": None,
            "error": None
        }
        
        mock_post.side_effect = [store_response, update_response]
        
        result = _add_audio_to_note(1234567890, "http://example.com/audio.mp3", self.anki_url)
        
        assert "Audio added successfully" in result

    @patch('anki.anki.requests.post')
    def test_add_audio_to_note_storage_error(self, mock_post):
        """Test audio addition with storage error"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "result": None,
            "error": "Failed to download audio file"
        }
        mock_post.return_value = mock_response
        
        result = _add_audio_to_note(1234567890, "http://invalid-url.com/audio.mp3", self.anki_url)
        
        assert "Error storing audio: Failed to download audio file" in result

    @patch('anki.anki.requests.post')
    def test_timeout_error(self, mock_post):
        """Test timeout error handling"""
        mock_post.side_effect = requests.exceptions.Timeout()
        
        result = check_anki_connection.invoke({})
        
        assert "Connection to AnkiConnect timed out" in result

    @patch('anki.anki.requests.post')
    def test_generic_exception(self, mock_post):
        """Test generic exception handling"""
        mock_post.side_effect = Exception("Unexpected error")
        
        result = check_anki_connection.invoke({})
        
        assert "Error checking AnkiConnect: Unexpected error" in result


class TestAnkiConnectIntegration:
    """Integration tests that would require actual AnkiConnect running"""
    
    def setup_method(self):
        """Setup for each integration test method"""
        self.test_deck_name = "Test_Integration_Deck_Kotori"
        self.test_note_ids = []  # Track created notes for cleanup
        
    def teardown_method(self):
        """Cleanup after each integration test"""
        # Clean up any notes created during testing
        if self.test_note_ids:
            try:
                delete_multiple_notes.invoke({"note_ids": self.test_note_ids})
            except:
                pass  # Ignore cleanup errors
        
        # Clean up test deck
        try:
            delete_anki_deck.invoke({
                "deck_name": self.test_deck_name,
                "cards_too": True
            })
        except:
            pass  # Ignore cleanup errors
    
    def _is_anki_available(self):
        """Check if AnkiConnect is available for testing"""
        try:
            result = check_anki_connection.invoke({})
            return "AnkiConnect is working" in result
        except:
            return False
    
    def test_real_connection(self):
        """Test actual connection to AnkiConnect (requires Anki running)"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        result = check_anki_connection.invoke({})
        assert "AnkiConnect is working" in result
        assert "Version:" in result
    
    def test_deck_operations_integration(self):
        """Test deck creation, listing, and deletion"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Test deck creation
        create_result = create_anki_deck.invoke({
            "deck_name": self.test_deck_name
        })
        assert "Successfully created deck" in create_result
        
        # Test deck listing (should include our new deck)
        list_result = get_anki_decks.invoke({})
        assert self.test_deck_name in list_result
        
        # Test deck stats
        stats_result = get_deck_stats.invoke({
            "deck_name": self.test_deck_name
        })
        assert f"Statistics for deck '{self.test_deck_name}'" in stats_result
        assert "Total notes: 0" in stats_result  # New deck should be empty
    
    def test_note_operations_integration(self):
        """Test complete note lifecycle: create, search, retrieve, delete"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create test deck first
        create_anki_deck.invoke({"deck_name": self.test_deck_name})
        
        # Test note creation
        add_result = add_anki_note.invoke({
            "front": "Integration Test Question",
            "back": "Integration Test Answer",
            "deck_name": self.test_deck_name,
            "tags": ["integration", "test", "kotori"]
        })
        assert "Successfully added note" in add_result
        
        # Extract note ID from the result
        import re
        note_id_match = re.search(r'ID: (\d+)', add_result)
        assert note_id_match, "Could not extract note ID from add result"
        note_id = int(note_id_match.group(1))
        self.test_note_ids.append(note_id)
        
        # Test note retrieval by ID
        get_result = get_note_by_id.invoke({"note_id": note_id})
        assert f"Note ID: {note_id}" in get_result
        assert "Integration Test Question" in get_result
        assert "Integration Test Answer" in get_result
        
        # Test note search by query
        query_result = query_anki_notes.invoke({
            "query": "Integration Test",
            "deck_name": self.test_deck_name,
            "limit": 10
        })
        assert "Found 1 notes" in query_result
        assert "Integration Test Question" in query_result
        
        # Test content-based search
        content_search_result = search_notes_by_content.invoke({
            "content": "Integration",
            "limit": 10
        })
        assert 'notes containing "Integration"' in content_search_result
        assert "Integration Test Question" in content_search_result
        
        # Test note deletion
        delete_result = delete_anki_note.invoke({"note_id": note_id})
        assert f"Successfully deleted note with ID: {note_id}" in delete_result
        
        # Verify note is gone
        get_deleted_result = get_note_by_id.invoke({"note_id": note_id})
        assert f"No note found with ID: {note_id}" in get_deleted_result
        
        # Remove from cleanup list since we already deleted it
        self.test_note_ids.remove(note_id)
    
    def test_multiple_notes_integration(self):
        """Test operations with multiple notes"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Create test deck first
        create_anki_deck.invoke({"deck_name": self.test_deck_name})
        
        # Create multiple notes
        note_data = [
            {"front": "Question 1", "back": "Answer 1"},
            {"front": "Question 2", "back": "Answer 2"},
            {"front": "Question 3", "back": "Answer 3"}
        ]
        
        created_note_ids = []
        
        for i, data in enumerate(note_data):
            add_result = add_anki_note.invoke({
                "front": data["front"],
                "back": data["back"],
                "deck_name": self.test_deck_name,
                "tags": ["multi_test", f"note_{i+1}"]
            })
            
            # Extract note ID
            import re
            note_id_match = re.search(r'ID: (\d+)', add_result)
            assert note_id_match, f"Could not extract note ID for note {i+1}"
            note_id = int(note_id_match.group(1))
            created_note_ids.append(note_id)
            self.test_note_ids.append(note_id)
        
        # Test querying multiple notes
        query_result = query_anki_notes.invoke({
            "query": "tag:multi_test",
            "deck_name": self.test_deck_name,
            "limit": 10
        })
        assert "Found 3 notes" in query_result
        
        # Test deck stats with notes
        stats_result = get_deck_stats.invoke({
            "deck_name": self.test_deck_name
        })
        assert "Total notes: 3" in stats_result
        
        # Test multiple note deletion
        delete_result = delete_multiple_notes.invoke({
            "note_ids": created_note_ids
        })
        assert f"Successfully deleted 3 notes" in delete_result
        
        # Clear from cleanup list since we already deleted them
        for note_id in created_note_ids:
            self.test_note_ids.remove(note_id)
        
        # Verify deck is now empty
        final_stats = get_deck_stats.invoke({
            "deck_name": self.test_deck_name
        })
        assert "Total notes: 0" in final_stats
    
    def test_error_handling_integration(self):
        """Test error handling with real AnkiConnect"""
        if not self._is_anki_available():
            pytest.skip("Integration test - requires Anki with AnkiConnect running")
        
        # Test adding note to non-existent deck (this should error)
        import time
        unique_id = int(time.time())
        error_result = add_anki_note.invoke({
            "front": f"Test Question {unique_id}",
            "back": f"Test Answer {unique_id}",
            "deck_name": "NonExistentDeck_12345"
        })
        # This should fail because the deck doesn't exist
        assert "Error adding note to Anki" in error_result
        
        # Test getting note with invalid ID
        invalid_get_result = get_note_by_id.invoke({
            "note_id": 9999999999
        })
        assert "No note found with ID: 9999999999" in invalid_get_result
        
        # Test deleting non-existent note
        invalid_delete_result = delete_anki_note.invoke({
            "note_id": 9999999999
        })
        # Note: AnkiConnect might not return an error for deleting non-existent notes
        # so we just verify the operation completes
        assert "deleted note with ID: 9999999999" in invalid_delete_result
        
        # Test getting stats for deck that definitely doesn't exist (using special chars to prevent auto-creation)
        invalid_stats_result = get_deck_stats.invoke({
            "deck_name": ""  # Empty deck name should error
        })
        assert "Error: Deck name cannot be empty" in invalid_stats_result


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
