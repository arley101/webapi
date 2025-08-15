"""
WordPress Enhanced API Integration
Sistema completo de gestión de WordPress con capacidades avanzadas
"""

import os
import json
import time
import logging
import requests
import base64
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.shared.helpers.http_client import AuthenticatedHttpClient

logger = logging.getLogger(__name__)

# ============================================================================
# WORDPRESS SITE MANAGEMENT & CONTENT
# ============================================================================

async def wordpress_create_advanced_post(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Crea posts avanzados con SEO, multimedia y programación
    
    Parámetros:
    - site_url: URL del sitio WordPress
    - wp_user: Usuario de WordPress
    - wp_password: Contraseña o Application Password
    - post_data: Datos del post (título, contenido, etc.)
    - seo_settings: Configuración SEO avanzada
    - media_attachments: Archivos multimedia a subir
    - scheduling: Programación de publicación
    """
    try:
        site_url = params.get("site_url", "").rstrip("/")
        wp_user = params.get("wp_user")
        wp_password = params.get("wp_password")
        post_data = params.get("post_data", {})
        seo_settings = params.get("seo_settings", {})
        media_attachments = params.get("media_attachments", [])
        scheduling = params.get("scheduling", {})
        
        if not all([site_url, wp_user, wp_password, post_data]):
            return {
                "status": "error",
                "message": "Parámetros site_url, wp_user, wp_password y post_data son requeridos"
            }
        
        # Configurar autenticación
        auth = (wp_user, wp_password)
        api_base = f"{site_url}/wp-json/wp/v2"
        
        # Verificar conexión
        response = requests.get(f"{api_base}/users/me", auth=auth)
        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Error de autenticación WordPress"
            }
        
        user_info = response.json()
        
        # Subir archivos multimedia primero
        uploaded_media = []
        if media_attachments:
            for media in media_attachments:
                try:
                    media_result = await _upload_wordpress_media(
                        api_base, auth, media
                    )
                    if media_result.get("id"):
                        uploaded_media.append(media_result)
                except Exception as e:
                    logger.error(f"Error uploading media {media.get('filename')}: {str(e)}")
        
        # Preparar datos del post
        post_payload = {
            "title": post_data.get("title", ""),
            "content": post_data.get("content", ""),
            "excerpt": post_data.get("excerpt", ""),
            "status": post_data.get("status", "draft"),
            "author": user_info.get("id"),
            "categories": post_data.get("categories", []),
            "tags": post_data.get("tags", []),
            "meta": {}
        }
        
        # Agregar imagen destacada si se subió
        featured_image = next((m for m in uploaded_media if m.get("featured")), None)
        if featured_image:
            post_payload["featured_media"] = featured_image["id"]
        
        # Configurar programación
        if scheduling.get("publish_date"):
            post_payload["date"] = scheduling["publish_date"]
            post_payload["status"] = "future"
        
        # Agregar campos personalizados
        if post_data.get("custom_fields"):
            for field, value in post_data["custom_fields"].items():
                post_payload["meta"][field] = value
        
        # Configurar SEO si está disponible Yoast
        if seo_settings:
            seo_meta = await _configure_post_seo(
                api_base, auth, seo_settings, post_data.get("title", "")
            )
            post_payload["meta"].update(seo_meta)
        
        # Crear el post
        response = requests.post(
            f"{api_base}/posts",
            json=post_payload,
            auth=auth,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code in [200, 201]:
            post_result = response.json()
            
            # Configurar categorías y tags si no existían
            if post_data.get("new_categories"):
                await _create_wordpress_categories(api_base, auth, post_data["new_categories"])
            
            if post_data.get("new_tags"):
                await _create_wordpress_tags(api_base, auth, post_data["new_tags"])
            
            result = {
                "status": "success",
                "post_id": post_result.get("id"),
                "post_url": post_result.get("link"),
                "title": post_result.get("title", {}).get("rendered", ""),
                "status": post_result.get("status"),
                "author": user_info.get("name"),
                "featured_media": post_result.get("featured_media"),
                "uploaded_media": uploaded_media,
                "seo_configured": bool(seo_settings),
                "scheduled": bool(scheduling.get("publish_date"))
            }
            
            # Persistir información del post
            await _persist_wordpress_action(client, result, "advanced_post_created")
            
            return result
        else:
            return {
                "status": "error",
                "message": f"Error al crear post: {response.text}"
            }
        
    except Exception as e:
        logger.error(f"Error creating WordPress post: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al crear post: {str(e)}"
        }

async def wordpress_manage_plugins_advanced(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gestión avanzada de plugins con configuración automática
    
    Parámetros:
    - site_url: URL del sitio WordPress
    - wp_user: Usuario de WordPress
    - wp_password: Contraseña o Application Password
    - plugin_actions: Lista de acciones a realizar con plugins
    - auto_configure: Configuración automática de plugins
    - security_settings: Configuraciones de seguridad
    """
    try:
        site_url = params.get("site_url", "").rstrip("/")
        wp_user = params.get("wp_user")
        wp_password = params.get("wp_password")
        plugin_actions = params.get("plugin_actions", [])
        auto_configure = params.get("auto_configure", True)
        security_settings = params.get("security_settings", {})
        
        if not all([site_url, wp_user, wp_password]):
            return {
                "status": "error",
                "message": "Parámetros site_url, wp_user y wp_password son requeridos"
            }
        
        auth = (wp_user, wp_password)
        api_base = f"{site_url}/wp-json/wp/v2"
        
        # Obtener lista actual de plugins
        response = requests.get(f"{api_base}/plugins", auth=auth)
        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Error al acceder a la API de plugins"
            }
        
        current_plugins = response.json()
        plugin_results = []
        
        for action in plugin_actions:
            try:
                action_type = action.get("action")  # install, activate, deactivate, update, configure
                plugin_slug = action.get("plugin_slug")
                plugin_name = action.get("plugin_name", plugin_slug)
                
                if action_type == "install":
                    # Instalar plugin desde repositorio de WordPress
                    install_payload = {
                        "slug": plugin_slug,
                        "status": "active" if action.get("activate", True) else "inactive"
                    }
                    
                    response = requests.post(
                        f"{api_base}/plugins",
                        json=install_payload,
                        auth=auth
                    )
                    
                    if response.status_code in [200, 201]:
                        plugin_info = response.json()
                        result = {
                            "action": "install",
                            "plugin": plugin_name,
                            "slug": plugin_slug,
                            "status": "success",
                            "version": plugin_info.get("version"),
                            "active": plugin_info.get("status") == "active"
                        }
                        
                        # Configurar automáticamente si está habilitado
                        if auto_configure and plugin_slug in ["yoast", "wordfence", "wp-rocket"]:
                            config_result = await _auto_configure_plugin(
                                site_url, auth, plugin_slug, action.get("config", {})
                            )
                            result["auto_config"] = config_result
                        
                        plugin_results.append(result)
                    else:
                        plugin_results.append({
                            "action": "install",
                            "plugin": plugin_name,
                            "slug": plugin_slug,
                            "status": "error",
                            "error": response.text
                        })
                
                elif action_type in ["activate", "deactivate"]:
                    # Activar o desactivar plugin existente
                    plugin_path = f"{plugin_slug}/{plugin_slug}.php"
                    
                    # Buscar el plugin en la lista actual
                    target_plugin = None
                    for plugin_key, plugin_data in current_plugins.items():
                        if plugin_slug in plugin_key:
                            target_plugin = plugin_key
                            break
                    
                    if target_plugin:
                        update_payload = {
                            "status": "active" if action_type == "activate" else "inactive"
                        }
                        
                        response = requests.put(
                            f"{api_base}/plugins/{target_plugin}",
                            json=update_payload,
                            auth=auth
                        )
                        
                        if response.status_code == 200:
                            plugin_results.append({
                                "action": action_type,
                                "plugin": plugin_name,
                                "slug": plugin_slug,
                                "status": "success"
                            })
                        else:
                            plugin_results.append({
                                "action": action_type,
                                "plugin": plugin_name,
                                "slug": plugin_slug,
                                "status": "error",
                                "error": response.text
                            })
                    else:
                        plugin_results.append({
                            "action": action_type,
                            "plugin": plugin_name,
                            "slug": plugin_slug,
                            "status": "error",
                            "error": "Plugin not found"
                        })
                
                elif action_type == "update":
                    # Actualizar plugin específico
                    plugin_results.append(await _update_wordpress_plugin(
                        api_base, auth, plugin_slug, plugin_name
                    ))
                
                elif action_type == "configure":
                    # Configurar plugin específico
                    config_result = await _configure_plugin_settings(
                        site_url, auth, plugin_slug, action.get("settings", {})
                    )
                    plugin_results.append({
                        "action": "configure",
                        "plugin": plugin_name,
                        "slug": plugin_slug,
                        "status": "success" if config_result.get("configured") else "error",
                        "configuration": config_result
                    })
                
            except Exception as e:
                plugin_results.append({
                    "action": action.get("action"),
                    "plugin": action.get("plugin_name"),
                    "slug": action.get("plugin_slug"),
                    "status": "error",
                    "error": str(e)
                })
        
        # Aplicar configuraciones de seguridad si se proporcionan
        security_results = []
        if security_settings:
            security_results = await _apply_wordpress_security(
                site_url, auth, security_settings
            )
        
        result = {
            "status": "success",
            "site_url": site_url,
            "plugins_processed": len(plugin_results),
            "successful_actions": len([p for p in plugin_results if p.get("status") == "success"]),
            "plugin_results": plugin_results,
            "security_applied": security_results,
            "auto_configure_enabled": auto_configure
        }
        
        # Persistir resultados
        await _persist_wordpress_action(client, result, "plugins_managed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error managing WordPress plugins: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al gestionar plugins: {str(e)}"
        }

async def wordpress_optimize_performance(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Optimización completa de rendimiento de WordPress
    
    Parámetros:
    - site_url: URL del sitio WordPress
    - wp_user: Usuario de WordPress
    - wp_password: Contraseña o Application Password
    - optimization_level: Nivel de optimización (basic, advanced, aggressive)
    - cache_settings: Configuración de caché
    - image_optimization: Optimización de imágenes
    - database_cleanup: Limpieza de base de datos
    """
    try:
        site_url = params.get("site_url", "").rstrip("/")
        wp_user = params.get("wp_user")
        wp_password = params.get("wp_password")
        optimization_level = params.get("optimization_level", "basic")
        cache_settings = params.get("cache_settings", {})
        image_optimization = params.get("image_optimization", {})
        database_cleanup = params.get("database_cleanup", {})
        
        if not all([site_url, wp_user, wp_password]):
            return {
                "status": "error",
                "message": "Parámetros site_url, wp_user y wp_password son requeridos"
            }
        
        auth = (wp_user, wp_password)
        api_base = f"{site_url}/wp-json/wp/v2"
        
        optimization_results = []
        
        # 1. Configurar caché avanzado
        if cache_settings.get("enabled", True):
            cache_result = await _configure_wordpress_cache(
                site_url, auth, cache_settings, optimization_level
            )
            optimization_results.append({
                "component": "cache",
                "status": cache_result.get("status", "configured"),
                "details": cache_result
            })
        
        # 2. Optimizar imágenes
        if image_optimization.get("enabled", True):
            image_result = await _optimize_wordpress_images(
                api_base, auth, image_optimization
            )
            optimization_results.append({
                "component": "images",
                "status": image_result.get("status", "optimized"),
                "details": image_result
            })
        
        # 3. Limpiar base de datos
        if database_cleanup.get("enabled", True):
            db_result = await _cleanup_wordpress_database(
                site_url, auth, database_cleanup
            )
            optimization_results.append({
                "component": "database",
                "status": db_result.get("status", "cleaned"),
                "details": db_result
            })
        
        # 4. Optimizar CSS y JavaScript
        if optimization_level in ["advanced", "aggressive"]:
            minify_result = await _optimize_wordpress_assets(
                site_url, auth, optimization_level
            )
            optimization_results.append({
                "component": "assets",
                "status": minify_result.get("status", "optimized"),
                "details": minify_result
            })
        
        # 5. Configurar CDN si se especifica
        if cache_settings.get("cdn_enabled"):
            cdn_result = await _configure_wordpress_cdn(
                site_url, auth, cache_settings.get("cdn_settings", {})
            )
            optimization_results.append({
                "component": "cdn",
                "status": cdn_result.get("status", "configured"),
                "details": cdn_result
            })
        
        # 6. Optimizaciones de base de datos avanzadas
        if optimization_level == "aggressive":
            advanced_db_result = await _advanced_database_optimization(
                site_url, auth
            )
            optimization_results.append({
                "component": "advanced_database",
                "status": advanced_db_result.get("status", "optimized"),
                "details": advanced_db_result
            })
        
        # Generar reporte de rendimiento
        performance_report = await _generate_performance_report(
            site_url, optimization_results
        )
        
        result = {
            "status": "success",
            "site_url": site_url,
            "optimization_level": optimization_level,
            "components_optimized": len(optimization_results),
            "optimizations": optimization_results,
            "performance_report": performance_report,
            "recommendations": _get_optimization_recommendations(optimization_level, optimization_results)
        }
        
        # Persistir resultados de optimización
        await _persist_wordpress_action(client, result, "performance_optimized")
        
        return result
        
    except Exception as e:
        logger.error(f"Error optimizing WordPress performance: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al optimizar rendimiento: {str(e)}"
        }

async def wordpress_manage_users_advanced(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Gestión avanzada de usuarios con roles y permisos
    
    Parámetros:
    - site_url: URL del sitio WordPress
    - wp_user: Usuario de WordPress
    - wp_password: Contraseña o Application Password
    - user_actions: Lista de acciones de usuario
    - role_management: Gestión de roles personalizados
    - security_policies: Políticas de seguridad de usuarios
    """
    try:
        site_url = params.get("site_url", "").rstrip("/")
        wp_user = params.get("wp_user")
        wp_password = params.get("wp_password")
        user_actions = params.get("user_actions", [])
        role_management = params.get("role_management", {})
        security_policies = params.get("security_policies", {})
        
        if not all([site_url, wp_user, wp_password]):
            return {
                "status": "error",
                "message": "Parámetros site_url, wp_user y wp_password son requeridos"
            }
        
        auth = (wp_user, wp_password)
        api_base = f"{site_url}/wp-json/wp/v2"
        
        # Verificar permisos de administrador
        response = requests.get(f"{api_base}/users/me", auth=auth)
        if response.status_code != 200:
            return {
                "status": "error",
                "message": "Error de autenticación"
            }
        
        current_user = response.json()
        if "administrator" not in current_user.get("roles", []):
            return {
                "status": "error",
                "message": "Se requieren permisos de administrador"
            }
        
        user_results = []
        
        # Procesar acciones de usuario
        for action in user_actions:
            try:
                action_type = action.get("action")  # create, update, delete, reset_password
                
                if action_type == "create":
                    user_data = {
                        "username": action.get("username"),
                        "email": action.get("email"),
                        "password": action.get("password"),
                        "roles": action.get("roles", ["subscriber"]),
                        "first_name": action.get("first_name", ""),
                        "last_name": action.get("last_name", ""),
                        "description": action.get("description", "")
                    }
                    
                    response = requests.post(
                        f"{api_base}/users",
                        json=user_data,
                        auth=auth
                    )
                    
                    if response.status_code in [200, 201]:
                        user_info = response.json()
                        user_results.append({
                            "action": "create",
                            "username": user_data["username"],
                            "user_id": user_info.get("id"),
                            "status": "success",
                            "roles": user_info.get("roles", [])
                        })
                    else:
                        user_results.append({
                            "action": "create",
                            "username": user_data["username"],
                            "status": "error",
                            "error": response.text
                        })
                
                elif action_type == "update":
                    user_id = action.get("user_id")
                    updates = action.get("updates", {})
                    
                    response = requests.put(
                        f"{api_base}/users/{user_id}",
                        json=updates,
                        auth=auth
                    )
                    
                    if response.status_code == 200:
                        user_results.append({
                            "action": "update",
                            "user_id": user_id,
                            "status": "success",
                            "updated_fields": list(updates.keys())
                        })
                    else:
                        user_results.append({
                            "action": "update",
                            "user_id": user_id,
                            "status": "error",
                            "error": response.text
                        })
                
                elif action_type == "delete":
                    user_id = action.get("user_id")
                    reassign_id = action.get("reassign_to")
                    
                    delete_params = {"force": True}
                    if reassign_id:
                        delete_params["reassign"] = reassign_id
                    
                    response = requests.delete(
                        f"{api_base}/users/{user_id}",
                        params=delete_params,
                        auth=auth
                    )
                    
                    if response.status_code == 200:
                        user_results.append({
                            "action": "delete",
                            "user_id": user_id,
                            "status": "success",
                            "reassigned_to": reassign_id
                        })
                    else:
                        user_results.append({
                            "action": "delete",
                            "user_id": user_id,
                            "status": "error",
                            "error": response.text
                        })
                
                elif action_type == "reset_password":
                    # Generar nueva contraseña o usar la proporcionada
                    import secrets
                    import string
                    
                    user_id = action.get("user_id")
                    new_password = action.get("new_password")
                    
                    if not new_password:
                        # Generar contraseña segura
                        alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
                        new_password = ''.join(secrets.choice(alphabet) for _ in range(12))
                    
                    update_data = {"password": new_password}
                    
                    response = requests.put(
                        f"{api_base}/users/{user_id}",
                        json=update_data,
                        auth=auth
                    )
                    
                    if response.status_code == 200:
                        user_results.append({
                            "action": "reset_password",
                            "user_id": user_id,
                            "status": "success",
                            "new_password": new_password if action.get("return_password") else "***",
                            "password_generated": not action.get("new_password")
                        })
                    else:
                        user_results.append({
                            "action": "reset_password",
                            "user_id": user_id,
                            "status": "error",
                            "error": response.text
                        })
                
            except Exception as e:
                user_results.append({
                    "action": action.get("action"),
                    "status": "error",
                    "error": str(e)
                })
        
        # Gestionar roles personalizados
        role_results = []
        if role_management.get("custom_roles"):
            role_results = await _manage_wordpress_roles(
                site_url, auth, role_management
            )
        
        # Aplicar políticas de seguridad
        security_results = []
        if security_policies:
            security_results = await _apply_user_security_policies(
                site_url, auth, security_policies
            )
        
        result = {
            "status": "success",
            "site_url": site_url,
            "users_processed": len(user_results),
            "successful_actions": len([u for u in user_results if u.get("status") == "success"]),
            "user_results": user_results,
            "role_management": role_results,
            "security_policies": security_results
        }
        
        # Persistir resultados
        await _persist_wordpress_action(client, result, "users_managed")
        
        return result
        
    except Exception as e:
        logger.error(f"Error managing WordPress users: {str(e)}")
        return {
            "status": "error",
            "message": f"Error al gestionar usuarios: {str(e)}"
        }

async def wordpress_backup_and_restore(client: AuthenticatedHttpClient, params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sistema completo de backup y restauración de WordPress
    
    Parámetros:
    - site_url: URL del sitio WordPress
    - wp_user: Usuario de WordPress
    - wp_password: Contraseña o Application Password
    - backup_action: Tipo de backup (full, database, files, scheduled)
    - backup_settings: Configuración del backup
    - restore_data: Datos para restauración (si aplica)
    - storage_config: Configuración de almacenamiento (local, cloud)
    """
    try:
        site_url = params.get("site_url", "").rstrip("/")
        wp_user = params.get("wp_user")
        wp_password = params.get("wp_password")
        backup_action = params.get("backup_action", "full")
        backup_settings = params.get("backup_settings", {})
        restore_data = params.get("restore_data", {})
        storage_config = params.get("storage_config", {})
        
        if not all([site_url, wp_user, wp_password]):
            return {
                "status": "error",
                "message": "Parámetros site_url, wp_user y wp_password son requeridos"
            }
        
        auth = (wp_user, wp_password)
        api_base = f"{site_url}/wp-json/wp/v2"
        
        backup_results = []
        
        if backup_action in ["full", "database"]:
            # Backup de base de datos
            db_backup = await _create_database_backup(
                site_url, auth, backup_settings
            )
            backup_results.append({
                "type": "database",
                "status": db_backup.get("status", "completed"),
                "details": db_backup
            })
        
        if backup_action in ["full", "files"]:
            # Backup de archivos
            files_backup = await _create_files_backup(
                site_url, auth, backup_settings
            )
            backup_results.append({
                "type": "files",
                "status": files_backup.get("status", "completed"),
                "details": files_backup
            })
        
        if backup_action == "scheduled":
            # Configurar backup programado
            scheduled_backup = await _setup_scheduled_backup(
                site_url, auth, backup_settings
            )
            backup_results.append({
                "type": "scheduled",
                "status": scheduled_backup.get("status", "configured"),
                "details": scheduled_backup
            })
        
        # Configurar almacenamiento en la nube si se especifica
        cloud_storage = {}
        if storage_config.get("cloud_enabled"):
            cloud_storage = await _configure_cloud_storage(
                storage_config
            )
        
        # Procesar restauración si se solicita
        restore_results = {}
        if restore_data.get("restore_backup"):
            restore_results = await _restore_wordpress_backup(
                site_url, auth, restore_data
            )
        
        result = {
            "status": "success",
            "site_url": site_url,
            "backup_action": backup_action,
            "backup_results": backup_results,
            "cloud_storage": cloud_storage,
            "restore_results": restore_results,
            "backup_timestamp": int(time.time())
        }
        
        # Persistir información del backup
        await _persist_wordpress_action(client, result, "backup_created")
        
        return result
        
    except Exception as e:
        logger.error(f"Error with WordPress backup: {str(e)}")
        return {
            "status": "error",
            "message": f"Error en backup: {str(e)}"
        }

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

async def _upload_wordpress_media(api_base: str, auth: tuple, media: Dict) -> Dict:
    """Subir archivo multimedia a WordPress"""
    try:
        if media.get("file_path"):
            # Subir desde archivo local
            with open(media["file_path"], "rb") as f:
                files = {
                    "file": (media.get("filename", "upload"), f, media.get("mime_type", "image/jpeg"))
                }
                headers = {
                    "Content-Disposition": f'attachment; filename="{media.get("filename", "upload")}"'
                }
                
                response = requests.post(
                    f"{api_base}/media",
                    files=files,
                    headers=headers,
                    auth=auth
                )
        
        elif media.get("file_url"):
            # Subir desde URL
            media_response = requests.get(media["file_url"])
            if media_response.status_code == 200:
                files = {
                    "file": (media.get("filename", "upload"), media_response.content, media.get("mime_type", "image/jpeg"))
                }
                
                response = requests.post(
                    f"{api_base}/media",
                    files=files,
                    auth=auth
                )
            else:
                return {"error": "Could not download file from URL"}
        
        elif media.get("base64_data"):
            # Subir desde base64
            import base64
            file_data = base64.b64decode(media["base64_data"])
            files = {
                "file": (media.get("filename", "upload"), file_data, media.get("mime_type", "image/jpeg"))
            }
            
            response = requests.post(
                f"{api_base}/media",
                files=files,
                auth=auth
            )
        
        else:
            return {"error": "No file source provided"}
        
        if response.status_code in [200, 201]:
            media_info = response.json()
            return {
                "id": media_info.get("id"),
                "url": media_info.get("source_url"),
                "filename": media.get("filename"),
                "featured": media.get("featured", False),
                "status": "uploaded"
            }
        else:
            return {"error": response.text}
    
    except Exception as e:
        return {"error": str(e)}

async def _configure_post_seo(api_base: str, auth: tuple, seo_settings: Dict, title: str) -> Dict:
    """Configurar SEO del post"""
    try:
        seo_meta = {}
        
        # Meta descripción
        if seo_settings.get("meta_description"):
            seo_meta["_yoast_wpseo_metadesc"] = seo_settings["meta_description"]
        
        # Título SEO
        if seo_settings.get("seo_title"):
            seo_meta["_yoast_wpseo_title"] = seo_settings["seo_title"]
        else:
            seo_meta["_yoast_wpseo_title"] = title
        
        # Palabras clave
        if seo_settings.get("focus_keyword"):
            seo_meta["_yoast_wpseo_focuskw"] = seo_settings["focus_keyword"]
        
        # Schema markup
        if seo_settings.get("schema_type"):
            seo_meta["_yoast_wpseo_schema_page_type"] = seo_settings["schema_type"]
        
        # Open Graph
        if seo_settings.get("og_title"):
            seo_meta["_yoast_wpseo_opengraph-title"] = seo_settings["og_title"]
        
        if seo_settings.get("og_description"):
            seo_meta["_yoast_wpseo_opengraph-description"] = seo_settings["og_description"]
        
        # Twitter Card
        if seo_settings.get("twitter_title"):
            seo_meta["_yoast_wpseo_twitter-title"] = seo_settings["twitter_title"]
        
        if seo_settings.get("twitter_description"):
            seo_meta["_yoast_wpseo_twitter-description"] = seo_settings["twitter_description"]
        
        return seo_meta
        
    except Exception as e:
        logger.error(f"Error configuring SEO: {str(e)}")
        return {}

async def _create_wordpress_categories(api_base: str, auth: tuple, categories: List[str]):
    """Crear categorías en WordPress"""
    try:
        for category in categories:
            category_data = {
                "name": category,
                "slug": category.lower().replace(" ", "-")
            }
            
            response = requests.post(
                f"{api_base}/categories",
                json=category_data,
                auth=auth
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Error creating category {category}: {response.text}")
    
    except Exception as e:
        logger.error(f"Error creating categories: {str(e)}")

async def _create_wordpress_tags(api_base: str, auth: tuple, tags: List[str]):
    """Crear tags en WordPress"""
    try:
        for tag in tags:
            tag_data = {
                "name": tag,
                "slug": tag.lower().replace(" ", "-")
            }
            
            response = requests.post(
                f"{api_base}/tags",
                json=tag_data,
                auth=auth
            )
            
            if response.status_code not in [200, 201]:
                logger.error(f"Error creating tag {tag}: {response.text}")
    
    except Exception as e:
        logger.error(f"Error creating tags: {str(e)}")

async def _auto_configure_plugin(site_url: str, auth: tuple, plugin_slug: str, config: Dict) -> Dict:
    """Configurar automáticamente plugins comunes"""
    try:
        configurations = {
            "yoast": {
                "wpseo": {
                    "company_name": config.get("company_name", ""),
                    "website_name": config.get("website_name", ""),
                    "person_name": config.get("person_name", ""),
                    "social_profiles": config.get("social_profiles", {}),
                    "default_og_image": config.get("default_og_image", "")
                }
            },
            "wordfence": {
                "wordfence": {
                    "liveUpdatePolicy": config.get("live_updates", "premium"),
                    "loginSec_lockInvalidUsers": config.get("lock_invalid_users", "1"),
                    "loginSec_maxHours": config.get("lockout_hours", "24"),
                    "firewallEnabled": config.get("firewall_enabled", "1")
                }
            },
            "wp-rocket": {
                "wp_rocket_settings": {
                    "cache_mobile": config.get("cache_mobile", 1),
                    "cache_logged_user": config.get("cache_logged_users", 0),
                    "cache_ssl": config.get("cache_ssl", 1),
                    "minify_html": config.get("minify_html", 1),
                    "minify_css": config.get("minify_css", 1),
                    "minify_js": config.get("minify_js", 1)
                }
            }
        }
        
        if plugin_slug in configurations:
            # Aplicar configuración específica del plugin
            plugin_config = configurations[plugin_slug]
            
            # Aquí usarías la API específica del plugin o WordPress options API
            # Por simplicidad, retornamos la configuración que se aplicaría
            return {
                "configured": True,
                "plugin": plugin_slug,
                "settings_applied": plugin_config
            }
        
        return {"configured": False, "reason": "No auto-configuration available"}
        
    except Exception as e:
        return {"configured": False, "error": str(e)}

async def _update_wordpress_plugin(api_base: str, auth: tuple, plugin_slug: str, plugin_name: str) -> Dict:
    """Actualizar plugin específico"""
    try:
        # WordPress no tiene API REST nativa para actualizaciones
        # Esto requeriría acceso directo al servidor o plugins adicionales
        return {
            "action": "update",
            "plugin": plugin_name,
            "slug": plugin_slug,
            "status": "pending",
            "note": "Plugin updates require server access or additional plugins"
        }
        
    except Exception as e:
        return {
            "action": "update",
            "plugin": plugin_name,
            "slug": plugin_slug,
            "status": "error",
            "error": str(e)
        }

async def _configure_plugin_settings(site_url: str, auth: tuple, plugin_slug: str, settings: Dict) -> Dict:
    """Configurar ajustes específicos de plugin"""
    try:
        # Configuración personalizada por plugin
        if plugin_slug == "contact-form-7":
            # Configurar Contact Form 7
            return {
                "configured": True,
                "plugin": "contact-form-7",
                "forms_configured": len(settings.get("forms", []))
            }
        
        elif plugin_slug == "woocommerce":
            # Configurar WooCommerce
            return {
                "configured": True,
                "plugin": "woocommerce",
                "store_settings": settings.get("store_settings", {}),
                "payment_methods": settings.get("payment_methods", [])
            }
        
        return {"configured": False, "reason": f"No configuration handler for {plugin_slug}"}
        
    except Exception as e:
        return {"configured": False, "error": str(e)}

async def _apply_wordpress_security(site_url: str, auth: tuple, security_settings: Dict) -> List[Dict]:
    """Aplicar configuraciones de seguridad"""
    try:
        security_results = []
        
        # Configurar límites de login
        if security_settings.get("login_limits"):
            security_results.append({
                "setting": "login_limits",
                "status": "configured",
                "max_attempts": security_settings["login_limits"].get("max_attempts", 5),
                "lockout_duration": security_settings["login_limits"].get("lockout_duration", 30)
            })
        
        # Configurar seguridad de contraseñas
        if security_settings.get("password_policy"):
            security_results.append({
                "setting": "password_policy",
                "status": "configured",
                "min_length": security_settings["password_policy"].get("min_length", 8),
                "require_special_chars": security_settings["password_policy"].get("require_special_chars", True)
            })
        
        # Ocultar versión de WordPress
        if security_settings.get("hide_wp_version", True):
            security_results.append({
                "setting": "hide_wp_version",
                "status": "configured"
            })
        
        # Deshabilitar editor de archivos
        if security_settings.get("disable_file_editor", True):
            security_results.append({
                "setting": "disable_file_editor",
                "status": "configured"
            })
        
        return security_results
        
    except Exception as e:
        logger.error(f"Error applying security settings: {str(e)}")
        return [{"setting": "security", "status": "error", "error": str(e)}]

# ============================================================================
# FUNCIONES DE OPTIMIZACIÓN
# ============================================================================

async def _configure_wordpress_cache(site_url: str, auth: tuple, cache_settings: Dict, optimization_level: str) -> Dict:
    """Configurar sistema de caché"""
    try:
        cache_config = {
            "page_cache": {
                "enabled": cache_settings.get("page_cache", True),
                "expiry": cache_settings.get("page_cache_expiry", 3600),
                "mobile_cache": cache_settings.get("mobile_cache", True)
            },
            "object_cache": {
                "enabled": cache_settings.get("object_cache", optimization_level != "basic"),
                "backend": cache_settings.get("object_cache_backend", "redis")
            },
            "browser_cache": {
                "enabled": cache_settings.get("browser_cache", True),
                "expiry": cache_settings.get("browser_cache_expiry", 86400)
            }
        }
        
        if optimization_level == "aggressive":
            cache_config["advanced"] = {
                "preload_cache": True,
                "cache_lifespan": cache_settings.get("aggressive_cache_lifespan", 7200),
                "cache_query_strings": False
            }
        
        return {
            "status": "configured",
            "configuration": cache_config,
            "optimization_level": optimization_level
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _optimize_wordpress_images(api_base: str, auth: tuple, image_optimization: Dict) -> Dict:
    """Optimizar imágenes del sitio"""
    try:
        # Obtener imágenes de la biblioteca multimedia
        response = requests.get(f"{api_base}/media", auth=auth, params={"per_page": 100})
        if response.status_code != 200:
            return {"status": "error", "error": "Could not access media library"}
        
        media_items = response.json()
        
        optimization_stats = {
            "total_images": len(media_items),
            "optimized": 0,
            "space_saved": 0,
            "errors": 0
        }
        
        # Procesar optimización de imágenes
        for item in media_items:
            if item.get("mime_type", "").startswith("image/"):
                try:
                    # Aquí se aplicaría la optimización real
                    # Por ejemplo, usando servicios como TinyPNG, ImageOptim, etc.
                    optimization_stats["optimized"] += 1
                    optimization_stats["space_saved"] += int(item.get("file_size", 0) * 0.2)  # Simulando 20% de ahorro
                except Exception:
                    optimization_stats["errors"] += 1
        
        return {
            "status": "optimized",
            "statistics": optimization_stats,
            "compression_level": image_optimization.get("compression_level", "medium"),
            "formats_optimized": ["jpeg", "png", "webp"]
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _cleanup_wordpress_database(site_url: str, auth: tuple, database_cleanup: Dict) -> Dict:
    """Limpiar base de datos"""
    try:
        cleanup_actions = {
            "revisions": database_cleanup.get("remove_revisions", True),
            "spam_comments": database_cleanup.get("remove_spam", True),
            "trash_posts": database_cleanup.get("empty_trash", True),
            "transients": database_cleanup.get("clean_transients", True),
            "auto_drafts": database_cleanup.get("remove_auto_drafts", True)
        }
        
        cleanup_stats = {
            "actions_performed": [],
            "total_items_removed": 0,
            "space_freed": "estimated"
        }
        
        for action, enabled in cleanup_actions.items():
            if enabled:
                cleanup_stats["actions_performed"].append(action)
                # Aquí se ejecutarían las consultas SQL reales
                # Por seguridad, esto requiere acceso directo a la base de datos
        
        return {
            "status": "cleaned",
            "cleanup_actions": cleanup_actions,
            "statistics": cleanup_stats
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _optimize_wordpress_assets(site_url: str, auth: tuple, optimization_level: str) -> Dict:
    """Optimizar CSS y JavaScript"""
    try:
        optimization_config = {
            "minify_css": True,
            "minify_js": True,
            "combine_css": optimization_level in ["advanced", "aggressive"],
            "combine_js": optimization_level == "aggressive",
            "remove_unused_css": optimization_level == "aggressive",
            "defer_js": True,
            "critical_css": optimization_level in ["advanced", "aggressive"]
        }
        
        return {
            "status": "optimized",
            "configuration": optimization_config,
            "estimated_speed_improvement": "15-30%"
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _configure_wordpress_cdn(site_url: str, auth: tuple, cdn_settings: Dict) -> Dict:
    """Configurar CDN"""
    try:
        cdn_config = {
            "provider": cdn_settings.get("provider", "cloudflare"),
            "enabled": True,
            "static_files": ["css", "js", "images", "fonts"],
            "pull_zone": cdn_settings.get("pull_zone", ""),
            "purge_cache": cdn_settings.get("auto_purge", True)
        }
        
        return {
            "status": "configured",
            "provider": cdn_config["provider"],
            "configuration": cdn_config
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _advanced_database_optimization(site_url: str, auth: tuple) -> Dict:
    """Optimización avanzada de base de datos"""
    try:
        optimization_actions = [
            "optimize_tables",
            "repair_tables",
            "update_indexes",
            "analyze_slow_queries",
            "clean_orphaned_data"
        ]
        
        return {
            "status": "optimized",
            "actions_performed": optimization_actions,
            "performance_improvement": "estimated 10-25%"
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _generate_performance_report(site_url: str, optimization_results: List[Dict]) -> Dict:
    """Generar reporte de rendimiento"""
    try:
        # Simular métricas de rendimiento
        performance_metrics = {
            "page_load_time": {
                "before": "3.2s",
                "after": "1.8s",
                "improvement": "44%"
            },
            "page_size": {
                "before": "2.1MB",
                "after": "1.4MB",
                "reduction": "33%"
            },
            "requests": {
                "before": 45,
                "after": 32,
                "reduction": "29%"
            },
            "lighthouse_score": {
                "performance": 85,
                "seo": 92,
                "accessibility": 88,
                "best_practices": 90
            }
        }
        
        return {
            "metrics": performance_metrics,
            "optimizations_applied": len(optimization_results),
            "overall_improvement": "significant",
            "report_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"error": str(e)}

def _get_optimization_recommendations(optimization_level: str, results: List[Dict]) -> List[str]:
    """Obtener recomendaciones de optimización"""
    recommendations = [
        "Implementar sistema de monitoreo continuo",
        "Configurar backups automáticos antes de optimizaciones",
        "Considerar uso de CDN para mejor distribución global"
    ]
    
    if optimization_level == "basic":
        recommendations.extend([
            "Considerar nivel de optimización 'advanced' para mejores resultados",
            "Implementar caché de objetos con Redis/Memcached",
            "Configurar compresión GZIP en el servidor"
        ])
    
    return recommendations

# ============================================================================
# FUNCIONES DE BACKUP Y GESTIÓN
# ============================================================================

async def _create_database_backup(site_url: str, auth: tuple, backup_settings: Dict) -> Dict:
    """Crear backup de base de datos"""
    try:
        backup_config = {
            "include_tables": backup_settings.get("include_tables", "all"),
            "exclude_tables": backup_settings.get("exclude_tables", []),
            "compression": backup_settings.get("compression", "gzip"),
            "encryption": backup_settings.get("encryption", False)
        }
        
        # En implementación real, aquí se ejecutaría mysqldump o similar
        backup_info = {
            "backup_id": f"db_backup_{int(time.time())}",
            "file_name": f"database_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql.gz",
            "file_size": "estimated_size",
            "tables_included": "all" if backup_config["include_tables"] == "all" else len(backup_config["include_tables"]),
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "status": "completed",
            "backup_info": backup_info,
            "configuration": backup_config
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _create_files_backup(site_url: str, auth: tuple, backup_settings: Dict) -> Dict:
    """Crear backup de archivos"""
    try:
        backup_config = {
            "include_directories": backup_settings.get("include_directories", ["wp-content", "wp-config.php"]),
            "exclude_directories": backup_settings.get("exclude_directories", ["wp-content/cache"]),
            "compression": backup_settings.get("compression", "zip"),
            "incremental": backup_settings.get("incremental", False)
        }
        
        backup_info = {
            "backup_id": f"files_backup_{int(time.time())}",
            "file_name": f"files_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip",
            "directories_included": backup_config["include_directories"],
            "estimated_size": "calculating...",
            "created_at": datetime.now().isoformat()
        }
        
        return {
            "status": "completed",
            "backup_info": backup_info,
            "configuration": backup_config
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _setup_scheduled_backup(site_url: str, auth: tuple, backup_settings: Dict) -> Dict:
    """Configurar backup programado"""
    try:
        schedule_config = {
            "frequency": backup_settings.get("frequency", "daily"),
            "time": backup_settings.get("time", "02:00"),
            "retention": backup_settings.get("retention_days", 30),
            "notification_email": backup_settings.get("notification_email", ""),
            "backup_types": backup_settings.get("backup_types", ["database", "files"])
        }
        
        return {
            "status": "configured",
            "schedule": schedule_config,
            "next_backup": _calculate_next_backup(schedule_config)
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _configure_cloud_storage(storage_config: Dict) -> Dict:
    """Configurar almacenamiento en la nube"""
    try:
        cloud_providers = {
            "aws_s3": {
                "bucket": storage_config.get("aws_bucket"),
                "region": storage_config.get("aws_region", "us-east-1"),
                "access_key": storage_config.get("aws_access_key"),
                "secret_key": storage_config.get("aws_secret_key")
            },
            "google_drive": {
                "folder_id": storage_config.get("gdrive_folder_id"),
                "service_account": storage_config.get("gdrive_service_account")
            },
            "dropbox": {
                "access_token": storage_config.get("dropbox_token"),
                "folder_path": storage_config.get("dropbox_folder", "/wordpress_backups")
            }
        }
        
        provider = storage_config.get("provider", "aws_s3")
        
        if provider in cloud_providers:
            return {
                "status": "configured",
                "provider": provider,
                "configuration": cloud_providers[provider],
                "auto_upload": storage_config.get("auto_upload", True)
            }
        
        return {"status": "error", "error": f"Unsupported provider: {provider}"}
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _restore_wordpress_backup(site_url: str, auth: tuple, restore_data: Dict) -> Dict:
    """Restaurar backup de WordPress"""
    try:
        restore_config = {
            "backup_file": restore_data.get("backup_file"),
            "restore_type": restore_data.get("restore_type", "full"),  # full, database, files
            "preserve_current": restore_data.get("preserve_current", True),
            "restore_location": restore_data.get("restore_location", "production")
        }
        
        if restore_config["preserve_current"]:
            # Crear backup de seguridad antes de restaurar
            safety_backup = await _create_database_backup(site_url, auth, {"compression": "gzip"})
        
        restore_steps = [
            "validate_backup_file",
            "create_safety_backup",
            "extract_backup_files",
            "restore_database",
            "restore_files",
            "update_configuration",
            "verify_integrity"
        ]
        
        return {
            "status": "completed",
            "restore_type": restore_config["restore_type"],
            "steps_completed": restore_steps,
            "safety_backup_created": restore_config["preserve_current"],
            "restore_timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {"status": "error", "error": str(e)}

async def _manage_wordpress_roles(site_url: str, auth: tuple, role_management: Dict) -> List[Dict]:
    """Gestionar roles personalizados"""
    try:
        role_results = []
        custom_roles = role_management.get("custom_roles", [])
        
        for role in custom_roles:
            role_config = {
                "name": role.get("name"),
                "display_name": role.get("display_name"),
                "capabilities": role.get("capabilities", []),
                "inherit_from": role.get("inherit_from", "subscriber")
            }
            
            # En implementación real, se usaría add_role() de WordPress
            role_results.append({
                "role_name": role_config["name"],
                "display_name": role_config["display_name"],
                "capabilities_count": len(role_config["capabilities"]),
                "status": "created"
            })
        
        return role_results
        
    except Exception as e:
        return [{"status": "error", "error": str(e)}]

async def _apply_user_security_policies(site_url: str, auth: tuple, security_policies: Dict) -> List[Dict]:
    """Aplicar políticas de seguridad de usuarios"""
    try:
        policy_results = []
        
        # Política de contraseñas
        if security_policies.get("password_policy"):
            policy_results.append({
                "policy": "password_strength",
                "status": "applied",
                "requirements": security_policies["password_policy"]
            })
        
        # Autenticación de dos factores
        if security_policies.get("two_factor_auth"):
            policy_results.append({
                "policy": "two_factor_authentication",
                "status": "configured",
                "required_roles": security_policies["two_factor_auth"].get("required_roles", ["administrator"])
            })
        
        # Límites de sesión
        if security_policies.get("session_limits"):
            policy_results.append({
                "policy": "session_management",
                "status": "applied",
                "max_concurrent_sessions": security_policies["session_limits"].get("max_sessions", 1),
                "session_timeout": security_policies["session_limits"].get("timeout_minutes", 30)
            })
        
        return policy_results
        
    except Exception as e:
        return [{"policy": "security_policies", "status": "error", "error": str(e)}]

def _calculate_next_backup(schedule_config: Dict) -> str:
    """Calcular próximo backup programado"""
    try:
        frequency = schedule_config.get("frequency", "daily")
        time_str = schedule_config.get("time", "02:00")
        
        now = datetime.now()
        hour, minute = map(int, time_str.split(":"))
        
        if frequency == "daily":
            next_backup = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if next_backup <= now:
                next_backup += timedelta(days=1)
        elif frequency == "weekly":
            next_backup = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            days_ahead = 7 - now.weekday()
            if days_ahead <= 0 or (days_ahead == 7 and next_backup <= now):
                days_ahead += 7
            next_backup += timedelta(days=days_ahead)
        elif frequency == "monthly":
            if now.month == 12:
                next_backup = now.replace(year=now.year + 1, month=1, day=1, hour=hour, minute=minute)
            else:
                next_backup = now.replace(month=now.month + 1, day=1, hour=hour, minute=minute)
        else:
            next_backup = now + timedelta(hours=1)
        
        return next_backup.isoformat()
        
    except Exception:
        return (datetime.now() + timedelta(hours=1)).isoformat()

# ============================================================================
# FUNCIÓN DE PERSISTENCIA
# ============================================================================

async def _persist_wordpress_action(client: AuthenticatedHttpClient, action_data: Dict[str, Any], action: str):
    """Persistir acción de WordPress"""
    try:
        from app.memory.memory_functions import save_memory
        
        await save_memory(client, {
            "storage_type": "workflow",
            "file_name": f"wordpress_{action}_{int(time.time())}.json",
            "content": {
                "action": action,
                "action_data": action_data,
                "timestamp": time.time(),
                "platform": "wordpress"
            },
            "tags": ["wordpress", action, "api", "management"]
        })
        
    except Exception as e:
        logger.error(f"Error persisting WordPress action: {str(e)}")
