import sys
import os
import pandas as pd

# Add the project root to the path so we can import the backend modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from monday_api_client import MondayAPIClient
from backend.normalizer import normalize_board_data

# The specific board IDs from Monday.com
BOARD_DEAL_FUNNEL = 5027339053
BOARD_WORK_ORDER = 5027339041

def items_to_dataframe(items: list) -> pd.DataFrame:
    """
    Given a list of Monday.com items (where each item contains 'column_values'),
    flatten it into a Pandas DataFrame.
    """
    rows = []
    for item in items:
        # Base row data
        row = {
            "Item ID": item.get("id"),
            "Item Name": item.get("name"),
            "Group": item.get("group", {}).get("title"),
        }
        
        # Extract all column values directly using their 'title' or 'id'
        # Monday API v2 provides text or value. text is usually best for DataFrames.
        for cv in item.get("column_values", []):
            col_name = cv.get("column", {}).get("title", cv.get("id"))
            col_val = cv.get("text", cv.get("value"))
            row[col_name] = col_val
            
        rows.append(row)
        
    return pd.DataFrame(rows)

def fetch_and_print_dataframe(client: MondayAPIClient, board_id: int, name: str):
    print(f"\\n{'='*50}")
    print(f"Fetching '{name}' (Board ID: {board_id})...")
    
    # 1. Live API call fetching all items (handles cursor pagination under the hood)
    # Using the normalizer limits it to a clean representation or we can use raw client
    items = client.get_board_items(board_id, limit=500)
    print(f"Fetched {len(items)} items from Live GraphQL API.")
    
    # 2. Convert to DataFrame
    df = items_to_dataframe(items)
    
    # 3. Print DataFrame info and head
    print(f"\\n--- DataFrame shape: {df.shape} ---")
    print(df.info())
    print("\\n--- Data Preview (first 5 rows) ---")
    print(df.head())
    
    return df

def main():
    print("Initializing Monday API Client...")
    client = MondayAPIClient()
    
    # Fetch DataFrames
    df_deals = fetch_and_print_dataframe(client, BOARD_DEAL_FUNNEL, "Deal Funnel Data")
    df_work_orders = fetch_and_print_dataframe(client, BOARD_WORK_ORDER, "Work Order Tracker Data")

    print(f"\\n{'='*50}")
    print("Success! Both boards are now successfully loaded into live Pandas DataFrames memory.")
    print("You can now apply AI inference, math calculations, or export them to CSV.")
    
if __name__ == "__main__":
    main()
