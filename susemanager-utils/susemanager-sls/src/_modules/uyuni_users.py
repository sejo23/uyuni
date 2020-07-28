# coding: utf-8
from typing import Any, Dict, List, Optional, Union, Tuple
import ssl
import xmlrpc.client  # type: ignore
import logging

import os
import salt.config
from salt.utils.minions import CkMinions
import datetime
import pdb

log = logging.getLogger(__name__)

__pillar__: Dict[str, Any] = {}
__context__: Dict[str, Any] = {}
__virtualname__: str = "uyuni"


class UyuniUsersException(Exception):
    """
    Uyuni users Exception
    """


class UyuniChannelsException(Exception):
    """
    Uyuni channels Exception
    """


class RPCClient:
    """
    RPC Client
    """

    def __init__(self, user: str = None, password: str = None, url: str = "https://localhost/rpc/api"):
        """
        XML-RPC client interface.

        :param user: username for the XML-RPC API endpoints
        :param password: password credentials for the XML-RPC API endpoints
        :param url: URL of the remote host
        """

        ctx: ssl.SSLContext = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        self.conn = xmlrpc.client.ServerProxy(url, context=ctx, use_datetime=True, use_builtin_types=True)
        if user is None or password is None:
            # if user or password not set, fallback to default user defined on pillar data
            if "xmlrpc" in (__pillar__ or {}).get("uyuni", {}):
                rpc_conf = (__pillar__ or {})["uyuni"]["xmlrpc"] or {}
                self._user: str = rpc_conf.get("user", "")
                self._password: str = rpc_conf.get("password", "")
            else:
                raise UyuniUsersException("Unable to find Pillar configuration for Uyuni XML-RPC API")
        else:
            self._user: str = user
            self._password: str = password

        self.token: Optional[str] = None

    def get_user(self):
        return self._user

    def get_token(self, refresh: bool = False) -> Optional[str]:
        """
        Authenticate.
        If a authentication token is present on __context__ it will be returned
        Otherwise get an ew authentication token from xml rpc.
        If refresh parameter where set to True, it will get a new token from the API

        :param refresh: force token to the refreshed, cached values
        :return: authentication token
        """
        if self.token is None or refresh:
            try:
                auth_token_key = "uyuni.auth_token_" + self._user
                if (not auth_token_key in __context__) or refresh:
                    __context__[auth_token_key] = self.conn.auth.login(self._user, self._password)
            except Exception as exc:
                log.error("Unable to login to the Uyuni server: %s", exc)
                raise exc
            self.token = __context__[auth_token_key]
        return self.token

    def __call__(self, method: str, *args, **kwargs) -> Any:
        self.get_token()
        if self.token is not None:
            try:
                log.debug("Calling RPC method %s", method)
                return getattr(self.conn, method)(*((self.token,) + args))
            except Exception as exc:
                if exc.faultCode != 2950:
                    log.error("Unable to call RPC function: %s", str(exc))
                    raise exc
                """
                Authentication error when using Token, it can have expired.
                Call a second time with a new session token
                """
                log.warning("Fall back to the second try due to %s", str(exc))
                try:
                    return getattr(self.conn, method)(*((self.get_token(refresh=True),) + args))
                except Exception as exc:
                    log.error("Unable to call RPC function: %s", str(exc))
                    raise exc

        raise UyuniUsersException("XML-RPC backend authentication error.")


class UyuniRemoteObject:
    """
    RPC client
    """

    def __init__(self, user: str = None, password: str = None):
        self.client: RPCClient = RPCClient(user=user, password=password)

    @staticmethod
    def _convert_datetime_str(response: Dict[str, Any]) -> Dict[str, Any]:
        """
        modify any key-value pair where value is a datetime object to a string.

        :param response: response dictionary to be processed
        :return: new dictionary with datetime objects converted to sting
        """
        if response:
            return dict(
                [
                    (k, "{0}".format(v)) if isinstance(v, datetime.datetime) else (k, v)
                    for k, v in response.items()
                ]
            )
        return None

    @staticmethod
    def _convert_datetime_list(response: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        modify any list of key-value pair where value is a datetime object to a string.
        :param response: list of dictionaries to be processed
        :return: List of new dictionaries with datetime objects converted to sting
        """
        if response:
            return [UyuniRemoteObject._convert_datetime_str(value) for value in response]
        return None


class UyuniUser(UyuniRemoteObject):
    """
    CRUD operation on users.
    """

    def get_details(self, uid: str) -> Dict[str, Any]:
        """
        Get existing user data from the Uyuni.

        :param: uid: user name to lookup
        :return: Dictionary with user details
        """
        log.debug("get user details: %s", uid)
        return self.client("user.getDetails", uid)

    def list_users(self) -> List[Dict[str, Any]]:
        """
        Return all Uyuni users.
        Uyuni XML-RPC listUsers return all users that are visible for the authenticated user.
        This could be a sub-set of all existing users.

        :return: all users visible to the authenticated user
        """
        log.debug("list existing users")
        return self.client("user.listUsers")

    def create(self, uid: str, password: str, email: str, first_name: str = "", last_name: str = "") -> bool:
        """
        Create user in Uyuni.
        User will be created in the same organization as the authenticated user.

        :param uid: desired login name
        :param password: desired password for the user
        :param email: valid email address
        :param first_name: First name
        :param last_name: Second name

        :return: True on success, raise exception otherwise
        """
        log.debug("Adding user to Uyuni: %s", uid)
        return bool(self.client("user.create", uid, password, first_name, last_name, email))

    def set_details(self, uid: str, password: str, email: str, first_name: str = "", last_name: str = "") -> bool:
        """
        Update user information on Uyuni.

        :param uid: login name
        :param password: desired password for the user
        :param email: valid email address
        :param first_name: First name
        :param last_name: Second name

        :return: True on success, raise exception otherwise
        """
        log.debug("Updating user to Uyuni: %s", uid)
        return bool(self.client("user.setDetails", uid, {
            "password": password,
            "first_name": first_name,
            "last_name": last_name,
            "email": email
        }))

    def delete(self, uid: str) -> bool:
        """
        Remove user from the Uyuni.

        :param uid: UID of the user
        :return: boolean, True if user has been deleted successfully.
        """
        log.debug("delete user: %s", uid)
        return bool(self.client("user.delete", uid))

    def list_roles(self, uid: str) -> List[str]:
        """
        Get existing user data from the Uyuni.

        :param: uid: user name to use on lookup
        :return: list of user roles
        """
        log.debug("get user roles: %s", uid)
        return self.client("user.listRoles", uid)

    def add_role(self, uid: str, role: str) -> bool:
        """
        Add role to user

        :param uid: UID of the user
        :param role: one of uyuni user roles

        :return: boolean, True if role has been added successfully.
        """
        log.debug("add role '%s' to user %s", role, uid)
        return bool(self.client("user.addRole", uid, role))

    def remove_role(self, uid: str, role: str) -> bool:
        """
        Remove user from the Uyuni org.

        :param uid: UID of the user
        :param role: one of uyuni user roles

        :return: boolean, True if role has been removed successfully.
        """
        log.debug("remove role '%s' to user %s", role, uid)
        return bool(self.client("user.removeRole", uid, role))

    def list_assigned_system_groups(self, uid: str) -> List[Dict[str, Union[int, str]]]:
        """
        Returns the system groups that a user can administer.

        :param uid: UID of the user
        :return: List of system groups that a user can administer
        """
        log.debug("list assigned system groups for user %s", uid)
        return self.client("user.listAssignedSystemGroups", uid)

    def add_assigned_system_groups(self, uid: str, server_group_names: List[str], set_default: bool = False) -> int:
        """
        Add system groups to user's list of assigned system groups.

        :param uid: user id to look for
        :param server_group_names: systems groups to add to list of assigned system groups
        :param set_default: Should system groups also be added to user's list of default system groups.
        :return: 1 on success, exception thrown otherwise.
        """
        log.debug("add assigned system groups to user %s: %s", uid, server_group_names)
        return self.client("user.addAssignedSystemGroups", uid, server_group_names, set_default)

    def remove_assigned_system_groups(self, uid: str, server_group_names: List[str], set_default: bool = False) -> int:
        """
        Remove system groups from a user's list of assigned system groups

        :param uid: user id to look for
        :param server_group_names: systems groups to remove from list of assigned system groups
        :param set_default: Should system groups also be added to user's list of default system groups.
        :return: 1 on success, exception thrown otherwise.
        """
        log.debug("remove assign groups from user %s: %s", uid, server_group_names)
        return self.client("user.removeAssignedSystemGroups", uid, server_group_names, set_default)


class UyuniChannel(UyuniRemoteObject):
    def list_manageable_channels(self) -> List[Dict[str, Union[int, str]]]:
        """
        List all software channels that the user is entitled to manage.
        :return: list of manageable channels
        """
        return self.client("channel.listManageableChannels")

    def list_my_channels(self) -> List[Dict[str, Union[int, str]]]:
        """
        List all software channels that the user is entitled to manage.
        :return: list of manageable channels
        """
        return self.client("channel.listMyChannels")


class UyuniChannelSoftware(UyuniRemoteObject):
    def set_user_manageable(self, channel_label: str, uid: str, access: bool) -> int:
        """
        Set the manageable flag for a given channel and user.
        If access is set to 'true', this method will give the user manage permissions to the channel.
        Otherwise, that privilege is revoked.

        :param channel_label: label of the channel
        :param uid: user login id
        :param access: Flag which if user should have management access to channel or not
        :return: 1 on success, exception thrown otherwise.
        """
        log.debug("change managing access to %s for user %s in channel %s", access, uid, channel_label)
        return self.client("channel.software.setUserManageable", channel_label, uid, access)

    def set_user_subscribable(self, channel_label: str, uid: str, access: bool) -> int:
        """
        Set the subscribable flag for a given channel and user.
        If value is set to 'true', this method will give the user subscribe permissions to the channel.
        Otherwise, that privilege is revoked.

        :param channel_label: label of the channel
        :param uid: user login id
        :param access: Flag which if user should subscribe a channel or not
        :return: 1 on success, exception thrown otherwise.
        """
        log.debug("change subscription access to %s for user %s in channel %s", access, uid, channel_label)
        return self.client("channel.software.setUserSubscribable", channel_label, uid, access)

    def is_user_manageable(self, channel_label: str, uid: str) -> bool:
        """
        Returns whether the channel may be managed by the given user.

        :param channel_label: label of the channel
        :param uid: user login id
        :return: boolean which indicates if user can manage channel or not
        """
        log.debug("check if user %s can manage channel %s", uid, channel_label)
        return bool(self.client("channel.software.isUserManageable", channel_label, uid))

    def is_user_subscribable(self, channel_label: str, uid: str) -> bool:
        """
        Returns whether the channel may be subscribed to by the given user.

        :param channel_label: label of the channel
        :param uid: user login id
        :return: boolean which indicates if user subscribe the channel or not
        """
        log.debug("check if user %s can subscribe channel %s", uid, channel_label)
        return bool(self.client("channel.software.isUserSubscribable", channel_label, uid))

    def is_globally_subscribable(self, channel_label: str) -> bool:
        """
        Returns whether the channel is globally subscribed on the organization
        :param channel_label: label of the channel
        :return: boolean which indicates if channel is globally subscribe
        """
        log.debug("check if channel globally Subscribable %s", channel_label)
        return bool(self.client("channel.software.isGloballySubscribable", channel_label))


class UyuniOrg(UyuniRemoteObject):
    """
    CRUD operations on orgs
    """

    def list_orgs(self) -> Dict[str, Union[int, str, bool]]:
        """
        List all orgs.
        Admin user must have SUSE Manager Administrator role to perform this action

        :return: list of all existing organizations
        """
        return self.client("org.listOrgs")

    def get_details(self, name: str) -> Dict[str, Union[int, str, bool]]:
        """
        Get org data by name.
        Admin user must have SUSE Manager Administrator role to perform this action

        :param name: organisation name
        :return: organization details
        """
        return self.client("org.getDetails", name)

    def create(self, name: str, org_admin_user: str, org_admin_password: str,
               first_name: str, last_name: str, email: str,
               admin_prefix: str = "Mr.", pam: bool = False) -> Dict[str, Union[str, int, bool]]:
        """
        Create a new Uyuni org.
        Admin user must have SUSE Manager Administrator role to perform this action
        :param name:
        :param org_admin_user:
        :param org_admin_password:
        :param first_name:
        :param last_name:
        :param email:
        :param admin_prefix:
        :param pam:
        :return: tuple of data and error/log message
        """
        return self.client("org.create", name, org_admin_user, org_admin_password, admin_prefix,
                           first_name, last_name, email, pam)

    def delete(self, name: str) -> int:
        """
        Delete Uyuni org.
        Admin user must have SUSE Manager Administrator role to perform this action

        :param name:
        :return: 1 on success, exception thrown otherwise.
        """
        org_id = int(self.get_details(name=name).get("id", -1))
        return self.client("org.delete", org_id)

    def update_name(self, org_id: int, name: str) -> Dict[str, Union[str, int, bool]]:
        """
        Update Uyuni org name.
        Admin user must have SUSE Manager Administrator role to perform this action

        :param org_id: organization internal id
        :param name: new organization name
        :return: organization details
        """
        return self.client("org.updateName", org_id, name)


class UyuniOrgTrust(UyuniRemoteObject):

    def __init__(self, user: str = None, password: str = None):
        UyuniRemoteObject.__init__(self, user, password)
        self._org_manager = UyuniOrg()

    def list_orgs(self) -> List[Dict[str, Union[str, int]]]:
        """
        List all organizations trusted by the authenticated user organization

        :return: List of organization details
        """
        return self.client("org.trusts.listOrgs")

    def list_trusts(self, org_name: str) -> List[Dict[str, Union[str, int, bool]]]:
        """
        List all trusts for the organization
        Admin user must have SUSE Manager Administrator role to perform this action

        :return: list with all organization and if is trusted or not
        """
        org = self._org_manager.get_details(org_name)
        return self.client("org.trusts.listTrusts", org["id"])

    def add_trust_by_name(self, org_name: str, org_trust: str) -> int:
        """
        Set organisation trusted
        Admin user must have SUSE Manager Administrator role to perform this action

        :param org_name: organization name
        :param org_trust: organization to trust
        :return: 1 on success, exception thrown otherwise.
        """
        this_org = self._org_manager.get_details(org_name)
        trust_org = self._org_manager.get_details(org_trust)
        return self.add_trust(this_org["id"], trust_org["id"])

    def add_trust(self, org_id: str, org_trust_id: str) -> int:
        """
        Set organisation trusted.
        Admin user must have SUSE Manager Administrator role to perform this action

        :param org_id: organization id
        :param org_trust_id: organization id to trust
        :return: 1 on success, exception thrown otherwise.
        """
        return self.client("org.trusts.addTrust", org_id, org_trust_id)

    def remove_trust_by_name(self, org_name: str, org_untrust: str) -> int:
        """
        Remove organisation trusted.
        Admin user must have SUSE Manager Administrator role to perform this action

        :param org_name: organization name
        :param org_untrust: organization name to untrust
        :return: 1 on success, exception thrown otherwise.
        """
        this_org = self._org_manager.get_details(org_name)
        trust_org = self._org_manager.get_details(org_untrust)
        return self.remove_trust(this_org["id"], trust_org["id"])

    def remove_trust(self, org_id: str, org_untrust_id: str) -> int:
        """
        Remove organisation trusted.
        Admin user must have SUSE Manager Administrator role to perform this action

        :param org_id: organization id
        :param org_untrust_id: organization id to untrust
        :return: 1 on success, exception thrown otherwise.
        """
        return self.client("org.trusts.removeTrust", org_id, org_untrust_id)


class UyuniSystemgroup(UyuniRemoteObject):
    """
    Provides methods to access and modify system groups.
    """

    def get_details(self, name: str) -> Dict[str, Union[int, str]]:
        """
        Retrieve details of a ServerGroup.

        :param name: Name of the system group.
        :return: data of the system group.
        """
        log.debug("Get details for group: %s", name)
        return self.client("systemgroup.getDetails", name)

    def create(self, name: str, description: str) -> Dict[str, Union[int, str]]:
        """
        Create a new system group.

        :param name: Name of the system group.
        :param description: Description of the system group.
        :return: data of the system group.
        """
        log.debug("Create group: %s", name)
        return self.client("systemgroup.create", name, description)

    def delete(self, name: str) -> int:
        """
        Delete a system group.

        :param name: Name of the system group.
        :return: 1 on success, exception thrown otherwise.
        """
        log.debug("delete group: %s", name)
        return self.client("systemgroup.delete", name)

    def update(self, name: str, description: str) -> Dict[str, Union[int, str]]:
        """
        Update an existing system group.

        :param name: Name of the system group.
        :param description: Description of the system group.
        :return: data of the system group.
        """
        log.debug("update group: %s", name)
        return self.client("systemgroup.update", name, description)

    def list_systems(self, name: str, minimal: bool = True) -> List[Dict[str, Any]]:
        """
        Get information from the system in the group.

        :param name: Group name
        :param minimal: default True. Minimal information or more detailed one about systems
        :return: List of system information
        """
        return self._convert_datetime_list(
            self.client("systemgroup.listSystemsMinimal" if minimal else "systemgroup.listSystems", name))

    def add_remove_systems(self, name: str, add_remove: bool, system_ids: List[int] = []) -> int:
        """
        Add or remove list of systems from the group

        :param name: Group name
        :param add_remove: True to add to the group, False to remove
        :param system_ids: List of system ids to add or remove
        :return: 1 on success, exception thrown otherwise
        """
        return self.client("systemgroup.addOrRemoveSystems", name, system_ids, add_remove)


class UyuniSystems(UyuniRemoteObject):

    def get_minion_id_map(self, refresh: bool = False) -> Dict[str, int]:
        """
        Map between minion ID and system internal ID of all system user have access to.
        Context cache can be used, to avoid multiple call to the server.

        :param refresh: Get new data from server, ignoring values in local context cache
        :return: Map between minion ID and system ID of all system accessible by authenticated user
        """
        minions_token_key = "uyuni.minions_id_map_" + self.client.get_user()
        if (not minions_token_key in __context__) or refresh:
            __context__[minions_token_key] = self.client("system.getMinionIdMap")
        return __context__[minions_token_key]


class UyuniChildMasterIntegration:
    """
    Integration with the Salt Master which is running
    on the same host as this current Minion.
    """
    DEFAULT_MASTER_CONFIG_PATH = "/etc/salt/master"

    class FCkMinions(CkMinions):
        """
        Minion data matcher.
        """

        def _get_key_fingerprint(self, minion_id: str) -> str:
            """
            Get minion key fingerprint.

            :param minion_id:
            :return: fingerprint or an empty string if not found
            """
            keypath = os.path.join(self.opts['pki_dir'], self.acc, minion_id)
            return salt.utils.crypt.pem_finger(path=keypath, sum_type=self.opts["hash_type"])

        def _get_fingerprints(self, minion_ids: List[str]) -> Dict[str, str]:
            """
            Resolve all fingerprints.

            :param minion_ids:
            :return:
            """
            minions = {}
            for mid in minion_ids:
                minions[mid] = self._get_key_fingerprint(minion_id=mid)

            return minions

    def __init__(self):
        self._minions = UyuniChildMasterIntegration.FCkMinions(salt.config.client_config(self._get_master_config()))

    @staticmethod
    def _get_master_config() -> str:
        """
        Return master config.
        :return: path to salt master configuration file
        """
        cfg_path = UyuniChildMasterIntegration.DEFAULT_MASTER_CONFIG_PATH
        for path in __pillar__.get("uyuni", {}).get("masters", {}).get("configs", [cfg_path]):
            if os.path.exists(path):
                cfg_path = path
                break

        return cfg_path

    def list_minions(self, active: bool = False) -> List[str]:
        """
        Return list of currently registered minions.

        :param active: Return only active minions.
        :return: list of minion ids
        """
        return self._minions.connected_ids() if active else self._minions._pki_minions()

    def list_minions_fp(self, active: bool = False) -> Dict[str, str]:
        """
        Return list of currently registered minions, including their key fingerprints.

        :param active: Return only active minions.
        :return: mapping of minion ids to the fingerprints
        """
        return self._minions._get_fingerprints(self.list_minions(active=active))

    def select_minions(self, expr: str, tgt: str = "glob") -> Dict[str, Union[List[str], bool]]:
        """
        Select minion IDs that matches the expression.

        :param expr: expression
        :param tgt: target type, one of the following: glob, grain, grain_pcre, pillar, pillar_pcre,
                    pillar_exact, compound, compound_pillar_exact. Default: glob.

        :return: list of minions
        """
        return self._minions.check_minions(expr=expr, tgt_type=tgt)

    def select_minions_fp(self, expr: str, tgt: str = "glob") -> Dict[str, Union[str, bool]]:
        """
        Select minion IDs that matches the expression.

        :param expr: expression
        :param tgt: target type, one of the following: glob, grain, grain_pcre, pillar, pillar_pcre,
                    pillar_exact, compound, compound_pillar_exact. Default: glob.

        :return: mapping of minion ids to the fingerprints
        """
        selected = self.select_minions(expr=expr, tgt=tgt)
        ret = {
            "minions": self._minions._get_fingerprints(selected["minions"]),
            "missing": self._minions._get_fingerprints(selected["missing"]),
            "ssh_minions": selected.get("ssh_minions", False)
        }

        return ret


def __virtual__():
    """
    Provide Uyuni Users state module.

    :return:
    """

    return __virtualname__


def user_get_details(uid, password=None, org_admin_user=None, org_admin_password=None):
    """
    Get user in Uyuni.
    If user password is provided name and password fields are use to authenticate
    If no user credentials are provided, organization administrator credentials will be used
    If no user credentials neither organization admin credentials are provided, credentials from pillar will be used

    :param uid: user id to look for
    :param password: password for the user
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: The user information
    """
    return UyuniUser(org_admin_user if password is None else uid,
                     org_admin_password if password is None else password).get_details(uid=uid)


def user_list_users(org_admin_user=None, org_admin_password=None):
    """
    Get user in Uyuni.
    If no organization admin credentials are provided, credentials from pillar are used

    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: list of user roles
    """
    return UyuniUser(org_admin_user, org_admin_password).list_users()


def user_create(uid, password, email, first_name, last_name,
                org_admin_user=None, org_admin_password=None):
    """
    Create user in Uyuni.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param password: password for the user
    :param email: user email address
    :param first_name: user first name
    :param last_name: user last name
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user, org_admin_password).create(uid=uid, password=password, email=email,
                                                                first_name=first_name, last_name=last_name)


def user_set_details(uid, password, email, first_name=None, last_name=None,
                     org_admin_user=None, org_admin_password=None):
    """
    Update user in Uyuni.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param password: password for the user
    :param email: user email address
    :param first_name: user first name
    :param last_name: user last name
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user, org_admin_password).set_details(uid=uid, password=password, email=email,
                                                                     first_name=first_name, last_name=last_name)


def user_delete(uid, org_admin_user=None, org_admin_password=None):
    """
    Create user in Uyuni.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user, org_admin_password).delete(uid=uid)


def user_list_roles(uid, password=None, org_admin_user=None, org_admin_password=None):
    """
    Get user roles in Uyuni.
    If user password is provided name and password fields are use to authenticate
    If no user credentials are provided, organization administrator credentials will be used
    If no user credentials neither organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param password: password for the user
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: List of user roles assigned
    """
    return UyuniUser(org_admin_user if password is None else uid,
                     org_admin_password if password is None else password).list_roles(uid=uid)


def user_add_role(uid, role, org_admin_user=None, org_admin_password=None):
    """
    Add role to user in Uyuni.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param role: role to be added to the user
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user, org_admin_password).add_role(uid=uid, role=role)


def user_remove_role(uid, role, org_admin_user=None, org_admin_password=None):
    """
    Remove role to user in Uyuni.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param role: role to be removed from the user
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user, org_admin_password).remove_role(uid=uid, role=role)


def user_list_assigned_system_groups(uid, org_admin_user=None, org_admin_password=None):
    """
    Returns the system groups that a user can administer.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: List of system groups that a user can administer
    """
    return UyuniUser(org_admin_user,
                     org_admin_password).list_assigned_system_groups(uid=uid)


def user_add_assigned_system_groups(uid, server_group_names, set_default=False,
                                    org_admin_user=None, org_admin_password=None):
    """
    Add system groups to user's list of assigned system groups.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param server_group_names: systems groups to add to list of assigned system groups
    :param set_default: Should system groups also be added to user's list of default system groups.
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user,
                     org_admin_password).add_assigned_system_groups(uid=uid,
                                                                    server_group_names=server_group_names,
                                                                    set_default=set_default)


def user_remove_assigned_system_groups(uid, server_group_names, set_default=False,
                                       org_admin_user=None, org_admin_password=None):
    """
    Remove system groups from a user's list of assigned system groups.
    If no organization admin credentials are provided, credentials from pillar are used

    :param uid: user id to look for
    :param server_group_names: systems groups to remove from list of assigned system groups
    :param set_default: Should system groups also be added to user's list of default system groups.
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniUser(org_admin_user,
                     org_admin_password).remove_assigned_system_groups(uid=uid,
                                                                       server_group_names=server_group_names,
                                                                       set_default=set_default)


## channel.software
def channel_list_manageable_channels(uid, password):
    """
    List with all of manageable channels for the authenticated user
    :param uid: user login id
    :param password: user password
    :return: list of manageable channels for the user
    """
    return UyuniChannel(uid, password).list_manageable_channels()


def channel_list_my_channels(uid, password):
    """
    List with all of subscribed channels for the authenticated user
    :param uid: user login id
    :param password: user password
    :return: list of subscribed channels for the user
    """
    return UyuniChannel(uid, password).list_my_channels()


def channel_software_set_user_manageable(channel_label, uid, access,
                                         admin_user=None, admin_password=None):
    """
    Set the manageable flag for a given channel and user.
    If access is set to 'true', this method will give the user manage permissions to the channel.
    Otherwise, that privilege is revoked.

    :param channel_label: label of the channel
    :param uid: user login id
    :param access: Flag which if user should have access to channel or not
    :param admin_user: organization admin username
    :param admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniChannelSoftware(admin_user, admin_password).set_user_manageable(channel_label, uid, access)


def channel_software_set_user_subscribable(channel_label, uid, access,
                                           admin_user=None, admin_password=None):
    """
    Set the subscribable flag for a given channel and user.
    If value is set to 'true', this method will give the user subscribe permissions to the channel.
    Otherwise, that privilege is revoked.

    :param channel_label: label of the channel
    :param uid: user login id
    :param access: Flag which if user should subscribe a channel or not
    :param admin_user: organization admin username
    :param admin_password: organization admin password
    :return: boolean indication success in operation
    """
    return UyuniChannelSoftware(admin_user, admin_password).set_user_subscribable(channel_label, uid, access)


def channel_software_is_user_manageable(channel_label, uid, admin_user=None, admin_password=None):
    """
    Returns whether the channel may be managed by the given user.

    :param channel_label: label of the channel
    :param uid: user login id
    :param admin_user: organization admin username
    :param admin_password: organization admin password
    :return: boolean which indicates if user can manage channel or not
    """
    return UyuniChannelSoftware(admin_user, admin_password).is_user_manageable(channel_label, uid)


def channel_software_is_user_subscribable(channel_label, uid, org_admin_user=None, org_admin_password=None):
    """
    Returns whether the channel may be managed by the given user.

    :param channel_label: label of the channel
    :param uid: user login id
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean which indicates if user subscribe the channel or not
    """
    return UyuniChannelSoftware(org_admin_user, org_admin_password).is_user_subscribable(channel_label, uid)


def channel_software_is_global_subscribable(channel_label, org_admin_user=None, org_admin_password=None):
    """
    Returns whether the channel is globally subscribed on the organization

    :param channel_label: label of the channel
    :param org_admin_user: organization admin username
    :param org_admin_password: organization admin password
    :return: boolean which indicates if channel is globally subscribe
    """
    return UyuniChannelSoftware(org_admin_user, org_admin_password).is_globally_subscribable(channel_label)


def org_list_orgs(admin_user=None, admin_password=None):
    """
    List all existing org.
    Admin user must have SUSE Manager Administrator role to perform this action
    :return: list of all available orgs.
    """
    return UyuniOrg(admin_user, admin_password).list_orgs()


def org_get_details(name, admin_user=None, admin_password=None):
    """
    Get org details
    Admin user must have SUSE Manager Administrator role to perform this action
    :param name:
    :param admin_user:
    :param admin_password:
    :return:
    """
    return UyuniOrg(admin_user, admin_password).get_details(name)


def org_delete(name, admin_user=None, admin_password=None):
    """
    Delete org
    Admin user must have SUSE Manager Administrator role to perform this action
    :param name:
    :param admin_user:
    :param admin_password:
    :return:
    """
    return UyuniOrg(admin_user, admin_password).delete(name)


def org_create(name, org_admin_user, org_admin_password, first_name, last_name, email,
               admin_prefix="Mr.", pam=False, admin_user=None, admin_password=None):
    """
    Create org in Uyuni.
    Admin user must have SUSE Manager Administrator role to perform this action
    :param name: organization name
    :param org_admin_user: organization admin user
    :param org_admin_password: organization admin password
    :param first_name: organization admin first name
    :param last_name: organization admin last name
    :param email: organization admin email
    :param admin_prefix: organization admin prefix
    :param pam:organization admin pam authentication
    :param admin_user: uyuni admin user
    :param admin_password: uyuni admin password
    :return: dictionary with org information
    """
    return UyuniOrg(admin_user, admin_password).create(name=name, org_admin_user=org_admin_user,
                                                       org_admin_password=org_admin_password,
                                                       first_name=first_name, last_name=last_name, email=email,
                                                       admin_prefix=admin_prefix, pam=pam)


def org_update_name(org_id, name, admin_user=None, admin_password=None):
    """
    update Uyuni organization name
    :param org_id:
    :param name:
    :param admin_user:
    :param admin_password:
    :return:
    """
    return UyuniOrg(admin_user, admin_password).update_name(org_id, name)


def org_trust_list_orgs(admin_user=None, admin_password=None):
    """
    List all organanizations trusted by the authenticated user organization
    :param admin_user: authentication user
    :param admin_password: authentication user password
    :return:
    """
    return UyuniOrgTrust(admin_user, admin_password).list_orgs()


def org_trust_list_trusts(org_name, admin_user=None, admin_password=None):
    """
    List all trusts for one organization
    admin_user needs to have SUSE Manager Administrator role to perform this action
    :param org_name: Name of the organization to get the trusts
    :param admin_user: authentication user
    :param admin_password: authentication user password
    :return: list of all organizations with the trust flag value
    """
    return UyuniOrgTrust(admin_user, admin_password).list_trusts(org_name)


def org_trust_add_trust_by_name(org_name, org_trust, admin_user=None, admin_password=None):
    """
    Add an organization to the list of trusted organizations.
    admin_user needs to have SUSE Manager Administrator role to perform this action
    :param org_name: organization name
    :param org_trust: Trust organization name
    :param admin_user: uyuni admin user
    :param admin_password: uyuni admin password
    :return:
    """
    return UyuniOrgTrust(admin_user, admin_password).add_trust_by_name(org_name, org_trust)


def org_trust_add_trust(org_id, org_trust_id, admin_user=None, admin_password=None):
    """
    Add an organization to the list of trusted organizations.
    admin_user needs to have SUSE Manager Administrator role to perform this action
    :param org_id: Organization id
    :param org_trust_id: Trust organization id
    :param admin_user: uyuni admin user
    :param admin_password: uyuni admin password
    :return:
    """
    return UyuniOrgTrust(admin_user, admin_password).add_trust(org_id, org_trust_id)


def org_trust_remove_trust_by_name(org_name, org_untrust, admin_user=None, admin_password=None):
    """
    Remove an organization to the list of trusted organizations.
    admin_user needs to have SUSE Manager Administrator role to perform this action
    :param org_name: organization name
    :param org_untrust: organization name to untrust
    :param admin_user: uyuni admin user
    :param admin_password: uyuni admin password
    :return:
    """
    return UyuniOrgTrust(admin_user, admin_password).remove_trust_by_name(org_name, org_untrust)


def org_trust_remove_trust(org_id, org_untrust_id, admin_user=None, admin_password=None):
    """
    Remove an organization to the list of trusted organizations.
    admin_user needs to have SUSE Manager Administrator role to perform this action
    :param org_id: orgnization id
    :param org_untrust_id: organizaton id to untrust
    :param admin_user: uyuni admin user
    :param admin_password: uyuni admin password
    :return:
    """
    return UyuniOrgTrust(admin_user, admin_password).remove_trust(org_id, org_untrust_id)


"""
Server groups management
"""


def systemgroup_create(name, descr, org_admin_user=None, org_admin_password=None):
    """
    Create system group.

    :param name: Name of the system group.
    :param descr: Description of the system group.
    :param org_admin_user: organization administrator username
    :param org_admin_password: organization administrator password

    :return: server group structure.
    """
    return UyuniSystemgroup(org_admin_user, org_admin_password).create(name=name, description=descr)


def systemgroup_get_details(name, org_admin_user=None, org_admin_password=None):
    """
    Get system group details.

    :param name: Name of the system group.
    :param org_admin_user: organization administrator username
    :param org_admin_password: organization administrator password

    :return: server group structure.
    """
    return UyuniSystemgroup(org_admin_user, org_admin_password).get_details(name=name)


def systemgroup_update(name, descr, org_admin_user=None, org_admin_password=None):
    """
    Update system group.

    :param name: Name of the system group.
    :param descr: Description of the system group.
    :param org_admin_user: organization administrator username
    :param org_admin_password: organization administrator password

    :return: server group structure.
    """
    return UyuniSystemgroup(org_admin_user, org_admin_password).update(name=name, description=descr)


def systemgroup_delete(name, org_admin_user=None, org_admin_password=None):
    """
    Delete system group.

    :param name: Name of the system group.
    :param org_admin_user: organization administrator username
    :param org_admin_password: organization administrator password

    :return: 1 on success, exception thrown otherwise.
    """
    return UyuniSystemgroup(org_admin_user, org_admin_password).delete(name=name)


def systemgroup_list_systems(name, minimal=True, org_admin_user=None, org_admin_password=None):
    """
    Delete system group.

    :param name: Name of the system group.

    :return: List of system information
    """
    return UyuniSystemgroup(org_admin_user, org_admin_password).list_systems(name=name, minimal=minimal)


def systemgroup_add_remove_systems(name, add_remove, system_ids=[],
                                   org_admin_user=None, org_admin_password=None):
    """
    Delete system group.

    :param name: Name of the system group.
    :param add_remove: True to add to the group, False to remove.
    :param system_ids: list of system ids to add/remove from group
    :param org_admin_user: organization administrator username
    :param org_admin_password: organization administrator password

    :return: 1 on success, exception thrown otherwise.
    """
    return UyuniSystemgroup(org_admin_user, org_admin_password).add_remove_systems(name=name, add_remove=add_remove,
                                                                                   system_ids=system_ids)


def master_select_minions(expr=None, tgt="glob", fp=False):
    """
    Return list minions from the configured Salt Master on the same host
    which match the expression on the defined target

    :param expr: expression to filter minions
    :param tgt: target type, one of the following: glob, grain, grain_pcre, pillar, pillar_pcre,
                pillar_exact, compound, compound_pillar_exact. Default: glob.
    :param fp: Include fingerprints

    :return: list of minion IDs
    """
    cmi = UyuniChildMasterIntegration()

    return (cmi.select_minions_fp if fp else cmi.select_minions)(expr=expr, tgt=tgt)


def master_list_minions(active=False):
    """
    Return list of all available minions from the configured
        Salt Master on the same host.

    :param active: Return only active minions.

    :return: list of minion IDs
    """
    cmi = UyuniChildMasterIntegration()

    return cmi.list_minions(active=active)


def systems_get_minion_id_map(username=None, password=None, refresh=False):
    """
    Map between minion ID and system internal ID of all system user have access to

    :param username: username to authenticate
    :param password: password for user
    :param refresh: Get new data from server, ignoring values in local context cache
    :return: Map between minion ID and system ID of all system accessible by authenticated user
    """
    return UyuniSystems(username, password).get_minion_id_map(refresh)