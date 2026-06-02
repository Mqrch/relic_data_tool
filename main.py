import requests
import json
import time
import os
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import customtkinter as ctk
from tkinter import messagebox
from alecaData import decrypt_last_data

# Global variables
settings = {}
stat_type = "median"
num_days = 7
resurgence_data = {}
headers = {'Platform': 'pc', 'Language': 'en'}
price_list = {}
error_codes = {}
prime_items = {}
enriched_data = {}
status_text = "Loading cached data..."
relic_rewards_map = {}

# Load settings.json (create with defaults if it doesn't exist)
def load_settings():
    global settings, stat_type, num_days
    try:
        with open("settings.json", "r", encoding="utf-8") as f:
            settings = json.load(f)
    except FileNotFoundError:
        settings = {"stat": "median", "days": 7, "lastDataPath": "%LOCALAPPDATA%\\AlecaFrame\\lastData.dat"}
        with open("settings.json", "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2)
    
    stat_type = settings.get("stat", "median")
    num_days = settings.get("days", 7)

def load_resurgence():
    global resurgence_data
    with open("resurgence.json", "r", encoding="utf-8") as f:
        resurgence_data = json.load(f)

def resolve_reward_type(reward_type, export_recipes, export_weapons, export_resources, export_warframes, dict_en):
    """Resolve a reward type to its final item name"""
    try:
        cleaned_type = reward_type.replace("/StoreItems/", "/")
        if cleaned_type not in export_recipes:
            if cleaned_type in export_resources:
                item_name = export_resources[cleaned_type].get("name")
                print(f"Resolved reward type: {reward_type} -> {item_name} (resource)")
                if item_name in dict_en:
                    print(f"Translated item name: {item_name} -> {dict_en[item_name]}")
                    return dict_en[item_name]
                return item_name
            return None
        recipe = export_recipes[cleaned_type]
        result_type = recipe.get("resultType")
        print(f"Resolving reward type: {reward_type} -> {result_type}")
        if not result_type:
            return None
        item_name = None
        if result_type.startswith("/Lotus/Weapons"):
            if result_type in export_weapons:
                item_name = export_weapons[result_type].get("name")
        elif result_type.startswith("/Lotus/Types"):
            if result_type in export_resources:
                item_name = export_resources[result_type].get("name")
        elif result_type.startswith("/Lotus/Powersuits"):
            if result_type in export_warframes:
                item_name = export_warframes[result_type].get("name")
        print(f"Resolved item name: {item_name}")
        if not item_name:
            return None
        if item_name in dict_en:
            print(f"Translated item name: {item_name} -> {dict_en[item_name]}")
            return dict_en[item_name]
        return item_name
    except Exception as e:
        print(f"Error resolving reward type {reward_type}: {e}")
        return None

def process_projections():
    """Process projections from inventory and save to relics.txt"""
    global relic_rewards_map
    relic_rewards_map = {}  # Reset the map
    try:
        # Check if inventory.json exists
        if not os.path.exists("inventory.json"):
            print("inventory.json not found.")
            return
        
        # Load inventory data
        with open("inventory.json", "r", encoding="utf-8") as f:
            inventory = json.load(f)
        
        # Load ExportRelics data
        if not os.path.exists("Exports\\ExportRelics.json"):
            print("ExportRelics.json not found.")
            return
        
        with open("Exports\\ExportRelics.json", "r", encoding="utf-8") as f:
            export_relics = json.load(f)
        
        # Load ExportRewards data
        if not os.path.exists("Exports\\ExportRewards.json"):
            print("ExportRewards.json not found.")
            return
        
        with open("Exports\\ExportRewards.json", "r", encoding="utf-8") as f:
            export_rewards = json.load(f)
        
        # Load additional export files for reward resolution
        export_recipes = {}
        if os.path.exists("Exports\\ExportRecipes.json"):
            with open("Exports\\ExportRecipes.json", "r", encoding="utf-8") as f:
                export_recipes = json.load(f)
        
        export_weapons = {}
        if os.path.exists("Exports\\ExportWeapons.json"):
            with open("Exports\\ExportWeapons.json", "r", encoding="utf-8") as f:
                export_weapons = json.load(f)
        
        export_resources = {}
        if os.path.exists("Exports\\ExportResources.json"):
            with open("Exports\\ExportResources.json", "r", encoding="utf-8") as f:
                export_resources = json.load(f)
        
        export_warframes = {}
        if os.path.exists("Exports\\ExportWarframes.json"):
            with open("Exports\\ExportWarframes.json", "r", encoding="utf-8") as f:
                export_warframes = json.load(f)
        
        dict_en = {}
        if os.path.exists("Exports\\dict.en.json"):
            with open("Exports\\dict.en.json", "r", encoding="utf-8") as f:
                dict_en = json.load(f)
        # Extract projection items from inventory
        misc_items = inventory.get("MiscItems", [])
        projection_items = []
        print("Searching for projection items in inventory...")
        for item in misc_items:
            item_type = item.get("ItemType", "")
            if item_type.startswith("/Lotus/Types/Game/Projections/"):
                item_count = item.get("ItemCount", 0)
                projection_items.append({
                    "itemType": item_type,
                    "itemCount": item_count
                })
                # print(f"Found projection item: {item_type} x{item_count}")
        
        # Search for each projection item in ExportRelics.json
        relic_info = []
        
        for proj_item in projection_items:
            item_type = proj_item["itemType"]
            item_count = proj_item["itemCount"]
            
            # Search in ExportRelics for matching itemType (ExportRelics is a dict, not a list)
            if item_type in export_relics:
                relic = export_relics[item_type]
                era = relic.get("era", "Unknown")
                category = relic.get("category", "Unknown")
                rewardManifest = relic.get("rewardManifest", "Unknown")
                
                # Get rewards from ExportRewards using rewardManifest
                reward_types = []
                if rewardManifest in export_rewards:
                    reward_tables = export_rewards[rewardManifest]
                    for reward_table in reward_tables:
                        for reward_item in reward_table:
                            reward_type = reward_item.get("type", "Unknown")
                            reward_types.append(reward_type)
                            
                            # Resolve reward type to item name and add to map
                            item_name = resolve_reward_type(reward_type, export_recipes, export_weapons, export_resources, export_warframes, dict_en)
                            if item_name:
                                if item_name not in relic_rewards_map:
                                    relic_rewards_map[item_name] = 0
                                relic_rewards_map[item_name] += item_count

                relic_info.append({
                    "itemType": item_type,
                    "itemCount": item_count,
                    "era": era,
                    "category": category,
                    "rewards": reward_types
                })
                print(f"Found relic match: {item_type} - Era: {era}, Category: {category}, Rewards: {len(reward_types)}")
            else:
                print(f"No match found for: {item_type}")
        
        # Write to relics.txt
        if relic_info:
            with open("relics.txt", "w", encoding="utf-8") as f:
                for info in relic_info:
                    f.write(f"{info['era']} {info['category']} x{info['itemCount']}\n")
        print("End of the script.")
        
    except Exception as e:
        print(f"Error processing projections: {e}")

def calculate_average(result, stat, days):
    """Calculate average of the last N days for a given stat"""
    if not result or len(result) == 0:
        return 0
    last_entries = result[-days:] if len(result) >= days else result
    values = [entry.get(stat, 0) for entry in last_entries]
    return sum(values) / len(values) if values else 0

def fetch_item_statistics(url_name):
    """Fetch statistics for a single item"""
    try:
        response = requests.get(f"https://api.warframe.market/v1/items/{url_name}/statistics", headers=headers, timeout=10)
        
        while response.status_code == 429:
            time.sleep(1)
            response = requests.get(f"https://api.warframe.market/v1/items/{url_name}/statistics", headers=headers, timeout=10)
        
        if response.status_code != 200:
            error_codes[response.status_code] = error_codes.get(response.status_code, 0) + 1
            return None, None
        
        if not response.content:
            return None, None
        
        data = response.json()
        result = data["payload"]["statistics_closed"]["90days"]
        item_name = prime_items[url_name]
        return item_name, result
    except Exception as e:
        return None, None

def fetch_data_from_api(progress_callback=None):
    """Fetch fresh data from the API"""
    global price_list, prime_items, error_codes
    price_list = {}
    error_codes = {}
    
    # Call the API endpoint for all tradeable items
    response = requests.get("https://api.warframe.market/v2/items")
    data = response.json()

    prime_items = {}
    for item in data["data"]:
        if "tags" in item and "prime" in item.get("tags", []):
            if item.get("ducats") in [100, 65]:
                prime_items[item["slug"]] = item["i18n"]["en"]["name"].removesuffix(" Blueprint")

    total_items = len(prime_items)
    items_fetched = 0
    
    # Use ThreadPoolExecutor to fetch data concurrently
    start_time = time.time()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(fetch_item_statistics, item): item for item in prime_items}
        for future in as_completed(futures):
            item_name, result = future.result()
            if item_name is not None:
                price_list[item_name] = result
            items_fetched += 1
            if progress_callback:
                progress_callback(items_fetched, total_items)
    
    return time.time() - start_time

def build_display_data():
    """Build the enriched data and return formatted text"""
    global enriched_data
    enriched_data = {}
    
    sorted_prices = sorted(price_list.items(), key=lambda x: calculate_average(x[1], stat_type, num_days), reverse=True)
    
    if not sorted_prices:
        return "No data available"
    
    max_name_length = max(len(name) for name, _ in sorted_prices) + 1
    output_lines = []
    
    for name, result in sorted_prices:
        current_price = calculate_average(result, stat_type, num_days)
        
        # Strip text after "Prime" for resurgence matching
        stripped_name = name.split(" Prime")[0] + " Prime" if " Prime" in name else name
        
        # Search resurgence.json for matching items
        found_in_resurgence = None
        resurgence_date = None
        for resurgence_key, resurgence_entry in resurgence_data.items():
            for item in resurgence_entry["items"]:
                item_stripped = item.split(" Prime")[0] + " Prime" if " Prime" in item else item
                if item_stripped == stripped_name:
                    found_in_resurgence = resurgence_key
                    resurgence_date = resurgence_entry["date"]
                    break
            if found_in_resurgence:
                break
        
        # Calculate days ago if match found
        resurgence_info = ""
        resurgence_dict = None
        if found_in_resurgence and resurgence_date:
            resurgence_dt = datetime.strptime(resurgence_date, "%Y-%m-%d").date()
            today = datetime.today().date()
            days_diff = (today - resurgence_dt).days

            years = days_diff // 365
            days = days_diff % 365

            spacing = 3 - len(str(days))

            if years > 0:
                resurgence_info = f"({years}y{' '*spacing} {days}d ago)"
            else:
                resurgence_info = f"(   {' '*spacing}{days_diff}d ago)"
            
            resurgence_dict = {
                "date": resurgence_date,
                "days_ago": days_diff,
                "years": years,
                "days": days
            }
        
        # Add to enriched data dictionary
        enriched_data[name] = {
            "price": current_price,
            "resurgence": resurgence_dict
        }
        
        # Get relic count if available
        relic_count = relic_rewards_map.get(name, 0)
        relic_suffix = f" [R:{relic_count}]" if relic_count > 0 else ""
        
        dots = '.' * (max_name_length - len(name))
        output_line = f"{name} {dots} {current_price:.2f} {resurgence_info}{relic_suffix}"
        output_lines.append(output_line)
    
    return "\n".join(output_lines)

def save_data():
    """Save data to files"""
    statistics_data = {name: price_list[name] for name in price_list}
    with open("data_list.json", "w", encoding="utf-8") as f:
        json.dump(statistics_data, f, indent=2)
    
    with open("data_list.txt", "w", encoding="utf-8") as f:
        for name in sorted(enriched_data.keys(), key=lambda x: enriched_data[x]['price'], reverse=True):
            f.write(f"{name}: {enriched_data[name]['price']:.2f}\n")
    
    with open("price_list.txt", "w", encoding="utf-8") as f:
        for name in sorted(enriched_data.keys(), key=lambda x: enriched_data[x]['price'], reverse=True):
            f.write(f"{name}: {enriched_data[name]['price']:.2f}\n")

def update_status(status_msg):
    """Update the status text and refresh the display"""
    global status_text
    status_text = status_msg
    refresh_display()

def refresh_display():
    """Refresh the display with current data"""
    global status_text
    search_term = search_entry.get().lower()
    text_display.configure(state="normal")
    text_display.delete("0.0", "end")
    
    display_text = build_display_data()
    
    # Filter lines based on search term
    if search_term:
        lines = display_text.split("\n")
        filtered_lines = [line for line in lines if search_term in line.lower()]
        display_text = "\n".join(filtered_lines)
    
    # Add status at the bottom with a blank line separator
    if display_text:
        text_display.insert("0.0", display_text + "\n\n" + status_text)
    else:
        text_display.insert("0.0", status_text)
    text_display.configure(state="disabled")

def update_data_thread():
    """Fetch data in a background thread"""
    try:
        update_status("Updating data...")
        update_button.configure(state="disabled")
        root.update()
        
        def update_button_progress(current, total):
            update_button.configure(text=f"{current}/{total}")
            root.update()
        
        elapsed_time = fetch_data_from_api(progress_callback=update_button_progress)
        
        update_status(f"Data updated successfully in {elapsed_time:.2f}s | {len(price_list)} items")
        update_button.configure(text="Data up to date")
        save_data()
    except Exception as e:
        update_status(f"Error: {str(e)}")
        messagebox.showerror("Error", f"Failed to update data: {str(e)}")
        update_button.configure(text="Update Data")
    finally:
        update_button.configure(state="normal")

def on_update_button_click():
    """Handle update button click"""
    thread = threading.Thread(target=update_data_thread, daemon=True)
    thread.start()

# Initialize GUI
load_settings()
load_resurgence()

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

root = ctk.CTk()
root.title("Relic Data Tool")
root.geometry("900x600")

# Header frame with buttons
header_frame = ctk.CTkFrame(root, fg_color="black")
header_frame.pack(fill="x", padx=10, pady=10)

# Search bar
search_entry = ctk.CTkEntry(header_frame, placeholder_text="Search items...", width=200)
search_entry.pack(side="left", padx=5)
search_entry.bind("<KeyRelease>", lambda e: refresh_display())

# Days button
def on_days_click(selected_days):
    global num_days, stat_type
    num_days = selected_days
    settings["days"] = num_days
    with open("settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    refresh_display()
    days_menu.set(f"{num_days} Days")

days_menu = ctk.CTkOptionMenu(header_frame, values=["30 Days", "14 Days", "7 Days", "3 Days", "1 Day"],
                              command=lambda x: on_days_click(int(x.split()[0])),
                              fg_color="#343638", dropdown_fg_color="#343638", dropdown_text_color="#DCE4EE",
                              button_color="#343638", button_hover_color="#4D5155", text_color="#DCE4EE", width=100)
days_menu.pack(side="left", padx=5)
days_menu.set(f"{num_days} Days")

# Stat type mapping
stat_type_map = {"Median": "median", "Weighted Average": "wa_price", "Moving Average": "moving_avg"}

# Stat type button
def on_stat_click(selected_stat):
    global stat_type
    stat_type = stat_type_map.get(selected_stat, selected_stat)
    settings["stat"] = stat_type
    with open("settings.json", "w", encoding="utf-8") as f:
        json.dump(settings, f, indent=2)
    refresh_display()
    stat_menu.set(selected_stat)

stat_menu = ctk.CTkOptionMenu(header_frame, values=["Median", "Weighted Average", "Moving Average"], command=on_stat_click,
                              fg_color="#343638", dropdown_fg_color="#343638", dropdown_text_color="#DCE4EE",
                              button_color="#343638", button_hover_color="#4D5155", text_color="#DCE4EE", width=100)
stat_menu.pack(side="left", padx=5)
# Set initial value using reverse mapping
reverse_stat_map = {v: k for k, v in stat_type_map.items()}
stat_menu.set(reverse_stat_map.get(stat_type, "Median"))

update_button = ctk.CTkButton(header_frame, text="Update Data", command=on_update_button_click)
update_button.pack(side="right", padx=5)

# Scrollable text display
frame = ctk.CTkFrame(root, fg_color="black")
frame.pack(fill="both", expand=True, padx=10, pady=10)

text_display = ctk.CTkTextbox(frame, font=("Consolas", 16), text_color="#16c60c", fg_color="black")
text_display.pack(fill="both", expand=True)

# Load initial data
def load_initial_data():
    """Load initial data on startup"""
    global price_list
    try:
        # Attempt to decrypt lastData.dat if path is configured
        lastdata_path = settings.get("lastDataPath")
        if lastdata_path:
            lastdata_file = os.path.expandvars(lastdata_path)
            if os.path.exists(lastdata_file):
                decrypt_last_data(lastdata_file, "inventory.json")
        
        # Process projections from inventory
        process_projections()
        
        if os.path.exists("data_list.json"):
            with open("data_list.json", "r", encoding="utf-8") as f:
                price_list = json.load(f)
            
            # Check last modification time
            file_mtime = os.path.getmtime("data_list.json")
            current_time = time.time()
            days_since_update = (current_time - file_mtime) / (24 * 3600)
            
            if days_since_update > 1:
                days_ago = int(days_since_update)
                update_button.configure(text=f"Last Updated: {days_ago} day{'s' if days_ago != 1 else ''} ago")
                update_status(f"Loaded {len(price_list)} items from cache. Data is {days_ago} day{'s' if days_ago != 1 else ''} old. Click 'Update Data' to refresh.")
            else:
                update_button.configure(text="Data up to date")
                update_status(f"Loaded {len(price_list)} items from cache. Click 'Update Data' to refresh.")
        else:
            update_button.configure(text="Update Data")
            update_status("No cached data found. Click 'Update Data' to fetch from API.")
    except Exception as e:
        update_status(f"Error loading data: {str(e)}")

root.after(100, load_initial_data)

root.mainloop()