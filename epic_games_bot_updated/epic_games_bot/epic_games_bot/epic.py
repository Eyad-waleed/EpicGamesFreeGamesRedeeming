"""
Epic Games API client module.
Handles authentication, free games discovery, and claiming.
"""

import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger(__name__)

class EpicGamesClient:
    """Client for interacting with Epic Games Store API."""
    
    # Epic Games API endpoints
    BASE_URL = "https://www.epicgames.com"
    LOGIN_URL = "https://www.epicgames.com/id/api/login"
    REDIRECT_URL = "https://www.epicgames.com/id/api/redirect"
    OAUTH_URL = "https://www.epicgames.com/id/api/oauth"
    STORE_URL = "https://store-content.ak.epicgames.com"
    GRAPHQL_URL = "https://graphql.epicgames.com/graphql"
    FREE_GAMES_URL = f"{STORE_URL}/api/content/assets/v2/freegames"
    
    # Client credentials
    CLIENT_ID = "875a3b57d3a640a6b7f9b4e883463ab4"  # Epic Games Web Store client ID
    
    def __init__(self, data_dir: str = "./data"):
        """Initialize Epic Games client.
        
        Args:
            data_dir: Directory to store session and claimed games data
        """
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Accept": "application/json, text/plain, */*",
            "Content-Type": "application/json",
            "Referer": "https://www.epicgames.com/store/",
            "Origin": "https://www.epicgames.com"
        })
        
        # Create data directory if it doesn't exist
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Path to store session data
        self.session_file = os.path.join(self.data_dir, "session.json")
        # Path to store claimed games data
        self.claimed_games_file = os.path.join(self.data_dir, "claimed_games.json")
        
        # Load existing session if available
        self.access_token = None
        self.refresh_token = None
        self.account_id = None
        self.expires_at = 0
        self._load_session()
        
        # Load claimed games
        self.claimed_games = self._load_claimed_games()
    
    def _load_session(self) -> None:
        """Load session data from file if it exists."""
        try:
            if os.path.exists(self.session_file):
                with open(self.session_file, 'r') as f:
                    session_data = json.load(f)
                    self.access_token = session_data.get('access_token')
                    self.refresh_token = session_data.get('refresh_token')
                    self.account_id = session_data.get('account_id')
                    self.expires_at = session_data.get('expires_at', 0)
                    
                    # Update session headers with token
                    if self.access_token:
                        self.session.headers.update({
                            "Authorization": f"Bearer {self.access_token}"
                        })
                    
                    logger.info("Loaded existing session")
        except Exception as e:
            logger.error(f"Failed to load session: {e}")
    
    def _save_session(self) -> None:
        """Save session data to file."""
        try:
            session_data = {
                'access_token': self.access_token,
                'refresh_token': self.refresh_token,
                'account_id': self.account_id,
                'expires_at': self.expires_at
            }
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f)
            logger.info("Saved session data")
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def _load_claimed_games(self) -> List[str]:
        """Load list of claimed games from file."""
        try:
            if os.path.exists(self.claimed_games_file):
                with open(self.claimed_games_file, 'r') as f:
                    return json.load(f)
            return []
        except Exception as e:
            logger.error(f"Failed to load claimed games: {e}")
            return []
    
    def _save_claimed_games(self) -> None:
        """Save list of claimed games to file."""
        try:
            with open(self.claimed_games_file, 'w') as f:
                json.dump(self.claimed_games, f)
            logger.info(f"Saved claimed games list ({len(self.claimed_games)} games)")
        except Exception as e:
            logger.error(f"Failed to save claimed games: {e}")
    
    def _is_token_expired(self) -> bool:
        """Check if the access token is expired."""
        # Add a 5-minute buffer to ensure we refresh before expiration
        return time.time() >= (self.expires_at - 300)
    
    def _refresh_access_token(self) -> bool:
        """Refresh the access token using the refresh token."""
        if not self.refresh_token:
            logger.error("No refresh token available")
            return False
        
        try:
            data = {
                "grant_type": "refresh_token",
                "refresh_token": self.refresh_token,
                "client_id": self.CLIENT_ID
            }
            
            response = self.session.post(
                f"{self.OAUTH_URL}/token",
                json=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data.get('access_token')
                self.refresh_token = token_data.get('refresh_token')
                self.expires_at = time.time() + token_data.get('expires_in', 28800)  # Default 8 hours
                
                # Update session headers
                self.session.headers.update({
                    "Authorization": f"Bearer {self.access_token}"
                })
                
                self._save_session()
                logger.info("Successfully refreshed access token")
                return True
            else:
                logger.error(f"Failed to refresh token: {response.status_code} - {response.text}")
                return False
        except Exception as e:
            logger.error(f"Error refreshing token: {e}")
            return False
    
    def login(self, username: str, password: str) -> Tuple[bool, Optional[str]]:
        """Log in to Epic Games account.
        
        Args:
            username: Epic Games account email/username
            password: Epic Games account password
            
        Returns:
            Tuple of (success, 2fa_method)
            If 2FA is required, 2fa_method will be set to the method (email, authenticator)
        """
        try:
            # Step 1: Initial login request
            login_data = {
                "email": username,
                "password": password,
                "rememberMe": True,
                "captcha": None
            }
            
            response = self.session.post(
                self.LOGIN_URL,
                json=login_data
            )
            
            if response.status_code == 200:
                login_response = response.json()
                
                # Check if 2FA is required
                if login_response.get('twoFactorRequired', False):
                    logger.info(f"2FA required. Method: {login_response.get('method')}")
                    return False, login_response.get('method')
                
                # If no 2FA, proceed with redirect
                redirect_response = self.session.get(self.REDIRECT_URL)
                if redirect_response.status_code == 200:
                    redirect_data = redirect_response.json()
                    code = redirect_data.get('redirectUrl', '').split('code=')[1].split('&')[0]
                    
                    # Exchange code for tokens
                    token_data = {
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": self.CLIENT_ID
                    }
                    
                    token_response = self.session.post(
                        f"{self.OAUTH_URL}/token",
                        json=token_data
                    )
                    
                    if token_response.status_code == 200:
                        token_info = token_response.json()
                        self.access_token = token_info.get('access_token')
                        self.refresh_token = token_info.get('refresh_token')
                        self.account_id = token_info.get('account_id')
                        self.expires_at = time.time() + token_info.get('expires_in', 28800)  # Default 8 hours
                        
                        # Update session headers
                        self.session.headers.update({
                            "Authorization": f"Bearer {self.access_token}"
                        })
                        
                        self._save_session()
                        logger.info(f"Successfully logged in as {username}")
                        return True, None
                    else:
                        logger.error(f"Failed to get tokens: {token_response.status_code} - {token_response.text}")
            else:
                logger.error(f"Login failed: {response.status_code} - {response.text}")
            
            return False, None
        except Exception as e:
            logger.error(f"Login error: {e}")
            return False, None
    
    def complete_2fa(self, code: str) -> bool:
        """Complete 2FA authentication.
        
        Args:
            code: 2FA code from email or authenticator app
            
        Returns:
            bool: True if 2FA was successful
        """
        try:
            # Submit 2FA code
            data = {
                "code": code,
                "method": "authenticator",  # This works for both email and authenticator
                "rememberDevice": True
            }
            
            response = self.session.post(
                f"{self.LOGIN_URL}/mfa",
                json=data
            )
            
            if response.status_code == 200:
                # Follow redirect to get authorization code
                redirect_response = self.session.get(self.REDIRECT_URL)
                if redirect_response.status_code == 200:
                    redirect_data = redirect_response.json()
                    code = redirect_data.get('redirectUrl', '').split('code=')[1].split('&')[0]
                    
                    # Exchange code for tokens
                    token_data = {
                        "grant_type": "authorization_code",
                        "code": code,
                        "client_id": self.CLIENT_ID
                    }
                    
                    token_response = self.session.post(
                        f"{self.OAUTH_URL}/token",
                        json=token_data
                    )
                    
                    if token_response.status_code == 200:
                        token_info = token_response.json()
                        self.access_token = token_info.get('access_token')
                        self.refresh_token = token_info.get('refresh_token')
                        self.account_id = token_info.get('account_id')
                        self.expires_at = time.time() + token_info.get('expires_in', 28800)  # Default 8 hours
                        
                        # Update session headers
                        self.session.headers.update({
                            "Authorization": f"Bearer {self.access_token}"
                        })
                        
                        self._save_session()
                        logger.info("2FA completed successfully")
                        return True
                    else:
                        logger.error(f"Failed to get tokens after 2FA: {token_response.status_code} - {token_response.text}")
                else:
                    logger.error(f"Failed to get redirect after 2FA: {redirect_response.status_code} - {redirect_response.text}")
            else:
                logger.error(f"2FA verification failed: {response.status_code} - {response.text}")
            
            return False
        except Exception as e:
            logger.error(f"2FA error: {e}")
            return False
    
    def ensure_authenticated(self) -> bool:
        """Ensure the client is authenticated, refreshing token if needed.
        
        Returns:
            bool: True if authenticated
        """
        if not self.access_token:
            logger.error("No access token available. Login required.")
            return False
        
        if self._is_token_expired():
            logger.info("Access token expired. Refreshing...")
            return self._refresh_access_token()
        
        return True
    
    def get_free_games(self) -> List[Dict[str, Any]]:
        """Get list of current free games from Epic Games Store.
        
        Returns:
            List of free game data dictionaries
        """
        if not self.ensure_authenticated():
            logger.error("Authentication required to get free games")
            return []
        
        try:
            # Get free games from Epic Games Store API
            params = {
                "locale": "en-US",
                "country": "US",
                "allowCountries": "US"
            }
            
            response = self.session.get(self.FREE_GAMES_URL, params=params)
            
            if response.status_code == 200:
                data = response.json()
                free_games = []
                
                # Extract free games from the response
                for item in data.get('data', {}).get('Catalog', {}).get('searchStore', {}).get('elements', []):
                    # Check if the game is free and not already claimed
                    if item.get('price', {}).get('totalPrice', {}).get('discountPrice', 0) == 0:
                        game_id = item.get('id')
                        title = item.get('title', 'Unknown Game')
                        
                        # Skip games that are already claimed
                        if game_id in self.claimed_games:
                            logger.info(f"Game '{title}' already claimed, skipping")
                            continue
                        
                        free_games.append({
                            'id': game_id,
                            'title': title,
                            'namespace': item.get('namespace'),
                            'description': item.get('description'),
                            'url': f"https://www.epicgames.com/store/en-US/p/{item.get('urlSlug')}"
                        })
                
                logger.info(f"Found {len(free_games)} new free games")
                return free_games
            else:
                logger.error(f"Failed to get free games: {response.status_code} - {response.text}")
                return []
        except Exception as e:
            logger.error(f"Error getting free games: {e}")
            return []
    
    def claim_game(self, game: Dict[str, Any]) -> bool:
        """Claim a free game.
        
        Args:
            game: Game data dictionary from get_free_games()
            
        Returns:
            bool: True if game was successfully claimed
        """
        if not self.ensure_authenticated():
            logger.error("Authentication required to claim games")
            return False
        
        game_id = game.get('id')
        namespace = game.get('namespace')
        title = game.get('title')
        
        if not all([game_id, namespace, title]):
            logger.error(f"Missing required game information: {game}")
            return False
        
        try:
            # GraphQL mutation to purchase (claim) the game
            query = """
            mutation purchaseOrderMutation($orderPurchaseParams: OrderPurchaseParams!) {
                purchaseOrder(orderPurchaseParams: $orderPurchaseParams) {
                    orderResponse {
                        orderResponseCode
                        orderNumber
                        orderComplete
                        orderError
                    }
                }
            }
            """
            
            variables = {
                "orderPurchaseParams": {
                    "productId": game_id,
                    "quantity": 1,
                    "namespace": namespace,
                    "offerId": game_id,
                    "currency": "USD",
                    "lineOffers": [
                        {
                            "offerId": game_id,
                            "quantity": 1
                        }
                    ]
                }
            }
            
            payload = {
                "query": query,
                "variables": variables
            }
            
            response = self.session.post(
                self.GRAPHQL_URL,
                json=payload
            )
            
            if response.status_code == 200:
                result = response.json()
                purchase_data = result.get('data', {}).get('purchaseOrder', {}).get('orderResponse', {})
                
                if purchase_data.get('orderComplete', False):
                    # Add to claimed games list
                    self.claimed_games.append(game_id)
                    self._save_claimed_games()
                    logger.info(f"Successfully claimed game: {title}")
                    return True
                else:
                    error = purchase_data.get('orderError')
                    logger.error(f"Failed to claim game '{title}': {error}")
            else:
                logger.error(f"Failed to claim game '{title}': {response.status_code} - {response.text}")
            
            return False
        except Exception as e:
            logger.error(f"Error claiming game '{title}': {e}")
            return False
