import requests
import os
from django.conf import settings

def upload_to_google_drive(file_obj, folder_path):
    """
    Relays a file to Google Apps Script Web App.
    """
    gas_url = os.getenv('GAS_WEB_APP_URL')
    if not gas_url or 'placeholder' in gas_url:
        return None, None

    try:
        files = {'file': (file_obj.name, file_obj.read())}
        data = {
            'folder_path': folder_path,
            'action': 'upload'
        }
        response = requests.post(gas_url, files=files, data=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result.get('fileId'), result.get('fileUrl')
    except Exception as e:
        print(f"Error uploading to Drive: {e}")
    
    return None, None

def sync_to_google_spreadsheet(data):
    """
    Sends transaction data to Google Sheets via GAS.
    """
    gas_url = os.getenv('GAS_WEB_APP_URL')
    if not gas_url or 'placeholder' in gas_url:
        return False

    try:
        payload = {
            'action': 'sync_sheet',
            'data': data
        }
        response = requests.post(gas_url, json=payload, timeout=10)
        return response.status_code == 200
    except Exception as e:
        print(f"Error syncing to Sheet: {e}")
        return False
