import requests
import re

class TrelloClient:
    def __init__(self, api_key, token):
        self.api_key = api_key
        self.token = token
        self.base_url = "https://api.trello.com/1"

    def fetch_board_data(self, board_input):
        """
        Fetch all lists and cards for a given board.
        Accepts Board ID or full URL.
        """
        board_id = board_input
        
        # Extract ID if URL is provided
        # Trello URLs: https://trello.com/b/BOARD_ID/board-name
        if "trello.com/b/" in board_input:
            match = re.search(r'trello\.com/b/([a-zA-Z0-9]+)', board_input)
            if match:
                board_id = match.group(1)
        
        # First ensure we resolve the board ID if it's a short ID
        try:
            board_url = f"{self.base_url}/boards/{board_id}"
            query = {'key': self.api_key, 'token': self.token}
            board_resp = requests.get(board_url, params=query)
            board_resp.raise_for_status()
            real_board_id = board_resp.json()['id']
        except Exception as e:
            return {"error": f"Invalid Board ID or credentials: {str(e)}"}

        # Now fetch lists with cards
        url = f"{self.base_url}/boards/{real_board_id}/lists"
        query = {
            'key': self.api_key,
            'token': self.token,
            'cards': 'all',
            'card_fields': 'name,desc,due,labels,idMembers'
        }
        
        try:
            response = requests.get(url, params=query)
            response.raise_for_status()
            lists_data = response.json()
            
            # Format for LLM consumption
            formatted_data = {}
            for list_item in lists_data:
                list_name = list_item['name']
                cards = []
                for card in list_item['cards']:
                    card_info = f"- {card['name']}"
                    if card.get('desc'):
                        card_info += f": {card['desc']}"
                    if card.get('due'):
                        card_info += f" (Due: {card['due'][:10]})"
                    cards.append(card_info)
                
                formatted_data[list_name] = cards
                
            return formatted_data
            
        except Exception as e:
            return {"error": str(e)}
