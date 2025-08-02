import time
import uuid
from collections import defaultdict
from datetime import datetime

class ChangeTracker:
    """
    Tracks changes made to files for the undo functionality.
    This enables granular editing operations with the ability to undo specific changes.
    """
    
    def __init__(self):
        self.changes = {}  # change_id -> change_info
        self.files_changed = defaultdict(list)  # file_path -> [change_ids]
        
    def track_change(self, file_path, change_type, original_content, new_content, 
                    metadata=None, change_id=None):
        """
        Record a change to enable future undo operations.
        
        Parameters:
        - file_path: Path to the file that was changed
        - change_type: Type of change (e.g., 'replacetext', 'insertlines')
        - original_content: Original content before the change
        - new_content: New content after the change
        - metadata: Additional information about the change (line numbers, positions, etc.)
        - change_id: Optional custom ID for the change (if None, one will be generated)
        
        Returns:
        - change_id: Unique identifier for the change
        """
        if change_id is None:
            generated_id = self._generate_change_id()
            # Ensure the generated ID is treated as a string
            current_change_id = str(generated_id)
        else:
            # If an ID is provided, ensure it's treated as a string key/value
            current_change_id = str(change_id)

        # Defensive check: Ensure the ID isn't literally the string 'False' or boolean False
        # which might indicate an upstream issue or unexpected input.
        if current_change_id == 'False' or current_change_id is False:
             # Log a warning? For now, generate a new ID to prevent storing False.
             print(f"Warning: change_id evaluated to False for {file_path}. Generating new ID.")
             current_change_id = self._generate_change_id()


        change = {
            # Use the confirmed string ID here
            'id': current_change_id,
            'file_path': file_path,
            'type': change_type,
            'original': original_content,
            'new': new_content,
            'metadata': metadata or {},
            'timestamp': time.time()
        }

        # Use the confirmed string ID for storage and return
        self.changes[current_change_id] = change
        self.files_changed[file_path].append(current_change_id)
        return current_change_id
    
    def undo_change(self, change_id):
        """
        Get information needed to reverse a specific change by ID.
        
        Parameters:
        - change_id: ID of the change to undo
        
        Returns:
        - (success, message, change_info): Tuple with success flag, message, and change information
        """
        if change_id not in self.changes:
            return False, f"Change ID {change_id} not found", None
        
        change = self.changes[change_id]
        
        # Mark this change as undone by removing it from the tracking dictionaries
        self.files_changed[change['file_path']].remove(change_id)
        if not self.files_changed[change['file_path']]:
            del self.files_changed[change['file_path']]
        
        # Keep the change in the changes dict but mark it as undone
        change['undone'] = True
        change['undone_at'] = time.time()
        
        return True, f"Undid change {change_id} in {change['file_path']}", change
    
    def get_last_change(self, file_path):
        """
        Get the most recent change for a specific file.
        
        Parameters:
        - file_path: Path to the file
        
        Returns:
        - change_id or None if no changes found
        """
        changes = self.files_changed.get(file_path, [])
        if not changes:
            return None
        return changes[-1]
    
    def list_changes(self, file_path=None, limit=10):
        """
        List recent changes, optionally filtered by file.
        
        Parameters:
        - file_path: Optional path to filter changes by file
        - limit: Maximum number of changes to list
        
        Returns:
        - List of change dictionaries
        """
        if file_path:
            # Get changes only for the specified file
            change_ids = self.files_changed.get(file_path, [])
            changes = [self.changes[cid] for cid in change_ids if cid in self.changes]
        else:
            # Get all changes
            changes = list(self.changes.values())
        
        # Filter out undone changes and sort by timestamp (most recent first)
        changes = [c for c in changes if not c.get('undone', False)]
        changes = sorted(changes, key=lambda c: c['timestamp'], reverse=True)
        
        # Apply limit
        return changes[:limit]
    
    def _generate_change_id(self):
        """Generate a unique ID for a change."""
        return str(uuid.uuid4())[:8]  # Short, readable ID
