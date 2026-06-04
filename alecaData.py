import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def decrypt_last_data(lastdata_path=None, output_path=None):
    # Key and IV bytes to decrypt lastData.dat
    key = bytes([76, 69, 79, 45, 65, 76, 69, 67, 9, 69, 79, 45, 65, 76, 69, 67])
    iv = bytes([49, 50, 70, 71, 66, 51, 54, 45, 76, 69, 51, 45, 113, 61, 57, 0])

    # Default paths
    if lastdata_path is None:
        lastdata_path = 'lastData.dat'
    if output_path is None:
        output_path = 'inventory.json'

    try:
        # 1. Read the encrypted file as binary
        with open(lastdata_path, 'rb') as f:
            ciphertext = f.read()
        
        # 2. Setup the AES CBC cipher
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        # 3. Decrypt the data
        decrypted_padded = cipher.decrypt(ciphertext)
        
        # 4. Remove the PKCS7 padding
        raw_json_bytes = unpad(decrypted_padded, AES.block_size)
        
        # 5. Decode the bytes to a UTF-8 string and parse into JSON object
        inventory_data = json.loads(raw_json_bytes.decode('utf-8'))
        
        # 6. Extract the actual inventory data from the InventoryJson field if it exists
        if isinstance(inventory_data, dict) and "InventoryJson" in inventory_data:
            inventory_data = json.loads(inventory_data["InventoryJson"])
        
        # 7. Save back to a beautifully formatted JSON file
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(inventory_data, f, indent=4)
            
        print("Success! Decrypted lastData.dat and generated a clean inventory.json.")
        return True

    except FileNotFoundError:
        print(f"Error: lastData.dat file not found at {lastdata_path}.")
        return False
    except ValueError as e:
        print(f"Decryption failed (likely bad padding or corrupted data): {e}")
        return False
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return False

if __name__ == "__main__":
    decrypt_last_data()