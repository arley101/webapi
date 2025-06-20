# app/actions/github_actions.py
# -*- coding: utf-8 -*-
import logging
import requests 
import json 
from typing import Dict, Any, Optional, List 

from app.core.config import settings
# Aunque el cliente AuthenticatedHttpClient se pasa a las funciones públicas,
# _make_github_request usa requests.request directamente con GITHUB_PAT.
# Se mantiene el tipo Optional[AuthenticatedHttpClient] en las firmas por consistencia con action_mapper.
from app.shared.helpers.http_client import AuthenticatedHttpClient 

logger = logging.getLogger(__name__)

GITHUB_API_BASE_URL = "https://api.github.com"

def _make_github_request(method: str, endpoint: str, params_query: Optional[Dict[str, Any]] = None, json_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Helper para realizar solicitudes a la API de GitHub.
    Utiliza GITHUB_PAT para la autenticación.
    """
    action_name_log = f"github_request_{method.lower()}_{endpoint.replace('/', '_')}"

    if not settings.GITHUB_PAT:
        logger.error(f"{action_name_log}: GITHUB_PAT no está configurado en las settings.")
        return {
            "status": "error",
            "action": action_name_log,
            "message": "Credenciales de GitHub (Personal Access Token) no configuradas en el servidor.",
            "http_status": 401 # Unauthorized
        }
    
    headers = {
        "Authorization": f"token {settings.GITHUB_PAT}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28" # Especificar versión de API
    }
    url = f"{GITHUB_API_BASE_URL}{endpoint}"
    
    log_call_details = f"Método: {method}, URL: {url}"
    if params_query: log_call_details += f", QueryParams: {params_query}"
    if json_data: log_call_details += f", JSON Payload Keys: {list(json_data.keys())}"
    logger.debug(f"{action_name_log}: Realizando solicitud. {log_call_details}")

    try:
        response = requests.request(
            method, 
            url, 
            headers=headers, 
            params=params_query, # Parámetros de URL para GET
            json=json_data,      # Cuerpo JSON para POST, PATCH, etc.
            timeout=settings.DEFAULT_API_TIMEOUT
        )
        response.raise_for_status() # Lanza HTTPError para respuestas 4xx/5xx
        
        if response.status_code == 204: # No Content (ej. para DELETE exitoso)
            logger.info(f"{action_name_log}: Solicitud exitosa (204 No Content) a {url}.")
            return {"status": "success", "data": None, "http_status": response.status_code}
        
        response_json = response.json() if response.content else None
        logger.info(f"{action_name_log}: Solicitud exitosa (Status: {response.status_code}) a {url}.")
        return {"status": "success", "data": response_json, "http_status": response.status_code}

    except requests.exceptions.HTTPError as http_err:
        error_details_response = {}
        error_message_from_api = str(http_err) 
        status_code_err = http_err.response.status_code if http_err.response is not None else 500
        
        try:
            if http_err.response is not None:
                error_details_response = http_err.response.json()
                error_message_from_api = error_details_response.get('message', str(http_err.response.reason))
        except json.JSONDecodeError: 
            error_details_response = {"raw_response": http_err.response.text[:500] if http_err.response is not None else "No response text"}
            error_message_from_api = http_err.response.reason if http_err.response is not None and http_err.response.reason else str(http_err)
        
        logger.error(f"{action_name_log}: Error HTTP en GitHub {url}: {status_code_err} - {error_message_from_api}. Detalles: {error_details_response}")
        return {
            "status": "error",
            "action": action_name_log,
            "message": f"Error de API de GitHub: {error_message_from_api}",
            "details": error_details_response,
            "http_status": status_code_err
        }
    except requests.exceptions.RequestException as req_err: # Errores de conexión, timeout, etc.
        logger.error(f"{action_name_log}: Error de conexión con GitHub {url}: {req_err}", exc_info=True)
        return {"status": "error", "action": action_name_log, "message": f"Error de conexión con GitHub: {req_err}", "http_status": 503} # Service Unavailable
    except Exception as e: # Otros errores inesperados
        logger.exception(f"{action_name_log}: Error inesperado con GitHub {url}: {e}")
        return {"status": "error", "action": action_name_log, "message": "Error inesperado al contactar GitHub.", "details": str(e), "http_status": 500}

# El parámetro client: AuthenticatedHttpClient no se usa aquí porque _make_github_request usa requests directamente.
# Se mantiene por consistencia con el action_mapper.
def github_list_repos(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "github_list_repos"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    # Parámetros de API de GitHub para listar repositorios del usuario autenticado (dueño del PAT)
    # https://docs.github.com/en/rest/repos/repos#list-repositories-for-the-authenticated-user
    api_params_filtered = {
        k: v for k, v in {
            "visibility": params.get("visibility"),  # all, public, private
            "affiliation": params.get("affiliation"),# owner, collaborator, organization_member
            "type": params.get("type"),              # all, owner, public, private, member. Default: all
            "sort": params.get("sort"),              # created, updated, pushed, full_name. Default: full_name
            "direction": params.get("direction"),    # asc, desc. Default: (asc for full_name, desc for others)
            "per_page": params.get("per_page", 30),  # Max 100
            "page": params.get("page", 1)
        }.items() if v is not None
    }
    # Asegurar que per_page no exceda 100
    if "per_page" in api_params_filtered:
        api_params_filtered["per_page"] = min(int(api_params_filtered["per_page"]), 100)
        
    logger.info(f"{action_name}: Listando repositorios del usuario autenticado (PAT). Params API: {api_params_filtered}")
    return _make_github_request("GET", "/user/repos", params_query=api_params_filtered)

def github_get_repo_details(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "github_get_repo_details"
    logger.info(f"Ejecutando {action_name} con params: {params}")
    
    owner: Optional[str] = params.get("owner")
    repo: Optional[str] = params.get("repo") # Nombre del repositorio
    
    if not owner or not repo:
        return {"status": "error", "action": action_name, "message": "Parámetros 'owner' (dueño del repo) y 'repo' (nombre del repo) son obligatorios.", "http_status": 400}
    
    logger.info(f"{action_name}: Obteniendo detalles del repositorio '{owner}/{repo}'.")
    return _make_github_request("GET", f"/repos/{owner}/{repo}")

def github_create_issue(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
    params = params or {}
    action_name = "github_create_issue"
    log_params = {k:v for k,v in params.items() if k not in ['body']} # Omitir body del log principal
    if 'body' in params: log_params['body_provided'] = True
    logger.info(f"Ejecutando {action_name} con params: {log_params}")
    
    owner: Optional[str] = params.get("owner")
    repo: Optional[str] = params.get("repo")
    title: Optional[str] = params.get("title")
    body: Optional[str] = params.get("body") # Cuerpo del issue
    assignees: Optional[List[str]] = params.get("assignees") # Lista de logins de usuarios
    labels: Optional[List[str]] = params.get("labels") # Lista de nombres de etiquetas
    milestone_id: Optional[int] = params.get("milestone") # ID numérico del milestone

    if not owner or not repo or not title:
        return {
            "status": "error",
            "action": action_name,
            "message": "Los parámetros 'owner', 'repo', y 'title' son obligatorios para crear un issue.",
            "http_status": 400
        }
    
    issue_data: Dict[str, Any] = {"title": title}
    if body is not None: issue_data["body"] = body # Permitir body vacío si se desea
    if assignees and isinstance(assignees, list): issue_data["assignees"] = assignees
    if labels and isinstance(labels, list): issue_data["labels"] = labels
    if milestone_id and isinstance(milestone_id, int): issue_data["milestone"] = milestone_id
    
    logger.info(f"{action_name}: Creando issue en '{owner}/{repo}' con título: '{title}'. Payload keys: {list(issue_data.keys())}")
    return _make_github_request("POST", f"/repos/{owner}/{repo}/issues", json_data=issue_data)

# La función github_list_issues estaba comentada en el action_mapper original.
# Si se necesita, se puede implementar aquí. Ejemplo:
# def github_list_issues(client: Optional[AuthenticatedHttpClient], params: Dict[str, Any]) -> Dict[str, Any]:
#     params = params or {}
#     action_name = "github_list_issues"
#     logger.info(f"Ejecutando {action_name} con params: {params}")
#     owner: Optional[str] = params.get("owner")
#     repo: Optional[str] = params.get("repo")
#     if not owner or not repo:
#         return {"status": "error", "action": action_name, "message": "'owner' y 'repo' son requeridos.", "http_status": 400}
#     api_params_query = {
#         "milestone": params.get("milestone"), # none, *, o número de ID
#         "state": params.get("state", "open"), # open, closed, all
#         "assignee": params.get("assignee"), # none, *, o login de usuario
#         "creator": params.get("creator"), # login de usuario
#         "mentioned": params.get("mentioned"), # login de usuario
#         "labels": ",".join(params.get("labels")) if params.get("labels") and isinstance(params.get("labels"), list) else params.get("labels"),
#         "sort": params.get("sort", "created"), # created, updated, comments
#         "direction": params.get("direction", "desc"),
#         "since": params.get("since"), # ISO 8601 timestamp
#         "per_page": params.get("per_page", 30),
#         "page": params.get("page", 1)
#     }
#     api_params_query_filtered = {k: v for k, v in api_params_query.items() if v is not None}
#     logger.info(f"{action_name}: Listando issues para '{owner}/{repo}'. Params API: {api_params_query_filtered}")
#     return _make_github_request("GET", f"/repos/{owner}/{repo}/issues", params_query=api_params_query_filtered)

# --- FIN DEL MÓDULO actions/github_actions.py ---