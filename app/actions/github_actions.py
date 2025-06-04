# app/actions/github_actions.py
# -*- coding: utf-8 -*-
import logging
import requests 
import json 
from typing import Dict, Any, Optional, List 

from app.core.config import settings
# AuthenticatedHttpClient no se usa aquí, se mantiene la firma por consistencia
from app.shared.helpers.http_client import AuthenticatedHttpClient 

logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"

def _make_github_request(method: str, endpoint: str, params_query: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    action_name_log = f"github_request_{method.lower()}_{endpoint.replace('/', '_')}"
    if not settings.GITHUB_PAT:
        logger.error(f"{action_name_log}: GITHUB_PAT no configurado.")
        return {"status": "error", "action": action_name_log, "message": "Credenciales de GitHub (PAT) no configuradas.", "http_status": 401 }
    
    headers = {
        "Authorization": f"token {settings.GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    url = f"{GITHUB_API_BASE_URL}{endpoint}"
    
    try:
        response = requests.request(method, url, headers=headers, params=params_query, json=json_data, timeout=settings.DEFAULT_API_TIMEOUT)
        response.raise_for_status()
        
        if response.status_code == 204: # No Content
            return {"status": "success", "data": None, "http_status": response.status_code}
        
        response_json = response.json() if response.content else None
        return {"status": "success", "data": response_json, "http_status": response.status_code}

    except requests.exceptions.HTTPError as http_err:
        error_details_response = {}; error_message_from_api = str(http_err) 
        status_code_err = http_err.response.status_code if http_err.response is not None else 500
        try:
            if http_err.response is not None:
                error_details_response = http_err.response.json()
                error_message_from_api = error_details_response.get('message', str(http_err.response.reason))
        except json.JSONDecodeError: 
            error_details_response = {"raw_response": http_err.response.text[:500] if http_err.response is not None else "No response text"}
            error_message_from_api = http_err.response.reason if http_err.response is not None and http_err.response.reason else str(http_err)
        return {"status": "error", "action": action_name_log, "message": f"Error API GitHub: {error_message_from_api}", 
                "details": error_details_response, "http_status": status_code_err}
    except requests.exceptions.RequestException as req_err:
        return {"status": "error", "action": action_name_log, "message": f"Error de conexión con GitHub: {req_err}", "http_status": 503}
    except Exception as e:
        return {"status": "error", "action": action_name_log, "message": "Error inesperado con GitHub.", "details": str(e), "http_status": 500}

def github_list_repos(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "github_list_repos"; logger.info(f"Ejecutando {action_name}: {params}")
    api_params_filtered = {k: v for k, v in {
            "visibility": params.get("visibility"), "affiliation": params.get("affiliation"),
            "type": params.get("type"), "sort": params.get("sort"), "direction": params.get("direction"),
            "per_page": min(int(params.get("per_page", 30)), 100), "page": params.get("page", 1)
        }.items() if v is not None}
    return _make_github_request("GET", "/user/repos", params_query=api_params_filtered)

def github_get_repo_details(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "github_get_repo_details"; logger.info(f"Ejecutando {action_name}: {params}")
    owner: Optional[str] = params.get("owner"); repo: Optional[str] = params.get("repo")
    if not owner or not repo:
        return {"status": "error", "action": action_name, "message": "'owner' y 'repo' obligatorios.", "http_status": 400}
    return _make_github_request("GET", f"/repos/{owner}/{repo}")

def github_create_issue(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}; action_name = "github_create_issue"
    log_params_safe = {k:v for k,v in params.items() if k not in ['body']}
    if 'body' in params: log_params_safe['body_provided'] = True
    logger.info(f"Ejecutando {action_name}: {log_params_safe}")
    owner = params.get("owner"); repo = params.get("repo"); title = params.get("title")
    if not owner or not repo or not title:
        return {"status": "error", "action": action_name, "message": "'owner', 'repo', y 'title' obligatorios.", "http_status": 400}
    issue_data: Dict[str, Any] = {"title": title}
    if params.get("body") is not None: issue_data["body"] = params.get("body")
    if params.get("assignees") and isinstance(params.get("assignees"), list): issue_data["assignees"] = params.get("assignees")
    if params.get("labels") and isinstance(params.get("labels"), list): issue_data["labels"] = params.get("labels")
    if params.get("milestone") and isinstance(params.get("milestone"), int): issue_data["milestone"] = params.get("milestone")
    return _make_github_request("POST", f"/repos/{owner}/{repo}/issues", json_data=issue_data)

# --- FIN DEL MÓDULO actions/github_actions.py ---