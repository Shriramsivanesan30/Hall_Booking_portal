"""
Microsoft Entra ID / Office 365 Authentication Service.

Encapsulates OAuth 2.0 / OpenID Connect authorization code flow using Microsoft's
official MSAL (Microsoft Authentication Library) for Python.
"""
import logging
import msal
from django.conf import settings

logger = logging.getLogger(__name__)


class MicrosoftConfigError(Exception):
    """Raised when Microsoft OAuth settings are missing or invalid."""
    pass


class MicrosoftAuthError(Exception):
    """Raised when token acquisition or identity validation fails."""
    pass


class MicrosoftAuthService:
    """
    Isolated service handling Microsoft Entra ID confidential client authentication.
    """

    DEFAULT_SCOPES = ['User.Read']

    def __init__(
        self,
        client_id: str = None,
        client_secret: str = None,
        tenant_id: str = None,
        redirect_uri: str = None,
        scopes: list = None,
        validate_authority: bool = True,
    ):
        """
        Initialize the service with settings or explicit arguments.
        Falls back to Django settings if arguments are None.
        """
        self.client_id = (client_id if client_id is not None else getattr(settings, 'MICROSOFT_CLIENT_ID', '')).strip()
        self.client_secret = (client_secret if client_secret is not None else getattr(settings, 'MICROSOFT_CLIENT_SECRET', '')).strip()
        self.tenant_id = (tenant_id if tenant_id is not None else getattr(settings, 'MICROSOFT_TENANT_ID', '')).strip()
        self.redirect_uri = (redirect_uri if redirect_uri is not None else getattr(settings, 'MICROSOFT_REDIRECT_URI', '')).strip()
        self.scopes = scopes or self.DEFAULT_SCOPES
        self.validate_authority = validate_authority

    def validate_configuration(self) -> None:
        """
        Validate that all required configuration settings are present and non-empty.
        Raises MicrosoftConfigError if any required setting is missing.
        """
        missing = []
        if not self.client_id:
            missing.append('MICROSOFT_CLIENT_ID')
        if not self.client_secret:
            missing.append('MICROSOFT_CLIENT_SECRET')
        if not self.tenant_id:
            missing.append('MICROSOFT_TENANT_ID')
        if not self.redirect_uri:
            missing.append('MICROSOFT_REDIRECT_URI')

        if missing:
            msg = f"Microsoft Authentication configuration missing required setting(s): {', '.join(missing)}"
            logger.error(msg)
            raise MicrosoftConfigError(msg)

        # Enforce single-tenant policy: disallow generic multi-tenant endpoints
        if self.tenant_id.lower() in ('common', 'consumers'):
            msg = (
                f"Invalid tenant ID '{self.tenant_id}'. The College Hall Booking Portal requires "
                "a single-tenant configuration (college Entra Directory/Tenant ID or domain)."
            )
            logger.error(msg)
            raise MicrosoftConfigError(msg)

    @property
    def authority(self) -> str:
        """
        Returns the tenant-specific Microsoft Entra authority URL.
        Never defaults to /common or /consumers for college portal security.
        """
        if not self.tenant_id:
            raise MicrosoftConfigError("Cannot determine authority: MICROSOFT_TENANT_ID is empty.")
        return f"https://login.microsoftonline.com/{self.tenant_id}"

    def get_msal_client(self) -> msal.ConfidentialClientApplication:
        """
        Instantiate MSAL's ConfidentialClientApplication for the configured tenant.
        """
        self.validate_configuration()

        return msal.ConfidentialClientApplication(
            client_id=self.client_id,
            client_credential=self.client_secret,
            authority=self.authority,
            validate_authority=self.validate_authority,
        )

    def initiate_auth_flow(self, prompt: str = None) -> dict:
        """
        Initiates the MSAL authorization-code flow.
        Generates a secure state and PKCE verifier.
        Returns a flow dictionary containing 'auth_uri', 'state', 'nonce', etc.
        This dictionary should be stored in the user's Django session (request.session['auth_flow']).
        """
        client = self.get_msal_client()

        flow_params = {
            'scopes': self.scopes,
            'redirect_uri': self.redirect_uri,
        }
        if prompt:
            flow_params['prompt'] = prompt

        flow = client.initiate_auth_code_flow(**flow_params)
        if 'auth_uri' not in flow:
            logger.error("Failed to generate Microsoft authorization URI from MSAL.")
            raise MicrosoftAuthError("Could not generate authorization URL from Microsoft Entra ID.")

        logger.info("Microsoft authorization URL generated successfully.")
        return flow

    def get_authorization_url(self, state: str = None, prompt: str = None) -> str:
        """
        Convenience method to retrieve just the authorization URL string.
        """
        client = self.get_msal_client()
        kwargs = {
            'scopes': self.scopes,
            'redirect_uri': self.redirect_uri,
        }
        if state:
            kwargs['state'] = state
        if prompt:
            kwargs['prompt'] = prompt

        auth_url = client.get_authorization_request_url(**kwargs)
        logger.info("Microsoft authorization request URL built.")
        return auth_url

    def acquire_token_by_auth_flow(self, auth_flow: dict, auth_response: dict) -> dict:
        """
        Exchanges the authorization code for tokens using MSAL's state-validated flow.

        Parameters:
            auth_flow: The flow dictionary saved in request.session['auth_flow'].
            auth_response: The query dictionary from the callback (e.g. request.GET.dict()).

        Returns:
            Dict containing:
                success (bool)
                access_token (str or None)
                id_token_claims (dict)
                error (str or None)
                error_description (str or None)
        """
        if not auth_flow:
            logger.warning("Microsoft auth callback invoked without active auth_flow in session.")
            return {
                'success': False,
                'access_token': None,
                'id_token_claims': {},
                'error': 'invalid_session',
                'error_description': 'Session state expired or missing. Please initiate login again.',
            }

        client = self.get_msal_client()
        result = client.acquire_token_by_auth_code_flow(auth_flow, auth_response)

        if 'error' in result:
            err = result.get('error')
            err_desc = result.get('error_description')
            logger.warning("Microsoft token acquisition failed: error=%s", err)
            return {
                'success': False,
                'access_token': None,
                'id_token_claims': {},
                'error': err,
                'error_description': err_desc,
            }

        logger.info("Microsoft token acquisition succeeded.")
        return {
            'success': True,
            'access_token': result.get('access_token'),
            'id_token_claims': result.get('id_token_claims', {}),
            'error': None,
            'error_description': None,
        }

    def acquire_token_by_code(self, code: str) -> dict:
        """
        Direct authorization code exchange without pre-existing session flow.
        Provided as a fallback method.
        """
        if not code:
            return {
                'success': False,
                'access_token': None,
                'id_token_claims': {},
                'error': 'invalid_code',
                'error_description': 'Authorization code is missing.',
            }

        client = self.get_msal_client()
        result = client.acquire_token_by_authorization_code(
            code=code,
            scopes=self.scopes,
            redirect_uri=self.redirect_uri,
        )

        if 'error' in result:
            err = result.get('error')
            err_desc = result.get('error_description')
            logger.warning("Direct Microsoft code exchange failed: error=%s", err)
            return {
                'success': False,
                'access_token': None,
                'id_token_claims': {},
                'error': err,
                'error_description': err_desc,
            }

        logger.info("Direct Microsoft code exchange succeeded.")
        return {
            'success': True,
            'access_token': result.get('access_token'),
            'id_token_claims': result.get('id_token_claims', {}),
            'error': None,
            'error_description': None,
        }

    def validate_tenant(self, id_token_claims: dict) -> bool:
        """
        Validates that the token's 'tid' claim matches the configured tenant ID.
        Protects against rogue token submission from untrusted tenants.
        """
        if not id_token_claims:
            return False

        token_tid = id_token_claims.get('tid', '')
        if not token_tid:
            logger.warning("id_token_claims is missing 'tid' (tenant id) claim.")
            return False

        # In case the configured tenant was given as a domain name (e.g. mcet.in) or GUID
        # Check against both self.tenant_id and matching tenant GUID
        configured = self.tenant_id.lower().strip()
        actual = token_tid.lower().strip()

        # If configured is GUID, exact match
        if configured == actual:
            return True

        # If configured is a domain name, check verified issuer in claims
        iss = id_token_claims.get('iss', '')
        if actual in iss:
            return True

        logger.warning("Tenant mismatch: token tenant '%s' does not match configured tenant '%s'.", actual, configured)
        return False

    @staticmethod
    def extract_identity_claims(id_token_claims: dict) -> dict:
        """
        Extract normalized identity claims from validated id_token_claims.
        Does not interact with the database.
        """
        if not id_token_claims:
            return {}

        return {
            'oid': id_token_claims.get('oid') or id_token_claims.get('sub') or '',
            'tid': id_token_claims.get('tid') or '',
            'name': id_token_claims.get('name') or '',
            'preferred_username': id_token_claims.get('preferred_username') or '',
            'email': (
                id_token_claims.get('email')
                or id_token_claims.get('preferred_username')
                or id_token_claims.get('upn')
                or ''
            ).lower().strip(),
            'given_name': id_token_claims.get('given_name') or '',
            'family_name': id_token_claims.get('family_name') or '',
        }
