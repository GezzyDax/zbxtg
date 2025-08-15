import json
import logging
import time
from typing import List, Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from config import ZabbixConfig


logger = logging.getLogger(__name__)


class ZabbixAPIError(Exception):
    """Исключение для ошибок Zabbix API"""
    pass


class ZabbixClient:
    """Клиент для работы с Zabbix API"""
    
    def __init__(self, config: ZabbixConfig):
        self.config = config
        self.session = self._create_session()
        self.auth_token: Optional[str] = None
        self.request_id = 1
        
    def _create_session(self) -> requests.Session:
        """Создает HTTP сессию с retry-стратегией"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Настройка SSL
        if self.config.ssl_verify:
            # Используем системный CA bundle вместо certifi
            session.verify = '/etc/ssl/certs/ca-certificates.crt'
        else:
            session.verify = False
        session.timeout = 30
        
        return session
    
    def _make_request(self, method: str, params: Dict[str, Any] = None, skip_auth: bool = False) -> Dict[str, Any]:
        """Выполняет запрос к Zabbix API"""
        url = f"{self.config.url.rstrip('/')}/api_jsonrpc.php"
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self.request_id
        }
        
        # Используем API токен или auth токен (если не пропускаем auth)
        if not skip_auth:
            if self.config.api_token:
                payload["auth"] = self.config.api_token
            elif self.auth_token and method != "user.login":
                payload["auth"] = self.auth_token
            
        self.request_id += 1
        
        try:
            response = self.session.post(url, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            if "error" in result:
                raise ZabbixAPIError(f"Zabbix API error: {result['error']}")
                
            return result.get("result", {})
            
        except requests.RequestException as e:
            logger.error(f"HTTP error during Zabbix API request: {e}")
            raise ZabbixAPIError(f"HTTP error: {e}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            raise ZabbixAPIError(f"Invalid JSON response: {e}")
    
    def authenticate(self) -> bool:
        """Аутентификация в Zabbix"""
        # Если используется API токен, аутентификация не требуется
        if self.config.api_token:
            logger.info("Using API token for Zabbix authentication")
            return True
            
        # Аутентификация по username/password
        if not (self.config.username and self.config.password):
            logger.error("No authentication method provided")
            return False
            
        try:
            result = self._make_request("user.login", {
                "user": self.config.username,
                "password": self.config.password
            })
            
            self.auth_token = result
            logger.info("Successfully authenticated to Zabbix")
            return True
            
        except ZabbixAPIError as e:
            logger.error(f"Authentication failed: {e}")
            return False
    
    def get_problems(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Получает список активных проблем"""
        try:
            problems = self._make_request("problem.get", {
                "output": "extend",
                "selectTags": "extend",
                "selectAcknowledges": "extend",
                "recent": True,
                "sortfield": ["eventid"],
                "sortorder": "DESC",
                "limit": limit
            })
            
            return problems
            
        except ZabbixAPIError as e:
            logger.error(f"Failed to get problems: {e}")
            return []
    
    def get_triggers(self, trigger_ids: List[str]) -> List[Dict[str, Any]]:
        """Получает информацию о триггерах"""
        if not trigger_ids:
            return []
            
        try:
            triggers = self._make_request("trigger.get", {
                "output": "extend",
                "triggerids": trigger_ids,
                "selectHosts": ["hostid", "name", "host"],
                "selectItems": ["itemid", "name", "key_"],
                "selectFunctions": "extend",
                "expandDescription": True,
                "expandComment": True
            })
            
            return triggers
            
        except ZabbixAPIError as e:
            logger.error(f"Failed to get triggers: {e}")
            return []
    
    def get_hosts(self, host_ids: List[str]) -> List[Dict[str, Any]]:
        """Получает информацию о хостах"""
        if not host_ids:
            return []
            
        try:
            hosts = self._make_request("host.get", {
                "output": "extend",
                "hostids": host_ids,
                "selectGroups": ["groupid", "name"],
                "selectInterfaces": ["interfaceid", "ip", "dns", "port", "type"]
            })
            
            return hosts
            
        except ZabbixAPIError as e:
            logger.error(f"Failed to get hosts: {e}")
            return []
    
    def get_events(self, event_ids: List[str]) -> List[Dict[str, Any]]:
        """Получает информацию о событиях"""
        if not event_ids:
            return []
            
        try:
            events = self._make_request("event.get", {
                "output": "extend",
                "eventids": event_ids,
                "select_acknowledges": "extend",
                "selectTags": "extend"
            })
            
            return events
            
        except ZabbixAPIError as e:
            logger.error(f"Failed to get events: {e}")
            return []
    
    def check_connection(self) -> bool:
        """Проверяет соединение с Zabbix"""
        try:
            # Если используется API токен, просто проверяем соединение
            if self.config.api_token:
                self._make_request("apiinfo.version")
                return True
                
            # Для username/password аутентификации
            if not self.auth_token:
                return self.authenticate()
                
            # Пробуем получить информацию об API
            self._make_request("apiinfo.version")
            return True
            
        except ZabbixAPIError:
            # Токен мог истечь, пробуем переаутентифицироваться
            if not self.config.api_token:
                self.auth_token = None
                return self.authenticate()
            return False
    
    def get_problem_details(self, problem: Dict[str, Any]) -> Dict[str, Any]:
        """Получает детальную информацию о проблеме"""
        try:
            # Получаем информацию о триггере
            triggers = self.get_triggers([problem["objectid"]])
            trigger = triggers[0] if triggers else {}
            
            # Получаем информацию о хостах
            host_ids = []
            if trigger and "hosts" in trigger:
                host_ids = [host["hostid"] for host in trigger["hosts"]]
            
            hosts = self.get_hosts(host_ids)
            
            return {
                "problem": problem,
                "trigger": trigger,
                "hosts": hosts
            }
            
        except Exception as e:
            logger.error(f"Failed to get problem details: {e}")
            return {"problem": problem, "trigger": {}, "hosts": []}