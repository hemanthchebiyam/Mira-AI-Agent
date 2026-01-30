import requests
import re

class TrelloClient:
    def __init__(self, api_key, token):
        self.api_key = api_key
        self.token = token
        self.base_url = "https://api.trello.com/1"

    def _resolve_board_id(self, board_input):
        """Accepts a Trello board ID or URL and returns the canonical board ID"""
        board_id = board_input

        if "trello.com/b/" in board_input:
            match = re.search(r'trello\.com/b/([a-zA-Z0-9]+)', board_input)
            if match:
                board_id = match.group(1)

        board_url = f"{self.base_url}/boards/{board_id}"
        query = {'key': self.api_key, 'token': self.token}
        board_resp = requests.get(board_url, params=query)
        board_resp.raise_for_status()
        return board_resp.json()['id']

    def fetch_board_data(self, board_input):
        """
        Fetch all lists and cards for a given board.
        Accepts Board ID or full URL.
        """
        try:
            real_board_id = self._resolve_board_id(board_input)
        except Exception as e:
            return {"error": f"Invalid Board ID or credentials: {str(e)}"}

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

    def get_lists(self, board_input):
        """Return list metadata for populating UI selectors"""
        try:
            real_board_id = self._resolve_board_id(board_input)
        except Exception as e:
            return {"error": f"Invalid Board ID or credentials: {str(e)}"}

        url = f"{self.base_url}/boards/{real_board_id}/lists"
        query = {'key': self.api_key, 'token': self.token}

        try:
            resp = requests.get(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def create_card(self, list_id, name, desc=None, due=None, label_ids=None, member_ids=None):
        """Create a new card on a list"""
        url = f"{self.base_url}/cards"
        query = {
            'key': self.api_key,
            'token': self.token,
            'idList': list_id,
            'name': name
        }
        if desc:
            query['desc'] = desc
        if due:
            query['due'] = due
        if label_ids:
            query['idLabels'] = ",".join(label_ids)
        if member_ids:
            query['idMembers'] = ",".join(member_ids)

        try:
            resp = requests.post(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def create_board(self, name):
        """Create a new Trello board"""
        url = f"{self.base_url}/boards"
        query = {
            'key': self.api_key,
            'token': self.token,
            'name': name
        }
        try:
            resp = requests.post(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def create_list(self, board_id, name):
        """Create a new list on a Trello board"""
        url = f"{self.base_url}/lists"
        query = {
            'key': self.api_key,
            'token': self.token,
            'idBoard': board_id,
            'name': name
        }
        try:
            resp = requests.post(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def update_card(self, card_id, name=None, desc=None, due=None, list_id=None, label_ids=None, member_ids=None):
        """Update key fields on an existing card"""
        url = f"{self.base_url}/cards/{card_id}"
        query = {
            'key': self.api_key,
            'token': self.token
        }
        if name is not None:
            query['name'] = name
        if desc is not None:
            query['desc'] = desc
        if due is not None:
            query['due'] = due
        if list_id is not None:
            query['idList'] = list_id
        if label_ids is not None:
            query['idLabels'] = ",".join(label_ids)
        if member_ids is not None:
            query['idMembers'] = ",".join(member_ids)

        try:
            resp = requests.put(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def add_comment(self, card_id, text):
        """Add a comment to a card"""
        url = f"{self.base_url}/cards/{card_id}/actions/comments"
        query = {'key': self.api_key, 'token': self.token, 'text': text}
        try:
            resp = requests.post(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def add_checklist_item(self, card_id, checklist_name, item_name, checked=False):
        """Create a checklist on the card (if needed) and add an item"""
        try:
            checklist_url = f"{self.base_url}/checklists"
            checklist_query = {
                'key': self.api_key,
                'token': self.token,
                'idCard': card_id,
                'name': checklist_name
            }
            checklist_resp = requests.post(checklist_url, params=checklist_query)
            checklist_resp.raise_for_status()
            checklist_id = checklist_resp.json()['id']

            item_url = f"{self.base_url}/checklists/{checklist_id}/checkItems"
            item_query = {
                'key': self.api_key,
                'token': self.token,
                'name': item_name,
                'checked': 'true' if checked else 'false'
            }
            item_resp = requests.post(item_url, params=item_query)
            item_resp.raise_for_status()

            return {
                "checklist": checklist_resp.json(),
                "item": item_resp.json()
            }
        except Exception as e:
            return {"error": str(e)}

    def close_card(self, card_id, closed=True):
        """Archive/unarchive a card"""
        url = f"{self.base_url}/cards/{card_id}"
        query = {
            'key': self.api_key,
            'token': self.token,
            'closed': 'true' if closed else 'false'
        }
        try:
            resp = requests.put(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}

    def close_list(self, list_id, closed=True):
        """Archive/unarchive a list"""
        url = f"{self.base_url}/lists/{list_id}"
        query = {
            'key': self.api_key,
            'token': self.token,
            'closed': 'true' if closed else 'false'
        }
        try:
            resp = requests.put(url, params=query)
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"error": str(e)}
