# coding: utf-8
"""
Unit tests for modules/uyuni_users.py execution module
"""

import sys
sys.path.append("../_modules")
import uyuni_users
from uyuni_users import RPCClient, UyuniUsersException, UyuniRemoteObject, UyuniUser, UyuniOrg
from unittest.mock import patch, MagicMock, mock_open
import pytest


class TestRPCClient:
    """
    Test RPCClient object
    """
    rpc_client = None

    @patch("uyuni_users.ssl", MagicMock())
    @patch("uyuni_users.xmlrpc", MagicMock())
    @patch("uyuni_users.os.makedirs", MagicMock())
    def setup_method(self, method):
        """
        Setup state per test.

        :param method:
        :return:
        """
        self.rpc_client = RPCClient(url="https://somewhere", user="user", password="password")
        self.rpc_client.conn = MagicMock()

    def teardown_method(self, method):
        """
        Tear-down state per test.

        :param method:
        :return:
        """
        self.rpc_client = None

    def test_session_load(self):
        """
        Load session.

        :return:
        """
        with patch.object(uyuni_users, "open", mock_open(read_data=b"disk spinning backwards")) as mo:
            out = self.rpc_client.load_session()
            assert mo.called
            assert mo.call_count == 1
            assert mo.call_args == [('/var/cache/salt/minion/uyuni.rpc.s', 'rb')]
            assert out is not None
            assert out.startswith("disk")

    def test_session_save(self):
        """
        Save session.

        :return:
        """
        # Method "save_session" is called on the auth automatically and is not meant to be directly accessed.
        # For this reason it is shifted away during testing and a Mock is called instead
        self.rpc_client.conn.auth.login = MagicMock(return_value="28000 bps connection")
        self.rpc_client._save_session = self.rpc_client.save_session
        self.rpc_client.save_session = MagicMock()

        with patch.object(uyuni_users, "open", mock_open()) as mo:
            out = self.rpc_client._save_session()
            assert out is True
            assert len(mo.mock_calls) == 4
            assert mo.mock_calls[2][1][0] == b"28000 bps connection"

    def test_get_token(self):
        """
        Get XML-RPC token from the Uyuni.

        :return: string
        """
        self.rpc_client.conn.auth.login = MagicMock(return_value="improperly oriented keyboard")
        self.rpc_client.token = None
        self.rpc_client.save_session = MagicMock()
        self.rpc_client.get_token()

        assert self.rpc_client.save_session.called
        assert self.rpc_client.token is not None
        assert self.rpc_client.token.startswith("improperly")

    def test_get_token_recall(self):
        """
        Get XML-RPC token from the Uyuni, second call should be skipped.

        :return: string
        """
        self.rpc_client.conn.auth.login = MagicMock(return_value="recursive recursion error")
        self.rpc_client.token = "sunspot activity"
        self.rpc_client.save_session = MagicMock()
        self.rpc_client.get_token()

        assert not self.rpc_client.save_session.called
        assert self.rpc_client.token is not None
        assert self.rpc_client.token.startswith("sunspot")

    def test_call_rpc(self):
        """
        Call any XML-RPC method.

        :return:
        """
        self.rpc_client.token = "The Borg"
        out = self.rpc_client("heavymetal.playLoud", self.rpc_client.get_token())
        mo = getattr(self.rpc_client.conn, "heavymetal.playLoud")

        assert out is not None
        assert mo.called
        assert mo.call_args == [("The Borg",)]

    def test_call_rpc_crash_handle(self):
        """
        Handle XML-RPC method crash.

        :return:
        """
        self.rpc_client.token = "The Borg"
        setattr(self.rpc_client.conn, "heavymetal.playLoud",
                MagicMock(side_effect=Exception("Chewing gum on /dev/sd3c")))

        with patch("uyuni_users.log") as logger:
            with pytest.raises(UyuniUsersException):
                out = self.rpc_client("heavymetal.playLoud", self.rpc_client.get_token())
                mo = getattr(self.rpc_client.conn, "heavymetal.playLoud")

                assert out is not None
                assert mo.called
                assert mo.call_args == [("The Borg",)]
            assert logger.error.call_args[0] == ('Unable to call RPC function: %s', 'Chewing gum on /dev/sd3c')


class TestUyuniRemoteObject:
    """
    Test UyuniRemoteObject base class.
    """

    @patch("uyuni_users.RPCClient", MagicMock())
    def test_get_proto_return(self):
        """
        Get protocol return.
        """
        uro = UyuniRemoteObject()
        err = Exception("Suboptimal routing experience")

        assert uro.get_proto_return() == {}
        assert uro.get_proto_return(exc=err) == {"error": str(err)}


class TestUyuniUser:
    """
    Test UyuniUser.
    """
    uyuni_user = None

    @patch("uyuni_users.RPCClient", MagicMock())
    def setup_method(self, method):
        """
        Setup each test.

        :return:
        """
        self.uyuni_user = UyuniUser()
        self.uyuni_user.client = MagicMock()
        self.uyuni_user.client.get_token = MagicMock(return_value="xyz")

    def teardown_method(self, method):
        """
        Remove setup for each test.

        :return:
        """
        self.uyuni_user = None

    def test_create(self):
        """
        Test user create.

        :return:
        """
        with patch("uyuni_users.log", MagicMock()) as logger:
            out = self.uyuni_user.create(uid="Borg", password="futile-resistance", email="here@you.go")

        assert out
        assert logger.debug.called
        assert logger.debug.call_count == 2
        assert logger.debug.call_args_list[0][0] == ('Adding user to Uyuni',)
        assert logger.debug.call_args_list[1][0] == ('User has been created',)
        assert self.uyuni_user.client.called
        assert self.uyuni_user.client.call_args_list[0][0] == ('user.create', 'xyz', 'Borg', 'futile-resistance',
                                                               '', '', 'here@you.go')

    def test_create_no_email(self):
        """
        Test user create attempt without email specified

        :return:
        """
        with patch("uyuni_users.log", MagicMock()) as logger:
            out = self.uyuni_user.create(uid="Borg", password="futile-resistance", email="")

        assert not out
        assert logger.debug.called
        assert logger.error.called
        assert logger.debug.call_count == 2
        assert logger.debug.call_args_list[0][0] == ("Adding user to Uyuni",)
        assert logger.debug.call_args_list[1][0] == ("Not all parameters has been specified",)
        assert logger.error.call_args_list[0][0] == ("Email should be specified when create user",)
        assert not self.uyuni_user.client.called

    def test_delete(self):
        """
        Test user delete.

        :return:
        """
        self.uyuni_user.client = MagicMock(return_value=True)
        self.uyuni_user.client.get_token = MagicMock(return_value="footoken")

        with patch("uyuni_users.log", MagicMock()) as logger:
            out = self.uyuni_user.delete(name="Borg")

        assert out
        assert not logger.error.called
        assert self.uyuni_user.client.call_args_list[0][0] == ("user.delete", "footoken", "Borg",)

    def test_delete_internal_exc(self):
        """
        Test user delete attempt, UyuniUsersException is raised.

        :return:
        """
        self.uyuni_user.client = MagicMock(side_effect=UyuniUsersException("Stop-bit received"))
        self.uyuni_user.client.get_token = MagicMock(return_value="dogfood")

        with patch("uyuni_users.log", MagicMock()) as logger:
            out = self.uyuni_user.delete(name="Borg")

        assert not out
        assert logger.error.called
        assert logger.error.call_args[0] == ('Unable to delete user "%s": %s', "Borg", "Stop-bit received",)

    def test_delete_unhandled_exc(self):
        """
        Test user delete attempt, common Exception is raised.

        :return:
        """
        self.uyuni_user.client = MagicMock(side_effect=Exception("Feature was not beta-tested"))
        self.uyuni_user.client.get_token = MagicMock(return_value="abcd")

        with patch("uyuni_users.log", MagicMock()) as logger:
            out = self.uyuni_user.delete(name="Borg")

        assert not out
        assert logger.error.called
        assert logger.error.call_args[0] == ('Unhandled error had happened while deleting user "%s": %s',
                                             "Borg", "Feature was not beta-tested",)


class TestUyuniOrg:
    """
    Test suite for Uyuni Org
    """
    orgs = None

    @patch("uyuni_users.RPCClient", MagicMock())
    def setup_method(self, method):
        """
        Setup method before the test.

        :param method:
        :return:
        """
        self.orgs = UyuniOrg()
        self.orgs.client = MagicMock()
        self.orgs.client.get_token = MagicMock(return_value="xyz")

    def teardown_method(self, method):
        """
        Teardown method after the test.

        :param method:
        :return:
        """
        self.orgs = None

    def test_get_org_by_name(self):
        """
        Test get_org_by_name method, normal operation.

        :return:
        """
        rv = {"key": "value"}
        self.orgs.client = MagicMock(return_value=rv)
        assert rv == self.orgs.get_org_by_name(name="Test Org")

    def test_get_org_by_name_exc(self):
        """
        Test get_org_by_name method, exception catching

        :return:
        """
        self.orgs.client = MagicMock(side_effect=UyuniUsersException("Incomplete transient lockout"))
        assert self.orgs.get_org_by_name(name="Test Org") == {}

    def test_create(self):
        """
        Test create org.

        :return:
        """
        with patch("uyuni_users.log", MagicMock()) as logger:
            _, msg = self.orgs.create(name="B-Org", admin_login="who", admin_password="co2", admin_prefix="Dr.",
                                      first_name="Hans", last_name="Schmidt", email="", pam=1)

        assert logger.debug.call_args_list[0][0] == ("Creating organisation %s", "B-Org")
        assert logger.debug.call_args_list[1][0] == (msg,)

    def test_create_int_exc(self):
        """
        Test create org, attempt failed with an internal exception.

        :return:
        """
        self.orgs.client = MagicMock(side_effect=UyuniUsersException("too small filesystem for jumbo Kernel Patch"))
        with patch("uyuni_users.log", MagicMock()) as logger:
            out, msg = self.orgs.create(name="B-Org", admin_login="who", admin_password="co2", admin_prefix="Dr.",
                                        first_name="Hans", last_name="Schmidt", email="", pam=1)

        assert logger.debug.call_args_list[0][0] == ("Creating organisation %s", "B-Org")
        assert out == {}
        assert msg == "Error while creating organisation: too small filesystem for jumbo Kernel Patch"

    def test_create_ext_exc(self):
        """
        Test create org, attempt failed with an external exception.

        :return:
        """
        self.orgs.client = MagicMock(side_effect=Exception("it is stuck in the web"))
        with patch("uyuni_users.log", MagicMock()) as logger:
            out, msg = self.orgs.create(name="B-Org", admin_login="who", admin_password="co2", admin_prefix="Dr.",
                                        first_name="Hans", last_name="Schmidt", email="", pam=1)

        assert logger.debug.call_args_list[0][0] == ("Creating organisation %s", "B-Org")
        assert out == {}
        assert msg == "Unhandled exception occurred while creating new organisation: it is stuck in the web"

    def test_delete(self):
        """
        Test delete org.

        :return:
        """
        self.orgs.get_org_by_name = MagicMock(return_value={"id": 777})
        with patch("uyuni_users.log", MagicMock()) as logger:
            _, msg = self.orgs.delete(name="B-Org")

        assert logger.debug.call_args_list[0][0] == (msg,)

    def test_delete_not_found(self):
        """
        Test an attempt to delete org, but it was not found.

        :return:
        """
        self.orgs.get_org_by_name = MagicMock(return_value={})
        with patch("uyuni_users.log", MagicMock()) as logger:
            _, msg = self.orgs.delete(name="B-Org")

        assert not logger.debug.called
        assert msg == 'Organisation "B-Org" was not found'