import json
import os
from datetime import datetime

# Get the directory of the current script
script_dir = os.path.dirname(os.path.abspath(__file__))
json_file = os.path.join(script_dir, "resurgence.json")

def load_json():
    """Load the JSON file"""
    try:
        with open(json_file, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading JSON file: {e}")
        return {}

def save_json(data):
    """Save the JSON file with proper formatting"""
    try:
        with open(json_file, 'w') as f:
            json.dump(data, f, indent=2)
        print(f"\nSuccessfully saved to {json_file}")
    except Exception as e:
        print(f"Error saving JSON file: {e}")

def search_entry(data, name):
    """Search for an entry in the JSON data"""
    return data.get(name)

def is_date_more_recent(new_date, old_date):
    """Check if new_date is more recent than old_date (YYYY-MM-DD format)"""
    try:
        new = datetime.strptime(new_date, "%Y-%m-%d")
        old = datetime.strptime(old_date, "%Y-%m-%d")
        return new > old
    except ValueError:
        return False

def main():
    print("=== Resurgence JSON Manager ===\n")
    
    # Load the JSON file
    data = load_json()
    
    if not data:
        print("Could not load data from JSON file.")
        return
    
    # Ask for input
    search_name = input("Enter the name to search for: ").strip()
    
    if not search_name:
        print("No name provided. Exiting.")
        return
    
    # Search for the entry
    entry = search_entry(data, search_name)
    
    if entry:
        print(f"\nEntry found: {search_name}")
        print(f"  Items: {', '.join(entry.get('items', []))}")
        print(f"  Date: {entry.get('date', 'N/A')}")
        
        # Ask if user wants to update the date
        update = input("\nWould you like to update the date? 'y' or 'n': ").strip().lower()
        
        if update in ['yes', 'y']:
            new_date = input("Enter the new date (YYYY-MM-DD): ").strip()
            
            if new_date:
                current_date = entry.get('date', '')
                
                # Validate date format
                try:
                    datetime.strptime(new_date, "%Y-%m-%d")
                except ValueError:
                    print("Invalid date format. Please use YYYY-MM-DD.")
                    return
                
                # Check if new date is more recent
                if is_date_more_recent(new_date, current_date):
                    data[search_name]['date'] = new_date
                    print(f"Date updated to: {new_date}")
                    save_json(data)
                else:
                    print(f"Error: New date ({new_date}) must be more recent than the current date ({current_date}).")
                    print("Update rejected.")
            else:
                print("No date provided. Update cancelled.")
    else:
        print(f"\nNo entry found for '{search_name}'")
        
        # Ask if user wants to create a new entry
        create = input("Would you like to create a new entry? 'y' or 'n': ").strip().lower()
        
        if create in ['yes', 'y']:
            # Ask for items
            items_input = input("Enter items (comma-separated): ").strip()
            items = [item.strip() for item in items_input.split(',') if item.strip()]
            
            if not items:
                print("No items provided. Entry not created.")
                return
            
            # Ask for date
            date_input = input("Enter the date (YYYY-MM-DD): ").strip()
            
            if not date_input:
                print("No date provided. Entry not created.")
                return
            
            # Create the entry
            data[search_name] = {
                "items": items,
                "date": date_input
            }
            
            print(f"\nNew entry created for '{search_name}':")
            print(f"  Items: {', '.join(items)}")
            print(f"  Date: {date_input}")
            
            # Save the JSON file
            save_json(data)
        else:
            print("Entry creation cancelled.")

if __name__ == "__main__":
    while True:
        main()
