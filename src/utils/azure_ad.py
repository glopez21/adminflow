"""
Azure AD / Microsoft Graph API Integration Module.

This module provides integration with Microsoft Azure Active Directory via
the Microsoft Graph API. It enables user and group management operations
in Azure AD, as well as hybrid synchronization between on-premises AD
and Azure AD environments.

Classes:
    AzureADConfig: Configuration dataclass for Azure AD connection
    GraphAPIError: Custom exception for Graph API errors
    AzureADManager: Main class for Azure AD operations
    HybridADSync: Synchronization manager for hybrid AD environments

Features:
    - OAuth2 client credentials authentication
    - User CRUD operations via Microsoft Graph API
    - Group membership management
    - Device management (list, disable)
    - Application and service principal listing
    - Hybrid on-prem AD to Azure AD synchronization
    - Group comparison between on-prem and Azure AD

Usage:
    from src.utils.azure_ad import AzureADManager, AzureADConfig

    # Create manager from environment variables
    manager = create_azure_manager_from_config()

    # Or create directly
    config = AzureADConfig(
        tenant_id="your-tenant-id",
        client_id="your-client-id",
        client_secret="your-client-secret"
    )
    manager = AzureADManager(config)

    # List users
    users = manager.list_users()

    # Synchronize on-prem users to Azure AD
    sync = HybridADSync(manager)
    results = sync.sync_users(onprem_users)

Requirements:
    - requests library for HTTP calls
    - Azure AD app registration with Graph API permissions

Environment Variables:
    AZURE_TENANT_ID: Azure AD tenant ID
    AZURE_CLIENT_ID: Application client ID
    AZURE_CLIENT_SECRET: Application client secret
"""

import logging
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AzureADConfig:
    """
    Configuration dataclass for Azure AD connection.

    Stores the credentials and settings required to connect to
    Microsoft Graph API for Azure AD operations.

    Attributes:
        tenant_id: Azure AD tenant ID (directory ID)
        client_id: Application (client) ID from app registration
        client_secret: Client secret from app registration
        redirect_uri: Redirect URI for OAuth flow (default: localhost)
        scope: List of Graph API permission scopes

    Example:
        config = AzureADConfig(
            tenant_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            client_id="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            client_secret="your-client-secret"
        )
    """

    tenant_id: str
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost"
    scope: list[str] | None = None

    def __post_init__(self):
        """Set default Graph API scopes if none provided."""
        if self.scope is None:
            self.scope = [
                "https://graph.microsoft.com/.default",
                "User.Read",
                "Group.Read.All",
                "Directory.Read.All",
            ]


class GraphAPIError(Exception):
    """
    Custom exception for Microsoft Graph API errors.

    Raised when Graph API calls fail due to authentication,
    authorization, or other API errors.
    """

    pass


class AzureADManager:
    """
    Manage Azure AD operations via Microsoft Graph API.

    This class provides a comprehensive interface for managing Azure AD
    resources including users, groups, devices, applications, and service
    principals through the Microsoft Graph API v1.0 endpoint.

    Attributes:
        config: AzureADConfig with connection credentials
        access_token: Cached OAuth2 access token
        base_url: Microsoft Graph API base URL

    Example:
        config = AzureADConfig(tenant_id="...", client_id="...", client_secret="...")
        manager = AzureADManager(config)
        manager.get_token()
        users = manager.list_users()
    """

    def __init__(self, config: AzureADConfig):
        """
        Initialize Azure AD manager with configuration.

        Args:
            config: AzureADConfig instance with tenant and app credentials
        """
        self.config = config
        self.access_token: str | None = None
        self.base_url = "https://graph.microsoft.com/v1.0"

    def get_token(self) -> str:
        """
        Obtain OAuth2 access token from Azure AD.

        Uses the client credentials flow to obtain an access token
        for Microsoft Graph API access. The token is cached for
        subsequent API calls.

        Returns:
            str: Access token string for Graph API authorization

        Raises:
            GraphAPIError: If token request fails

        Note:
            Uses client_credentials grant type which requires
            application permissions in Azure AD app registration.
        """
        try:
            import requests

            token_url = f"https://login.microsoftonline.com/{self.config.tenant_id}/oauth2/v2.0/token"

            data = {
                "client_id": self.config.client_id,
                "client_secret": self.config.client_secret,
                "scope": " ".join(self.config.scope or []),
                "grant_type": "client_credentials",
            }

            response = requests.post(token_url, data=data, timeout=30)

            if response.status_code == 200:
                token_data = response.json()
                self.access_token = token_data["access_token"]
                return self.access_token
            raise GraphAPIError(f"Failed to get token: {response.text}")

        except ImportError:
            raise GraphAPIError("requests library required") from None

    def _make_request(self, method: str, endpoint: str, data: dict | None = None) -> dict:
        """
        Make an authenticated request to Microsoft Graph API.

        Handles authentication, request construction, and response
        parsing for all Graph API calls.

        Args:
            method: HTTP method (GET, POST, PATCH, DELETE)
            endpoint: Graph API endpoint path (e.g., "/users")
            data: Optional request body for POST/PATCH operations

        Returns:
            dict: Parsed JSON response from the API

        Raises:
            GraphAPIError: If request fails or returns error status

        Note:
            Automatically obtains access token if not already cached.
        """
        if not self.access_token:
            self.get_token()

        import requests

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        url = f"{self.base_url}{endpoint}"

        if method == "GET":
            response = requests.get(url, headers=headers, timeout=30)
        elif method == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        elif method == "PATCH":
            response = requests.patch(url, headers=headers, json=data, timeout=30)
        elif method == "DELETE":
            response = requests.delete(url, headers=headers, timeout=30)
        else:
            raise GraphAPIError(f"Unsupported method: {method}")

        if response.status_code >= 400:
            raise GraphAPIError(
                f"API error: {response.status_code} - {response.text}"
            )

        return response.json()

    def get_user(self, user_id: str) -> dict:
        """
        Get user by ID or user principal name.

        Retrieves a single user's profile from Azure AD.

        Args:
            user_id: User object ID or user principal name (UPN)

        Returns:
            dict: User profile data

        Example:
            user = manager.get_user("john@domain.com")
        """
        return self._make_request("GET", f"/users/{user_id}")

    def list_users(self, filter: str | None = None, top: int = 100) -> list[dict]:
        """
        List users in Azure AD.

        Retrieves a paginated list of users, optionally filtered
        by OData filter expressions.

        Args:
            filter: OData filter expression (e.g., "startsWith(displayName,'John')")
            top: Maximum number of users to return (default: 100)

        Returns:
            list: List of user dictionaries

        Example:
            users = manager.list_users(filter="department eq 'Engineering'")
        """
        endpoint = f"/users?$top={top}"
        if filter:
            endpoint += f"&$filter={filter}"

        result = self._make_request("GET", endpoint)
        return result.get("value", [])

    def create_user(self, user_data: dict) -> dict:
        """
        Create new Azure AD user.

        Creates a new user in Azure AD with the provided profile data.

        Args:
            user_data: Dictionary with user properties per Graph API schema

        Returns:
            dict: Created user data

        Example:
            result = manager.create_user({
                "accountEnabled": True,
                "displayName": "John Smith",
                "mailNickname": "jsmith",
                "userPrincipalName": "jsmith@domain.com",
                "passwordProfile": {
                    "forceChangePasswordNextSignIn": True,
                    "password": "TempPass123!"
                }
            })
        """
        return self._make_request("POST", "/users", user_data)

    def update_user(self, user_id: str, user_data: dict) -> dict:
        """
        Update Azure AD user properties.

        Updates the specified properties of an existing user.

        Args:
            user_id: User object ID or UPN
            user_data: Dictionary with properties to update

        Returns:
            dict: Updated user data
        """
        return self._make_request("PATCH", f"/users/{user_id}", user_data)

    def delete_user(self, user_id: str) -> bool:
        """
        Delete Azure AD user.

        Permanently deletes a user from Azure AD.

        Args:
            user_id: User object ID or UPN

        Returns:
            bool: True if deletion was successful
        """
        self._make_request("DELETE", f"/users/{user_id}")
        return True

    def reset_password(self, user_id: str, new_password: str) -> bool:
        """
        Reset user password in Azure AD.

        Sets a new password for the specified user. The user will be
        required to change their password on next sign-in.

        Args:
            user_id: User object ID or UPN
            new_password: New password to set

        Returns:
            bool: True if password reset was successful
        """
        data = {
            "passwordProfile": {
                "forceChangePasswordNextSignIn": True,
                "password": new_password,
            }
        }
        self._make_request("PATCH", f"/users/{user_id}", data)
        return True

    def list_groups(self, filter: str | None = None) -> list[dict]:
        """
        List Azure AD groups.

        Retrieves a list of groups, optionally filtered.

        Args:
            filter: OData filter expression (e.g., "displayName eq 'IT-Team'")

        Returns:
            list: List of group dictionaries
        """
        endpoint = "/groups"
        if filter:
            endpoint += f"?$filter={filter}"

        result = self._make_request("GET", endpoint)
        return result.get("value", [])

    def get_group_members(self, group_id: str) -> list[dict]:
        """
        Get all members of a group.

        Retrieves all users and groups that are direct members
        of the specified group.

        Args:
            group_id: Group object ID

        Returns:
            list: List of member dictionaries
        """
        result = self._make_request("GET", f"/groups/{group_id}/members")
        return result.get("value", [])

    def add_group_member(self, group_id: str, user_id: str) -> bool:
        """
        Add a member to a group.

        Adds a user or group as a member of the specified group.

        Args:
            group_id: Target group object ID
            user_id: User or group object ID to add

        Returns:
            bool: True if addition was successful
        """
        self._make_request(
            "POST",
            f"/groups/{group_id}/members",
            {"@odata.id": f"https://graph.microsoft.com/v1.0/users/{user_id}"},
        )
        return True

    def remove_group_member(self, group_id: str, user_id: str) -> bool:
        """
        Remove a member from a group.

        Removes a user or group from the specified group's membership.

        Args:
            group_id: Group object ID
            user_id: Member object ID to remove

        Returns:
            bool: True if removal was successful
        """
        self._make_request("DELETE", f"/groups/{group_id}/members/{user_id}")
        return True

    def list_devices(self, filter: str | None = None) -> list[dict]:
        """
        List registered devices in Azure AD.

        Retrieves all devices registered in the directory,
        optionally filtered by OData expressions.

        Args:
            filter: OData filter expression

        Returns:
            list: List of device dictionaries
        """
        endpoint = "/devices"
        if filter:
            endpoint += f"?$filter={filter}"

        result = self._make_request("GET", endpoint)
        return result.get("value", [])

    def get_device(self, device_id: str) -> dict:
        """
        Get device details by ID.

        Retrieves detailed information about a specific device.

        Args:
            device_id: Device object ID

        Returns:
            dict: Device data dictionary
        """
        return self._make_request("GET", f"/devices/{device_id}")

    def disable_device(self, device_id: str) -> bool:
        """
        Disable a device in Azure AD.

        Sets the device's accountEnabled property to False,
        preventing it from authenticating.

        Args:
            device_id: Device object ID

        Returns:
            bool: True if device was successfully disabled
        """
        self._make_request("PATCH", f"/devices/{device_id}", {"accountEnabled": False})
        return True

    def list_applications(self) -> list[dict]:
        """
        List enterprise applications in Azure AD.

        Retrieves all application registrations in the directory.

        Returns:
            list: List of application dictionaries
        """
        result = self._make_request("GET", "/applications")
        return result.get("value", [])

    def get_service_principals(self) -> list[dict]:
        """
        List service principals in Azure AD.

        Retrieves all service principals which represent
        enterprise applications in the directory.

        Returns:
            list: List of service principal dictionaries
        """
        result = self._make_request("GET", "/servicePrincipals")
        return result.get("value", [])


class HybridADSync:
    """
    Synchronization between on-premises AD and Azure AD.

    Provides methods for synchronizing users and comparing groups
    between an on-premises Active Directory and Azure AD. This is
    useful for hybrid environments where both directories coexist.

    Attributes:
        azure: AzureADManager instance for Azure AD operations

    Example:
        azure_mgr = AzureADManager(config)
        sync = HybridADSync(azure_mgr)
        results = sync.sync_users(onprem_users)
    """

    def __init__(self, azure_manager: AzureADManager):
        """
        Initialize hybrid sync with Azure AD manager.

        Args:
            azure_manager: AzureADManager instance for Azure operations
        """
        self.azure = azure_manager

    def sync_users(self, onprem_users: list[dict]) -> dict:
        """
        Synchronize users from on-prem AD to Azure AD.

        Compares on-premises users with Azure AD users by UPN.
        Creates new users in Azure AD if they don't exist, and
        updates existing users if they're already present.

        Args:
            onprem_users: List of on-prem AD user dictionaries

        Returns:
            dict: Sync results with created/updated counts and errors

        Expected onprem_users format:
            [{"userPrincipalName": "jsmith@domain.com",
              "displayName": "John Smith", ...}, ...]
        """
        results: dict[str, Any] = {"created": 0, "updated": 0, "errors": []}

        azure_users = self.azure.list_users()
        azure_user_map = {u.get("userPrincipalName"): u for u in azure_users}

        for user in onprem_users:
            try:
                upn = user.get("userPrincipalName")

                if upn in azure_user_map:
                    azure_id = azure_user_map[upn].get("id")
                    self.azure.update_user(
                        str(azure_id),
                        {
                            "displayName": user.get("displayName"),
                            "jobTitle": user.get("title"),
                            "department": user.get("department"),
                        },
                    )
                    results["updated"] += 1
                else:
                    self.azure.create_user(
                        {
                            "accountEnabled": True,
                            "displayName": user.get("displayName"),
                            "mailNickname": user.get("sAMAccountName"),
                            "userPrincipalName": user.get("userPrincipalName"),
                            "passwordProfile": {
                                "forceChangePasswordNextSignIn": True,
                                "password": user.get("password", "ChangeMe123!"),
                            },
                        }
                    )
                    results["created"] += 1

            except Exception as e:
                results["errors"].append(
                    {"user": user.get("sAMAccountName"), "error": str(e)}
                )

        return results

    def compare_groups(self, onprem_groups: list[str]) -> dict:
        """
        Compare on-prem groups with Azure AD groups.

        Identifies groups that exist in both directories, groups
        only in on-prem AD, and groups only in Azure AD.

        Args:
            onprem_groups: List of on-prem group names

        Returns:
            dict: Comparison results with matching, onprem-only, azure-only groups

        Example Response:
            {
                "matching": ["IT-Team", "Engineering"],
                "only_onprem": ["Legacy-Group"],
                "only_azure": ["Cloud-Only-Group"]
            }
        """
        azure_groups = self.azure.list_groups()
        azure_group_names = {g.get("displayName"): g for g in azure_groups}

        comparison: dict[str, list[str]] = {"matching": [], "only_onprem": [], "only_azure": []}

        for group in onprem_groups:
            if group in azure_group_names:
                comparison["matching"].append(group)
            else:
                comparison["only_onprem"].append(group)

        for group_name in azure_group_names:
            if group_name is not None and group_name not in onprem_groups:
                comparison["only_azure"].append(group_name)

        return comparison


def create_azure_manager_from_config() -> AzureADManager | None:
    """
    Create AzureADManager from environment variables.

    Reads Azure AD credentials from environment variables and
    creates an AzureADManager instance. Returns None if required
    credentials are not configured.

    Environment Variables:
        AZURE_TENANT_ID: Azure AD tenant ID
        AZURE_CLIENT_ID: Application client ID
        AZURE_CLIENT_SECRET: Application client secret

    Returns:
        AzureADManager if credentials are configured, None otherwise

    Example:
        # Set environment variables first
        # export AZURE_TENANT_ID="your-tenant-id"
        # export AZURE_CLIENT_ID="your-client-id"
        # export AZURE_CLIENT_SECRET="your-client-secret"

        manager = create_azure_manager_from_config()
        if manager:
            users = manager.list_users()
    """
    import os

    tenant_id = os.environ.get("AZURE_TENANT_ID")
    client_id = os.environ.get("AZURE_CLIENT_ID")
    client_secret = os.environ.get("AZURE_CLIENT_SECRET")

    if not all([tenant_id, client_id, client_secret]):
        logger.warning("Azure AD credentials not configured")
        return None

    if tenant_id is None or client_id is None or client_secret is None:
        return None
    config = AzureADConfig(tenant_id=tenant_id, client_id=client_id, client_secret=client_secret)

    return AzureADManager(config)
