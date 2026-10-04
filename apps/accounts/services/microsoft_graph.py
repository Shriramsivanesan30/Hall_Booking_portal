"""
Microsoft Graph Profile Retrieval Service.

Encapsulates calling the Microsoft Graph /v1.0/me endpoint using a verified
OAuth 2.0 access token to retrieve and normalize user profile details.
"""
import logging
from typing import Any, Dict, Optional
import requests

logger = logging.getLogger(__name__)


class MicrosoftGraphError(Exception):
    """Raised when Microsoft Graph API requests fail or return non-200 responses."""
    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


class MicrosoftGraphService:
    """
    Isolated service for querying Microsoft Graph user profile data.
    """

    GRAPH_ME_ENDPOINT = 'https://graph.microsoft.com/v1.0/me'
    DEFAULT_SELECT_FIELDS = [
        'id',
        'displayName',
        'mail',
        'userPrincipalName',
        'department',
        'givenName',
        'surname',
        'jobTitle',
    ]
    DEFAULT_TIMEOUT = 10  # seconds

    def __init__(
        self,
        endpoint: Optional[str] = None,
        timeout: int = DEFAULT_TIMEOUT,
        select_fields: Optional[list] = None,
    ):
        self.endpoint = endpoint or self.GRAPH_ME_ENDPOINT
        self.timeout = timeout
        self.select_fields = select_fields or self.DEFAULT_SELECT_FIELDS

    def get_user_profile(self, access_token: str) -> Dict[str, Any]:
        """
        Fetch the authenticated user's profile from Microsoft Graph /v1.0/me.

        Args:
            access_token: Bearer token obtained from MicrosoftAuthService.

        Returns:
            Normalized dictionary containing:
                microsoft_user_id (str)
                display_name (str)
                email (str)
                user_principal_name (str)
                department (str or None)
                given_name (str)
                surname (str)
                job_title (str)

        Raises:
            MicrosoftGraphError: If token is missing, request fails, or returns error status.
        """
        if not access_token or not isinstance(access_token, str) or not access_token.strip():
            raise MicrosoftGraphError("A valid Microsoft access token must be provided.")

        headers = {
            'Authorization': f'Bearer {access_token.strip()}',
            'Accept': 'application/json',
        }
        params = {
            '$select': ','.join(self.select_fields)
        }

        try:
            response = requests.get(
                self.endpoint,
                headers=headers,
                params=params,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            logger.error("Microsoft Graph profile request timed out after %ds.", self.timeout)
            raise MicrosoftGraphError("Microsoft Graph request timed out. Please try again.") from None
        except requests.exceptions.RequestException as e:
            logger.error("Microsoft Graph connection error: %s", type(e).__name__)
            raise MicrosoftGraphError("Could not connect to Microsoft Graph service.") from None

        if response.status_code != 200:
            logger.warning("Microsoft Graph profile request failed with HTTP %d", response.status_code)
            if response.status_code == 401:
                raise MicrosoftGraphError("Unauthorized: Microsoft access token is invalid or expired.", status_code=401)
            elif response.status_code == 403:
                raise MicrosoftGraphError("Forbidden: Insufficient permissions to access Microsoft Graph profile.", status_code=403)
            elif response.status_code == 404:
                raise MicrosoftGraphError("User profile not found in Microsoft Graph.", status_code=404)
            elif response.status_code == 429:
                raise MicrosoftGraphError("Rate limit exceeded on Microsoft Graph.", status_code=429)
            elif response.status_code >= 500:
                raise MicrosoftGraphError("Microsoft Graph service encountered an internal server error.", status_code=response.status_code)
            else:
                raise MicrosoftGraphError(f"Microsoft Graph request failed with status {response.status_code}.", status_code=response.status_code)

        try:
            data = response.json()
        except Exception:
            logger.error("Failed to parse JSON response from Microsoft Graph")
            raise MicrosoftGraphError("Invalid JSON received from Microsoft Graph.") from None

        if not isinstance(data, dict):
            raise MicrosoftGraphError("Unexpected response structure from Microsoft Graph.")

        return self.normalize_profile(data)

    @staticmethod
    def normalize_profile(data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize Microsoft Graph raw JSON into a predictable Python dictionary.

        Follows strict email fallback (mail -> userPrincipalName) and department
        null-safety (none inferred or guessed).
        """
        user_principal_name = str(data.get('userPrincipalName') or '').strip().lower()

        # Email resolution: use 'mail' if present; fallback to 'userPrincipalName'
        raw_mail = data.get('mail')
        if raw_mail and isinstance(raw_mail, str) and raw_mail.strip():
            email = raw_mail.strip().lower()
        else:
            email = user_principal_name

        # Department resolution: MUST come from Graph if available; otherwise None.
        raw_dept = data.get('department')
        if raw_dept and isinstance(raw_dept, str) and raw_dept.strip():
            department = raw_dept.strip()
        else:
            department = None

        return {
            'microsoft_user_id': str(data.get('id') or '').strip(),
            'display_name': str(data.get('displayName') or '').strip(),
            'email': email,
            'user_principal_name': user_principal_name,
            'department': department,
            'given_name': str(data.get('givenName') or '').strip(),
            'surname': str(data.get('surname') or '').strip(),
            'job_title': str(data.get('jobTitle') or '').strip(),
        }
