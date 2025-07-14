import json
import requests
from typing import Dict, List, Optional
from langchain_core.tools import tool


@tool
def add_anki_note(
    front: str,
    back: str,
    deck_name: str = "Default",
    note_type: str = "Basic",
    tags: Optional[List[str]] = None,
    audio_url: Optional[str] = None
) -> str:
    """
    Add a note to Anki using AnkiConnect.
    
    Args:
        front: The front side of the card (question/prompt)
        back: The back side of the card (answer/explanation)
        deck_name: Name of the Anki deck to add the note to (default: "Default")
        note_type: Type of note template (default: "Basic")
        tags: Optional list of tags to add to the note
        audio_url: Optional URL of audio file to attach to the note
        
    Returns:
        String indicating success or failure of the operation
    """
    try:
        # AnkiConnect default URL
        anki_connect_url = "http://localhost:8765"
        
        # Prepare the fields based on note type
        fields = {
            "Front": front,
            "Back": back
        }
        
        # Prepare the note data
        note_data = {
            "deckName": deck_name,
            "modelName": note_type,
            "fields": fields,
            "options": {
                "allowDuplicate": False,
                "duplicateScope": "deck"
            }
        }
        
        # Add tags if provided
        if tags:
            note_data["tags"] = tags
        
        # Prepare the AnkiConnect request
        payload = {
            "action": "addNote",
            "version": 6,
            "params": {
                "note": note_data
            }
        }
        
        # Make the request to AnkiConnect
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error adding note to Anki: {result['error']}"
        
        note_id = result.get("result")
        
        # If audio URL is provided, add it to the note
        if audio_url and note_id:
            audio_result = _add_audio_to_note(note_id, audio_url, anki_connect_url)
            if "Error" in audio_result:
                return f"Note added successfully (ID: {note_id}), but failed to add audio: {audio_result}"
        
        return f"Successfully added note to Anki deck '{deck_name}' with ID: {note_id}"
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error adding note to Anki: {str(e)}"


def _add_audio_to_note(note_id: int, audio_url: str, anki_connect_url: str) -> str:
    """
    Helper function to add audio to an existing note.
    
    Args:
        note_id: The ID of the note to add audio to
        audio_url: URL of the audio file
        anki_connect_url: AnkiConnect server URL
        
    Returns:
        String indicating success or failure
    """
    try:
        # Download audio and store it in Anki's media folder
        audio_payload = {
            "action": "storeMediaFile",
            "version": 6,
            "params": {
                "filename": f"audio_{note_id}.mp3",
                "url": audio_url
            }
        }
        
        audio_response = requests.post(anki_connect_url, json=audio_payload, timeout=10)
        audio_response.raise_for_status()
        
        audio_result = audio_response.json()
        
        if audio_result.get("error"):
            return f"Error storing audio: {audio_result['error']}"
        
        # Update the note to include the audio
        filename = audio_result.get("result")
        if filename:
            update_payload = {
                "action": "updateNoteFields",
                "version": 6,
                "params": {
                    "note": {
                        "id": note_id,
                        "fields": {
                            "Back": f"[sound:{filename}]"  # Add audio to back field
                        }
                    }
                }
            }
            
            update_response = requests.post(anki_connect_url, json=update_payload, timeout=10)
            update_response.raise_for_status()
            
            update_result = update_response.json()
            
            if update_result.get("error"):
                return f"Error updating note with audio: {update_result['error']}"
            
            return "Audio added successfully"
        
        return "Error: No filename returned from audio storage"
        
    except Exception as e:
        return f"Error adding audio: {str(e)}"


@tool
def get_anki_decks() -> str:
    """
    Get a list of all available Anki decks.
    
    Returns:
        String containing the list of deck names or error message
    """
    try:
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "deckNames",
            "version": 6
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error getting deck names: {result['error']}"
        
        decks = result.get("result", [])
        
        if not decks:
            return "No decks found in Anki"
        
        return f"Available Anki decks: {', '.join(decks)}"
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error getting deck names: {str(e)}"


@tool
def check_anki_connection() -> str:
    """
    Check if AnkiConnect is available and working.
    
    Returns:
        String indicating the connection status
    """
    try:
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "version",
            "version": 6
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=5)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"AnkiConnect error: {result['error']}"
        
        version = result.get("result")
        return f"AnkiConnect is working! Version: {version}"
        
    except requests.exceptions.ConnectionError:
        return "AnkiConnect is not available. Make sure:\n1. Anki is running\n2. AnkiConnect addon is installed\n3. AnkiConnect is enabled"
    except requests.exceptions.Timeout:
        return "Connection to AnkiConnect timed out"
    except Exception as e:
        return f"Error checking AnkiConnect: {str(e)}"


@tool
def query_anki_notes(
    query: str = "",
    deck_name: Optional[str] = None,
    note_type: Optional[str] = None,
    tags: Optional[List[str]] = None,
    limit: int = 20
) -> str:
    """
    Query and search for notes in Anki using various filters.
    
    Args:
        query: Search query string (searches in note content)
        deck_name: Filter by specific deck name
        note_type: Filter by note type/model
        tags: Filter by tags (notes must have ALL specified tags)
        limit: Maximum number of notes to return (default: 20)
        
    Returns:
        String containing the found notes or error message
    """
    try:
        anki_connect_url = "http://localhost:8765"
        
        # Build the search query
        search_parts = []
        
        if query:
            search_parts.append(f'"{query}"')
        
        if deck_name:
            search_parts.append(f'deck:"{deck_name}"')
        
        if note_type:
            search_parts.append(f'note:"{note_type}"')
        
        if tags:
            for tag in tags:
                search_parts.append(f'tag:{tag}')
        
        # If no specific filters, search all notes
        search_query = " ".join(search_parts) if search_parts else "*"
        
        # First, find note IDs that match the search
        find_payload = {
            "action": "findNotes",
            "version": 6,
            "params": {
                "query": search_query
            }
        }
        
        response = requests.post(anki_connect_url, json=find_payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error searching notes: {result['error']}"
        
        note_ids = result.get("result", [])
        
        if not note_ids:
            return f"No notes found matching the search criteria: {search_query}"
        
        # Limit the number of results
        note_ids = note_ids[:limit]
        
        # Get detailed information about the notes
        notes_info_payload = {
            "action": "notesInfo",
            "version": 6,
            "params": {
                "notes": note_ids
            }
        }
        
        notes_response = requests.post(anki_connect_url, json=notes_info_payload, timeout=10)
        notes_response.raise_for_status()
        
        notes_result = notes_response.json()
        
        if notes_result.get("error"):
            return f"Error getting note details: {notes_result['error']}"
        
        notes_data = notes_result.get("result", [])
        
        if not notes_data:
            return "No note details found"
        
        # Format the results
        formatted_notes = []
        for note in notes_data:
            note_info = []
            note_info.append(f"Note ID: {note.get('noteId', 'Unknown')}")
            note_info.append(f"Deck: {note.get('deckName', 'Unknown')}")
            note_info.append(f"Model: {note.get('modelName', 'Unknown')}")
            
            # Add fields
            fields = note.get('fields', {})
            for field_name, field_data in fields.items():
                field_value = field_data.get('value', '').strip()
                if field_value:
                    # Truncate long field values
                    if len(field_value) > 100:
                        field_value = field_value[:100] + "..."
                    note_info.append(f"{field_name}: {field_value}")
            
            # Add tags if present
            tags_list = note.get('tags', [])
            if tags_list:
                note_info.append(f"Tags: {', '.join(tags_list)}")
            
            formatted_notes.append("\n".join(note_info))
        
        result_summary = f"Found {len(notes_data)} notes (showing up to {limit}):\n\n"
        result_summary += "\n" + "="*50 + "\n".join(formatted_notes)
        
        return result_summary
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error querying notes: {str(e)}"


@tool
def get_note_by_id(note_id: int) -> str:
    """
    Get detailed information about a specific Anki note by its ID.
    
    Args:
        note_id: The ID of the note to retrieve
        
    Returns:
        String containing the note details or error message
    """
    try:
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "notesInfo",
            "version": 6,
            "params": {
                "notes": [note_id]
            }
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error getting note: {result['error']}"
        
        notes_data = result.get("result", [])
        
        if not notes_data or not notes_data[0]:
            return f"No note found with ID: {note_id}"
        
        note = notes_data[0]
        
        # Format the note details
        note_details = []
        note_details.append(f"Note ID: {note.get('noteId', 'Unknown')}")
        note_details.append(f"Deck: {note.get('deckName', 'Unknown')}")
        note_details.append(f"Model: {note.get('modelName', 'Unknown')}")
        note_details.append(f"Created: {note.get('mod', 'Unknown')}")
        
        # Add all fields
        fields = note.get('fields', {})
        note_details.append("\nFields:")
        for field_name, field_data in fields.items():
            field_value = field_data.get('value', '').strip()
            note_details.append(f"  {field_name}: {field_value}")
        
        # Add tags
        tags_list = note.get('tags', [])
        if tags_list:
            note_details.append(f"\nTags: {', '.join(tags_list)}")
        
        return "\n".join(note_details)
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error getting note by ID: {str(e)}"


@tool
def search_notes_by_content(content: str, limit: int = 10) -> str:
    """
    Search for notes containing specific content in any field.
    
    Args:
        content: Text content to search for in note fields
        limit: Maximum number of notes to return (default: 10)
        
    Returns:
        String containing matching notes or error message
    """
    try:
        anki_connect_url = "http://localhost:8765"
        
        # Search for notes containing the content
        search_query = f'"{content}"'
        
        find_payload = {
            "action": "findNotes",
            "version": 6,
            "params": {
                "query": search_query
            }
        }
        
        response = requests.post(anki_connect_url, json=find_payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error searching for content: {result['error']}"
        
        note_ids = result.get("result", [])
        
        if not note_ids:
            return f'No notes found containing: "{content}"'
        
        # Limit results
        note_ids = note_ids[:limit]
        
        # Get note details
        notes_info_payload = {
            "action": "notesInfo",
            "version": 6,
            "params": {
                "notes": note_ids
            }
        }
        
        notes_response = requests.post(anki_connect_url, json=notes_info_payload, timeout=10)
        notes_response.raise_for_status()
        
        notes_result = notes_response.json()
        
        if notes_result.get("error"):
            return f"Error getting note details: {notes_result['error']}"
        
        notes_data = notes_result.get("result", [])
        
        # Format results with highlighted content
        formatted_notes = []
        for note in notes_data:
            note_summary = []
            note_summary.append(f"ID: {note.get('noteId')} | Deck: {note.get('deckName')}")
            
            # Show relevant fields that contain the search content
            fields = note.get('fields', {})
            for field_name, field_data in fields.items():
                field_value = field_data.get('value', '').strip()
                if content.lower() in field_value.lower():
                    # Truncate and highlight
                    if len(field_value) > 80:
                        field_value = field_value[:80] + "..."
                    note_summary.append(f"  {field_name}: {field_value}")
            
            formatted_notes.append("\n".join(note_summary))
        
        result_text = f'Found {len(notes_data)} notes containing "{content}":\n\n'
        result_text += "\n" + "-"*40 + "\n".join(formatted_notes)
        
        return result_text
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error searching notes by content: {str(e)}"


@tool
def delete_anki_note(note_id: int) -> str:
    """
    Delete a specific note from Anki by its ID.
    
    Args:
        note_id: The ID of the note to delete
        
    Returns:
        String indicating success or failure of the deletion
    """
    try:
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "deleteNotes",
            "version": 6,
            "params": {
                "notes": [note_id]
            }
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error deleting note: {result['error']}"
        
        # The result should be null for successful deletion
        if result.get("result") is None:
            return f"Successfully deleted note with ID: {note_id}"
        else:
            return f"Note deletion completed with result: {result.get('result')}"
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error deleting note: {str(e)}"


@tool
def delete_multiple_notes(note_ids: List[int]) -> str:
    """
    Delete multiple notes from Anki by their IDs.
    
    Args:
        note_ids: List of note IDs to delete
        
    Returns:
        String indicating success or failure of the deletion
    """
    try:
        if not note_ids:
            return "Error: No note IDs provided for deletion"
        
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "deleteNotes",
            "version": 6,
            "params": {
                "notes": note_ids
            }
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error deleting notes: {result['error']}"
        
        # The result should be null for successful deletion
        if result.get("result") is None:
            return f"Successfully deleted {len(note_ids)} notes with IDs: {', '.join(map(str, note_ids))}"
        else:
            return f"Note deletion completed with result: {result.get('result')}"
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error deleting notes: {str(e)}"


@tool
def create_anki_deck(deck_name: str) -> str:
    """
    Create a new deck in Anki.
    
    Args:
        deck_name: Name of the deck to create
        
    Returns:
        String indicating success or failure of the deck creation
    """
    try:
        if not deck_name or not deck_name.strip():
            return "Error: Deck name cannot be empty"
        
        deck_name = deck_name.strip()
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "createDeck",
            "version": 6,
            "params": {
                "deck": deck_name
            }
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error creating deck: {result['error']}"
        
        deck_id = result.get("result")
        
        if deck_id:
            return f"Successfully created deck '{deck_name}' with ID: {deck_id}"
        else:
            return f"Deck '{deck_name}' was created or already exists"
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error creating deck: {str(e)}"


@tool
def delete_anki_deck(deck_name: str, cards_too: bool = False) -> str:
    """
    Delete a deck from Anki.
    
    Args:
        deck_name: Name of the deck to delete
        cards_too: If True, delete all cards in the deck as well. If False, move cards to default deck.
        
    Returns:
        String indicating success or failure of the deck deletion
    """
    try:
        if not deck_name or not deck_name.strip():
            return "Error: Deck name cannot be empty"
        
        deck_name = deck_name.strip()
        anki_connect_url = "http://localhost:8765"
        
        payload = {
            "action": "deleteDecks",
            "version": 6,
            "params": {
                "decks": [deck_name],
                "cardsToo": cards_too
            }
        }
        
        response = requests.post(anki_connect_url, json=payload, timeout=10)
        response.raise_for_status()
        
        result = response.json()
        
        if result.get("error"):
            return f"Error deleting deck: {result['error']}"
        
        # The result should be null for successful deletion
        if result.get("result") is None:
            if cards_too:
                return f"Successfully deleted deck '{deck_name}' and all its cards"
            else:
                return f"Successfully deleted deck '{deck_name}' (cards moved to default deck)"
        else:
            return f"Deck deletion completed with result: {result.get('result')}"
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error deleting deck: {str(e)}"


@tool
def get_deck_stats(deck_name: str) -> str:
    """
    Get statistics for a specific deck.
    
    Args:
        deck_name: Name of the deck to get stats for
        
    Returns:
        String containing deck statistics or error message
    """
    try:
        if not deck_name or not deck_name.strip():
            return "Error: Deck name cannot be empty"
        
        deck_name = deck_name.strip()
        anki_connect_url = "http://localhost:8765"
        
        # Get deck configuration first to verify it exists
        deck_config_payload = {
            "action": "getDeckConfig",
            "version": 6,
            "params": {
                "deck": deck_name
            }
        }
        
        config_response = requests.post(anki_connect_url, json=deck_config_payload, timeout=10)
        config_response.raise_for_status()
        
        config_result = config_response.json()
        
        if config_result.get("error"):
            return f"Error accessing deck: {config_result['error']}"
        
        # Get deck statistics
        stats_payload = {
            "action": "getDeckStats",
            "version": 6,
            "params": {
                "decks": [deck_name]
            }
        }
        
        stats_response = requests.post(anki_connect_url, json=stats_payload, timeout=10)
        stats_response.raise_for_status()
        
        stats_result = stats_response.json()
        
        if stats_result.get("error"):
            return f"Error getting deck stats: {stats_result['error']}"
        
        stats_data = stats_result.get("result", {})
        
        # getDeckStats returns stats with deck ID as key, find the right deck
        deck_stats = None
        for deck_id, stats in stats_data.items():
            if stats.get("name") == deck_name:
                deck_stats = stats
                break
        
        if not deck_stats:
            return f"No statistics found for deck '{deck_name}'"
        
        # Format the statistics
        stats_info = []
        stats_info.append(f"Statistics for deck '{deck_name}':")
        stats_info.append(f"Total notes: {deck_stats.get('total_in_deck', 'Unknown')}")
        stats_info.append(f"New cards: {deck_stats.get('new_count', 'Unknown')}")
        stats_info.append(f"Learning cards: {deck_stats.get('learn_count', 'Unknown')}")
        stats_info.append(f"Review cards: {deck_stats.get('review_count', 'Unknown')}")
        
        return "\n".join(stats_info)
        
    except requests.exceptions.ConnectionError:
        return "Error: Could not connect to AnkiConnect. Make sure Anki is running and AnkiConnect addon is installed."
    except requests.exceptions.Timeout:
        return "Error: Request to AnkiConnect timed out."
    except Exception as e:
        return f"Error getting deck stats: {str(e)}"
