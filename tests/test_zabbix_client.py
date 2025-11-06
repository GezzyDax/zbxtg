"""Tests for zabbix_client module."""

import json
from unittest.mock import Mock, patch

import pytest
import requests

from zabbix_client import ZabbixAPIError, ZabbixClient


class TestZabbixClient:
    """Tests for ZabbixClient class."""

    def test_client_initialization(self, zabbix_config):
        """Test ZabbixClient initialization."""
        client = ZabbixClient(zabbix_config)
        assert client.config == zabbix_config
        assert client.session is not None
        assert client.auth_token is None
        assert client.request_id == 1

    def test_create_session(self, zabbix_config):
        """Test session creation with SSL settings."""
        client = ZabbixClient(zabbix_config)
        assert client.session is not None
        assert client.session.verify is False  # ssl_verify=False in fixture

    def test_create_session_with_ssl_verify(self, zabbix_config):
        """Test session creation with SSL verification enabled."""
        zabbix_config.ssl_verify = True
        client = ZabbixClient(zabbix_config)
        assert client.session.verify == "/etc/ssl/certs/ca-certificates.crt"

    @patch("zabbix_client.requests.Session.post")
    def test_make_request_success(self, mock_post, zabbix_config, mock_zabbix_response):
        """Test successful API request."""
        mock_response = Mock()
        mock_response.json.return_value = mock_zabbix_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        result = client._make_request("test.method", {"param": "value"})

        assert result == mock_zabbix_response["result"]
        mock_post.assert_called_once()

    @patch("zabbix_client.requests.Session.post")
    def test_make_request_api_error(self, mock_post, zabbix_config):
        """Test API request with error response."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "error": {"code": -32602, "message": "Invalid params"},
            "id": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        with pytest.raises(ZabbixAPIError, match="Zabbix API error"):
            client._make_request("test.method")

    @patch("zabbix_client.requests.Session.post")
    def test_make_request_http_error(self, mock_post, zabbix_config):
        """Test API request with HTTP error."""
        mock_post.side_effect = requests.RequestException("Connection error")

        client = ZabbixClient(zabbix_config)
        with pytest.raises(ZabbixAPIError, match="HTTP error"):
            client._make_request("test.method")

    @patch("zabbix_client.requests.Session.post")
    def test_make_request_json_decode_error(self, mock_post, zabbix_config):
        """Test API request with invalid JSON response."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        with pytest.raises(ZabbixAPIError, match="Invalid JSON response"):
            client._make_request("test.method")

    @patch("zabbix_client.requests.Session.post")
    def test_authenticate_with_api_token(self, mock_post, zabbix_config):
        """Test authentication with API token."""
        client = ZabbixClient(zabbix_config)
        result = client.authenticate()

        assert result is True
        mock_post.assert_not_called()  # No API call needed for token auth

    @patch("zabbix_client.requests.Session.post")
    def test_authenticate_with_username_password(self, mock_post, zabbix_config):
        """Test authentication with username/password."""
        zabbix_config.api_token = None
        zabbix_config.username = "admin"
        zabbix_config.password = "password"

        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": "auth_token_123",
            "id": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        result = client.authenticate()

        assert result is True
        assert client.auth_token == "auth_token_123"

    @patch("zabbix_client.requests.Session.post")
    def test_authenticate_failure(self, mock_post, zabbix_config):
        """Test authentication failure."""
        zabbix_config.api_token = None
        zabbix_config.username = "admin"
        zabbix_config.password = "wrong_password"

        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "error": {"code": -32500, "message": "Invalid credentials"},
            "id": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        result = client.authenticate()

        assert result is False

    @patch("zabbix_client.requests.Session.post")
    def test_get_problems(self, mock_post, zabbix_config, mock_zabbix_response):
        """Test getting problems from Zabbix."""
        mock_response = Mock()
        mock_response.json.return_value = mock_zabbix_response
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        problems = client.get_problems(limit=10)

        assert len(problems) == 1
        assert problems[0]["eventid"] == "12345"
        assert problems[0]["name"] == "Test problem"

    @patch("zabbix_client.requests.Session.post")
    def test_get_problems_error(self, mock_post, zabbix_config):
        """Test getting problems with error."""
        mock_post.side_effect = requests.RequestException("Connection error")

        client = ZabbixClient(zabbix_config)
        problems = client.get_problems()

        assert problems == []

    @patch("zabbix_client.requests.Session.post")
    def test_get_triggers(self, mock_post, zabbix_config):
        """Test getting triggers from Zabbix."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": [
                {
                    "triggerid": "54321",
                    "description": "High CPU usage",
                    "hosts": [{"hostid": "10001", "name": "web-server-01"}],
                }
            ],
            "id": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        triggers = client.get_triggers(["54321"])

        assert len(triggers) == 1
        assert triggers[0]["triggerid"] == "54321"

    @patch("zabbix_client.requests.Session.post")
    def test_get_hosts(self, mock_post, zabbix_config):
        """Test getting hosts from Zabbix."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": [
                {
                    "hostid": "10001",
                    "name": "web-server-01",
                    "interfaces": [{"ip": "192.168.1.100"}],
                }
            ],
            "id": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        hosts = client.get_hosts(["10001"])

        assert len(hosts) == 1
        assert hosts[0]["hostid"] == "10001"
        assert hosts[0]["name"] == "web-server-01"

    @patch("zabbix_client.requests.Session.post")
    def test_check_connection_with_api_token(self, mock_post, zabbix_config):
        """Test connection check with API token."""
        mock_response = Mock()
        mock_response.json.return_value = {
            "jsonrpc": "2.0",
            "result": "6.0.0",
            "id": 1,
        }
        mock_response.raise_for_status = Mock()
        mock_post.return_value = mock_response

        client = ZabbixClient(zabbix_config)
        result = client.check_connection()

        assert result is True

    @patch("zabbix_client.requests.Session.post")
    def test_check_connection_failure(self, mock_post, zabbix_config):
        """Test connection check failure."""
        mock_post.side_effect = requests.RequestException("Connection refused")

        client = ZabbixClient(zabbix_config)
        result = client.check_connection()

        assert result is False

    @patch.object(ZabbixClient, "get_triggers")
    @patch.object(ZabbixClient, "get_hosts")
    def test_get_problem_details(self, mock_get_hosts, mock_get_triggers, zabbix_config):
        """Test getting problem details."""
        mock_get_triggers.return_value = [
            {
                "triggerid": "54321",
                "description": "High CPU",
                "hosts": [{"hostid": "10001"}],
            }
        ]
        mock_get_hosts.return_value = [{"hostid": "10001", "name": "web-server-01"}]

        client = ZabbixClient(zabbix_config)
        problem = {"eventid": "12345", "objectid": "54321"}
        details = client.get_problem_details(problem)

        assert "problem" in details
        assert "trigger" in details
        assert "hosts" in details
        assert details["trigger"]["triggerid"] == "54321"
        assert details["hosts"][0]["hostid"] == "10001"
