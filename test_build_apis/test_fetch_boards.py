import os
import sys
import json
import requests

# Read the token provided by the environment
import dotenv
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
MONDAY_API_TOKEN = os.getenv("MONDAY_API_TOKEN", "your_token_here")
MONDAY_API_URL = "https://api.monday.com/v2"

headers = {
    "Authorization": MONDAY_API_TOKEN,
    "Content-Type": "application/json",
    "API-Version": "2026-01"
}

def fetch_boards():
    print("Connecting to Monday.com to fetch boards...")
    query = """
    {
        boards(limit: 50) {
            id
            name
            state
            items_count
            owner {
                name
                email
            }
        }
    }
    """
    
    payload = {"query": query}
    
    response = requests.post(MONDAY_API_URL, json=payload, headers=headers)
    
    if response.status_code == 200:
        data = response.json()
        if "errors" in data:
            print("GraphQL Error occurred:")
            print(json.dumps(data["errors"], indent=2))
            return
            
        boards = data.get("data", {}).get("boards", [])
        print(f"\\nSuccessfully fetched {len(boards)} boards.\\n")
        
        for idx, board in enumerate(boards, start=1):
            print(f"Board #{idx}:")
            print(f"  ID:          {board.get('id')}")
            print(f"  Name:        {board.get('name')}")
            print(f"  State:       {board.get('state')}")
            print(f"  Items Count: {board.get('items_count')}")
            
            owner = board.get('owner') or {}
            print(f"  Owner:       {owner.get('name')} ({owner.get('email')})\\n")
            
        print("Raw JSON Response snippet:")
        print(json.dumps(boards, indent=2))
        
    else:
        print(f"HTTP Error {response.status_code}:")
        print(response.text)

if __name__ == "__main__":
    fetch_boards()
