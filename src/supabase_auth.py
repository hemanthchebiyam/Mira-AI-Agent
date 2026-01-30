import os
import requests


def verify_supabase_token(access_token: str):
    """Verify Supabase access token and return user info dict or None."""
    # Try VITE_SUPABASE_URL first (for frontend), then SUPABASE_URL
    supabase_url = os.getenv("SUPABASE_URL") or os.getenv("VITE_SUPABASE_URL")
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    if not supabase_url or not service_role_key:
        # Supabase auth is optional - return None instead of raising error
        return None

    url = f"{supabase_url}/auth/v1/user"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "apikey": service_role_key,
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        if resp.status_code != 200:
            return None
        return resp.json()
    except Exception:
        # Network errors or other issues - return None gracefully
        return None
