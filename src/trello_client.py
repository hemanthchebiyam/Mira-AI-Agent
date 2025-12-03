import requests

class TrelloClient:
    def __init__(self, api_key, token):
        self.api_key = api_key
        self.token = token
        self.base_url = "https://api.trello.com/1"

    def fetch_board_data(self, board_id):
        """
        Fetch all lists and cards for a given board.
        """
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

