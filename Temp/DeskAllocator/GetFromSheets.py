"""
GetFromSheets.py
----------------
Fetches desk allocation data from Google Sheets.

Returns structured data that can be formatted into Slack messages.
"""

from typing import List, Dict, Any
from utils.config import logger


def fetch_sheet_data(service, spreadsheet_id: str, sheet_name: str) -> List[List[Any]]:
    """
    Fetch all data from the specified Google Sheet.

    Args:
        service: Google Sheets API service object
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: The name of the sheet/tab to read

    Returns:
        List of rows, where each row is a list of cell values
        Returns empty list on failure
    """
    try:
        # Fetch all data from the sheet
        range_name = f"{sheet_name}!A:Z"  # Adjust range as needed
        
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        
        values = result.get('values', [])
        
        if not values:
            logger.warning(f"No data found in sheet '{sheet_name}'")
            return []
        
        logger.info(f"Fetched {len(values)} rows from '{sheet_name}'")
        return values
        
    except Exception as e:
        logger.error(f"Failed to fetch sheet data: {e}")
        return []


def parse_desk_allocations(raw_data: List[List[Any]]) -> List[Dict[str, str]]:
    """
    Parse raw sheet data into structured desk allocation records.

    Expected sheet format (first row = headers):
        Name | Desk | Date | Notes
        
    Args:
        raw_data: Raw data from Google Sheets (list of rows)
        
    Returns:
        List of dictionaries with keys: name, desk, date, notes
        Returns empty list if parsing fails or no valid data
    """
    if not raw_data or len(raw_data) < 2:
        logger.warning("Sheet has no data rows (only headers or empty)")
        return []
    
    try:
        headers = [str(h).strip().lower() for h in raw_data[0]]
        allocations = []
        
        for i, row in enumerate(raw_data[1:], start=2):  # Skip header row
            # Skip empty rows
            if not row or all(not cell for cell in row):
                continue
            
            # Pad row with empty strings if shorter than headers
            row = row + [''] * (len(headers) - len(row))
            
            # Create a dict mapping header names to values
            row_dict = {headers[j]: str(row[j]).strip() for j in range(len(headers))}
            
            # Extract expected fields (adjust based on your sheet structure)
            allocation = {
                'name': row_dict.get('name', ''),
                'desk': row_dict.get('desk', ''),
                'date': row_dict.get('date', ''),
                'notes': row_dict.get('notes', ''),
            }
            
            # Only include rows with at least a name
            if allocation['name']:
                allocations.append(allocation)
            else:
                logger.debug(f"Skipping row {i}: no name found")
        
        logger.info(f"Parsed {len(allocations)} desk allocations")
        return allocations
        
    except Exception as e:
        logger.error(f"Failed to parse desk allocations: {e}")
        return []


def get_desk_allocations(service, spreadsheet_id: str, sheet_name: str) -> List[Dict[str, str]]:
    """
    Convenience function to fetch and parse desk allocations in one call.

    Args:
        service: Google Sheets API service object
        spreadsheet_id: The ID of the spreadsheet
        sheet_name: The name of the sheet/tab to read

    Returns:
        List of parsed allocation dictionaries
    """
    raw_data = fetch_sheet_data(service, spreadsheet_id, sheet_name)
    if not raw_data:
        return []
    
    return parse_desk_allocations(raw_data)