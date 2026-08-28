"""
MatonTool - AI Access to Your Favorite Apps via Maton Gateway
https://docs.maton.ai/api-reference/overview

Maton acts as a universal gateway - you connect apps once, then call their
native APIs through Maton with a single API key.
"""

import os
import requests
import json
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, asdict
from enum import Enum


class MatonApp(Enum):
    """Supported apps on Maton platform."""
    SLACK = "slack"
    GITHUB = "github"
    GMAIL = "gmail"
    NOTION = "notion"
    SALESFORCE = "salesforce"
    JIRA = "jira"
    LINEAR = "linear"
    SUPABASE = "supabase"
    STRIPE = "stripe"
    X_TWITTER = "x"  # X (Twitter)
    LINKEDIN = "linkedin"
    DISCORD = "discord"


@dataclass
class MatonConnection:
    connection_id: str
    app: str
    status: str  # PENDING, ACTIVE, EXPIRED, REVOKED
    url: str  # Authorization URL for PENDING connections
    creation_time: str
    last_updated_time: str
    metadata: Dict[str, Any]


@dataclass
class MatonTrigger:
    trigger_id: str
    connection_id: str
    event: str
    status: str
    config: Dict[str, Any]


class MatonTool:
    """
    Maton Gateway Client for ARIA.
    
    Provides unified access to 15+ apps through a single API key.
    """
    
    BASE_URL = "https://api.maton.ai"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get('MATON_API_KEY', '')
        if not self.api_key:
            raise ValueError("MATON_API_KEY not set. Get one at https://maton.ai/settings")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })
    
    # ═══════════════════════════════════════════════════════════════
    # CONNECTION MANAGEMENT
    # ═══════════════════════════════════════════════════════════════
    
    def list_connections(self, app: Optional[str] = None) -> Dict[str, Any]:
        """List all connections, optionally filtered by app."""
        params = {"app": app} if app else {}
        return self._request("GET", "/connections", params=params)
    
    def create_connection(self, app: str, metadata: Dict = None) -> Dict[str, Any]:
        """
        Create a new connection for an app.
        Returns connection with authorization URL - user must visit URL to complete.
        """
        payload = {"app": app}
        if metadata:
            payload["metadata"] = metadata
        return self._request("POST", "/connections", json=payload)
    
    def get_connection(self, connection_id: str) -> Dict[str, Any]:
        """Get connection details including status and auth URL."""
        return self._request("GET", f"/connections/{connection_id}")
    
    def delete_connection(self, connection_id: str) -> Dict[str, Any]:
        """Revoke and delete a connection."""
        return self._request("DELETE", f"/connections/{connection_id}")
    
    def wait_for_connection(self, connection_id: str, timeout: int = 120, poll_interval: int = 3) -> Dict[str, Any]:
        """
        Poll connection until ACTIVE or timeout.
        Useful after creating a connection and opening the auth URL.
        """
        import time
        start = time.time()
        while time.time() - start < timeout:
            result = self.get_connection(connection_id)
            if result.get("connection", {}).get("status") == "ACTIVE":
                return result
            time.sleep(poll_interval)
        return {"error": "Timeout waiting for connection", "connection": self.get_connection(connection_id)}
    
    # ═══════════════════════════════════════════════════════════════
    # GATEWAY API CALLS (Call any app's native API)
    # ═══════════════════════════════════════════════════════════════
    
    def call_app_api(
        self, 
        app: str, 
        endpoint: str, 
        method: str = "GET",
        params: Dict = None,
        json_data: Dict = None,
        headers: Dict = None
    ) -> Dict[str, Any]:
        """
        Call any native API endpoint for a connected app through Maton gateway.
        
        Examples:
            # Slack
            call_app_api("slack", "/api/conversations.list", params={"types": "public_channel"})
            
            # GitHub  
            call_app_api("github", "/repos/owner/repo/issues")
            
            # Gmail
            call_app_api("gmail", "/gmail/v1/users/me/messages")
            
            # Notion
            call_app_api("notion", "/v1/databases/{id}/query", method="POST", json_data={...})
        """
        # Maton gateway format: /{app}/{native_endpoint}
        url = f"/{app}{endpoint}"
        
        # Merge custom headers
        request_headers = dict(self.session.headers)
        if headers:
            request_headers.update(headers)
        
        return self._request(method, url, params=params, json=json_data, headers=request_headers)
    
    # ═══════════════════════════════════════════════════════════════
    # CONVENIENCE METHODS FOR POPULAR APPS
    # ═══════════════════════════════════════════════════════════════
    
    # ─── Slack ───
    def slack_list_channels(self, types: str = "public_channel", limit: int = 20) -> Dict:
        return self.call_app_api("slack", "/api/conversations.list", params={"types": types, "limit": limit})
    
    def slack_post_message(self, channel: str, text: str, blocks: List = None) -> Dict:
        payload = {"channel": channel, "text": text}
        if blocks:
            payload["blocks"] = json.dumps(blocks)
        return self.call_app_api("slack", "/api/chat.postMessage", method="POST", json_data=payload)
    
    def slack_get_user(self, user_id: str) -> Dict:
        return self.call_app_api("slack", "/api/users.info", params={"user": user_id})
    
    # ─── GitHub ───
    def github_get_repo(self, owner: str, repo: str) -> Dict:
        return self.call_app_api("github", f"/repos/{owner}/{repo}")
    
    def github_list_issues(self, owner: str, repo: str, state: str = "open") -> Dict:
        return self.call_app_api("github", f"/repos/{owner}/{repo}/issues", params={"state": state})
    
    def github_create_issue(self, owner: str, repo: str, title: str, body: str = "") -> Dict:
        return self.call_app_api("github", f"/repos/{owner}/{repo}/issues", method="POST", 
                                json_data={"title": title, "body": body})
    
    def github_search_code(self, query: str) -> Dict:
        return self.call_app_api("github", "/search/code", params={"q": query})
    
    # ─── Gmail ───
    def gmail_list_messages(self, query: str = "", max_results: int = 10) -> Dict:
        return self.call_app_api("gmail", "/gmail/v1/users/me/messages", 
                                params={"q": query, "maxResults": max_results})
    
    def gmail_get_message(self, message_id: str) -> Dict:
        return self.call_app_api("gmail", f"/gmail/v1/users/me/messages/{message_id}")
    
    def gmail_send_message(self, to: str, subject: str, body: str, thread_id: str = None) -> Dict:
        import base64
        from email.mime.text import MIMEText
        
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        payload = {"raw": raw}
        if thread_id:
            payload["threadId"] = thread_id
        
        return self.call_app_api("gmail", "/gmail/v1/users/me/messages/send", method="POST", json_data=payload)
    
    # ─── Notion ───
    def notion_search(self, query: str = "") -> Dict:
        return self.call_app_api("notion", "/v1/search", method="POST", 
                                json_data={"query": query} if query else {})
    
    def notion_query_database(self, database_id: str, filter_obj: Dict = None) -> Dict:
        payload = {}
        if filter_obj:
            payload["filter"] = filter_obj
        return self.call_app_api("notion", f"/v1/databases/{database_id}/query", method="POST", json_data=payload)
    
    def notion_create_page(self, parent_id: str, properties: Dict, children: List = None) -> Dict:
        payload = {"parent": {"database_id": parent_id}, "properties": properties}
        if children:
            payload["children"] = children
        return self.call_app_api("notion", "/v1/pages", method="POST", json_data=payload)
    
    # ─── Linear ───
    def linear_get_issues(self, team_id: str = None) -> Dict:
        params = {}
        if team_id:
            params["filter"] = json.dumps({"team": {"id": {"eq": team_id}}})
        return self.call_app_api("linear", "/issues", params=params)
    
    def linear_create_issue(self, team_id: str, title: str, description: str = "") -> Dict:
        return self.call_app_api("linear", "/issues", method="POST", json_data={
            "teamId": team_id,
            "title": title,
            "description": description
        })
    
    # ─── Supabase ───
    def supabase_query(self, table: str, select: str = "*", filters: Dict = None) -> Dict:
        params = {"select": select}
        if filters:
            for k, v in filters.items():
                params[k] = v
        return self.call_app_api("supabase", f"/rest/v1/{table}", params=params)
    
    # ─── Stripe ───
    def stripe_list_customers(self, limit: int = 10) -> Dict:
        return self.call_app_api("stripe", "/v1/customers", params={"limit": limit})
    
    def stripe_create_payment_intent(self, amount: int, currency: str = "usd") -> Dict:
        return self.call_app_api("stripe", "/v1/payment_intents", method="POST", json_data={
            "amount": amount,
            "currency": currency
        })
    
    # ─── X (Twitter) ───
    def x_post_tweet(self, text: str) -> Dict:
        return self.call_app_api("x", "/2/tweets", method="POST", json_data={"text": text})
    
    def x_get_user_tweets(self, user_id: str, max_results: int = 10) -> Dict:
        return self.call_app_api("x", f"/2/users/{user_id}/tweets", params={"max_results": max_results})
    
    # ─── Discord ───
    def discord_get_guilds(self) -> Dict:
        return self.call_app_api("discord", "/users/@me/guilds")
    
    def discord_send_message(self, channel_id: str, content: str) -> Dict:
        return self.call_app_api("discord", f"/channels/{channel_id}/messages", method="POST", 
                                json_data={"content": content})
    
    # ═══════════════════════════════════════════════════════════════
    # TRIGGERS (Webhooks for automation)
    # ═══════════════════════════════════════════════════════════════
    
    def list_triggers(self, connection_id: str = None) -> Dict[str, Any]:
        params = {"connection_id": connection_id} if connection_id else {}
        return self._request("GET", "/triggers", params=params)
    
    def create_trigger(self, connection_id: str, event: str, config: Dict) -> Dict[str, Any]:
        """Create a webhook trigger for an app event."""
        payload = {"connection_id": connection_id, "event": event, "config": config}
        return self._request("POST", "/triggers", json=payload)
    
    def get_trigger(self, trigger_id: str) -> Dict[str, Any]:
        return self._request("GET", f"/triggers/{trigger_id}")
    
    def update_trigger(self, trigger_id: str, config: Dict) -> Dict[str, Any]:
        return self._request("PATCH", f"/triggers/{trigger_id}", json=config)
    
    def delete_trigger(self, trigger_id: str) -> Dict[str, Any]:
        return self._request("DELETE", f"/triggers/{trigger_id}")
    
    def replay_event(self, event_id: str) -> Dict[str, Any]:
        return self._request("POST", f"/events/{event_id}/replay")
    
    # ═══════════════════════════════════════════════════════════════
    # INTERNAL
    # ═══════════════════════════════════════════════════════════════
    
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        url = f"{self.BASE_URL}{path}"
        try:
            response = self.session.request(method, url, timeout=30, **kwargs)
            
            # Maton returns third-party API responses verbatim (including their status codes)
            # But Maton errors have a specific format
            if response.status_code >= 400:
                try:
                    error_data = response.json()
                    if "message" in error_data and "type" in error_data:
                        # This is a Maton error
                        return {
                            "error": error_data.get("message"),
                            "type": error_data.get("type"),
                            "code": error_data.get("code"),
                            "status": response.status_code
                        }
                except:
                    pass
                
                # Return third-party API error verbatim
                return {
                    "error": f"HTTP {response.status_code}",
                    "response": response.text[:1000],
                    "status": response.status_code
                }
            
            try:
                return response.json()
            except:
                return {"raw": response.text}
                
        except requests.exceptions.Timeout:
            return {"error": "Request timed out (30s)"}
        except requests.exceptions.ConnectionError:
            return {"error": "Connection failed - check internet"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}


# ═══════════════════════════════════════════════════════════════
# HIGH-LEVEL WORKFLOWS
# ═══════════════════════════════════════════════════════════════

def setup_slack_workflow(api_key: str) -> Dict[str, Any]:
    """Quick setup: create Slack connection and wait for auth."""
    tool = MatonTool(api_key)
    result = tool.create_connection("slack")
    if "connection" in result:
        conn = result["connection"]
        print(f"🔗 Visit this URL to authorize Slack:\n{conn['url']}")
        print("Waiting for authorization...")
        return tool.wait_for_connection(conn["connection_id"])
    return result


def setup_github_workflow(api_key: str) -> Dict[str, Any]:
    """Quick setup: create GitHub connection and wait for auth."""
    tool = MatonTool(api_key)
    result = tool.create_connection("github")
    if "connection" in result:
        conn = result["connection"]
        print(f"🔗 Visit this URL to authorize GitHub:\n{conn['url']}")
        print("Waiting for authorization...")
        return tool.wait_for_connection(conn["connection_id"])
    return result


# ═══════════════════════════════════════════════════════════════
# AGENT TOOL INTERFACE
# ═══════════════════════════════════════════════════════════════

def maton_tool_dispatch(action: str, args: Dict) -> str:
    """
    Dispatch function for ARIA tool system.
    
    Actions:
    - list_connections: {"app": "slack"} (optional)
    - create_connection: {"app": "slack", "metadata": {}}
    - get_connection: {"connection_id": "..."}
    - delete_connection: {"connection_id": "..."}
    - call_api: {"app": "slack", "endpoint": "/api/conversations.list", "method": "GET", "params": {}, "json_data": {}}
    - slack_channels: {"types": "public_channel", "limit": 20}
    - slack_post: {"channel": "C123", "text": "Hello", "blocks": []}
    - github_repo: {"owner": "user", "repo": "repo"}
    - github_issues: {"owner": "user", "repo": "repo", "state": "open"}
    - github_create_issue: {"owner": "user", "repo": "repo", "title": "Bug", "body": "Details"}
    - gmail_messages: {"query": "is:unread", "max_results": 10}
    - gmail_send: {"to": "email@domain.com", "subject": "Hi", "body": "Message"}
    - notion_search: {"query": "project notes"}
    - notion_query: {"database_id": "...", "filter": {}}
    - linear_issues: {"team_id": "..."}
    - supabase_query: {"table": "users", "select": "*", "filters": {}}
    """
    api_key = os.environ.get('MATON_API_KEY', '')
    if not api_key:
        return json.dumps({"error": "MATON_API_KEY not set in environment"})
    
    tool = MatonTool(api_key)
    
    try:
        if action == "list_connections":
            return json.dumps(tool.list_connections(args.get("app")))
        
        elif action == "create_connection":
            return json.dumps(tool.create_connection(args["app"], args.get("metadata")))
        
        elif action == "get_connection":
            return json.dumps(tool.get_connection(args["connection_id"]))
        
        elif action == "delete_connection":
            return json.dumps(tool.delete_connection(args["connection_id"]))
        
        elif action == "call_api":
            return json.dumps(tool.call_app_api(
                args["app"],
                args["endpoint"],
                args.get("method", "GET"),
                args.get("params"),
                args.get("json_data")
            ))
        
        # Convenience actions
        elif action == "slack_channels":
            return json.dumps(tool.slack_list_channels(args.get("types", "public_channel"), args.get("limit", 20)))
        
        elif action == "slack_post":
            return json.dumps(tool.slack_post_message(args["channel"], args["text"], args.get("blocks")))
        
        elif action == "github_repo":
            return json.dumps(tool.github_get_repo(args["owner"], args["repo"]))
        
        elif action == "github_issues":
            return json.dumps(tool.github_list_issues(args["owner"], args["repo"], args.get("state", "open")))
        
        elif action == "github_create_issue":
            return json.dumps(tool.github_create_issue(args["owner"], args["repo"], args["title"], args.get("body", "")))
        
        elif action == "gmail_messages":
            return json.dumps(tool.gmail_list_messages(args.get("query", ""), args.get("max_results", 10)))
        
        elif action == "gmail_send":
            return json.dumps(tool.gmail_send_message(args["to"], args["subject"], args["body"], args.get("thread_id")))
        
        elif action == "notion_search":
            return json.dumps(tool.notion_search(args.get("query", "")))
        
        elif action == "notion_query":
            return json.dumps(tool.notion_query_database(args["database_id"], args.get("filter")))
        
        elif action == "linear_issues":
            return json.dumps(tool.linear_get_issues(args.get("team_id")))
        
        elif action == "supabase_query":
            return json.dumps(tool.supabase_query(args["table"], args.get("select", "*"), args.get("filters")))
        
        else:
            return json.dumps({"error": f"Unknown action: {action}"})
    
    except Exception as e:
        return json.dumps({"error": f"Maton tool error: {str(e)}"})


if __name__ == "__main__":
    # Demo
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "demo":
        if not os.environ.get('MATON_API_KEY'):
            print("Set MATON_API_KEY to run demo")
            sys.exit(1)
        
        tool = MatonTool()
        print("🔌 Maton Tool Demo")
        print("=" * 40)
        
        # List connections
        print("\n📋 Connections:")
        print(json.dumps(tool.list_connections(), indent=2))
        
        # List supported apps
        print("\n📱 Supported Apps:")
        for app in MatonApp:
            print(f"  - {app.value}")
