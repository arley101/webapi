# scripts/migrate_oauth_to_unified.py
"""
🔄 SCRIPT DE MIGRACIÓN OAUTH
Actualiza automáticamente todas las acciones que usan módulos OAuth obsoletos
para usar el nuevo sistema unificado.
"""

import os
import re
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Patrones a reemplazar
MIGRATION_PATTERNS = [
    # Google Auth patterns
    (
        r'from\s+app\.services\.auth\.google_auth\s+import\s+.*',
        'from app.core.unified_oauth_manager import unified_oauth'
    ),
    (
        r'from\s+app\.services\.auth\.youtube_auth\s+import\s+.*',
        'from app.core.unified_oauth_manager import unified_oauth'
    ),
    (
        r'GoogleServicesClient\(\)',
        'unified_oauth'
    ),
    (
        r'YouTubeClient\(\)',
        'unified_oauth'
    ),
    (
        r'\.get_google_service\(',
        '.get_google_service('
    ),
    # Métodos de auth manager obsoletos
    (
        r'get_auth_client\(\)\.get_google_access_token\(',
        'await unified_oauth.get_access_token("google"'
    ),
    (
        r'get_auth_client\(\)\.get_meta_access_token\(',
        'await unified_oauth.get_access_token("meta"'
    ),
]

def migrate_file(file_path: Path) -> bool:
    """Migra un archivo individual"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        modified = False
        
        # Aplicar patrones de migración
        for pattern, replacement in MIGRATION_PATTERNS:
            new_content = re.sub(pattern, replacement, content)
            if new_content != content:
                content = new_content
                modified = True
        
        # Si se modificó, escribir el archivo
        if modified:
            # Crear backup
            backup_path = file_path.with_suffix(file_path.suffix + '.bak')
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(original_content)
            
            # Escribir versión migrada
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"✅ Migrado: {file_path} (backup: {backup_path})")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"❌ Error migrando {file_path}: {e}")
        return False

def migrate_actions_directory():
    """Migra todos los archivos en el directorio actions/"""
    actions_dir = Path("app/actions")
    
    if not actions_dir.exists():
        logger.error(f"Directorio no encontrado: {actions_dir}")
        return
    
    migrated_files = []
    total_files = 0
    
    for file_path in actions_dir.glob("*.py"):
        if file_path.name.startswith("__"):
            continue
            
        total_files += 1
        if migrate_file(file_path):
            migrated_files.append(file_path.name)
    
    logger.info(f"📊 Migración completada:")
    logger.info(f"   - Archivos procesados: {total_files}")
    logger.info(f"   - Archivos migrados: {len(migrated_files)}")
    logger.info(f"   - Archivos migrados: {', '.join(migrated_files)}")

def create_unified_import_guide():
    """Crea una guía de referencia para el nuevo sistema"""
    guide_content = """# 🔧 GUÍA DE MIGRACIÓN AL SISTEMA OAUTH UNIFICADO

## ❌ OBSOLETO (No usar más):
```python
from app.services.auth.google_auth import GoogleServicesClient
from app.services.auth.youtube_auth import YouTubeClient
from app.core.auth_manager import get_auth_client

client = GoogleServicesClient()
youtube_client = YouTubeClient()
token = get_auth_client().get_google_access_token()
```

## ✅ NUEVO SISTEMA UNIFICADO:
```python
from app.core.unified_oauth_manager import unified_oauth

# Obtener tokens (automático con cache y refresh)
google_token = await unified_oauth.get_access_token("google")
youtube_token = await unified_oauth.get_access_token("youtube") 
meta_token = await unified_oauth.get_access_token("meta")

# Obtener servicios Google ya configurados
gmail = unified_oauth.get_google_service("gmail")
calendar = unified_oauth.get_google_service("calendar")
youtube = unified_oauth.get_google_service("youtube")

# Headers para requests HTTP
headers = await unified_oauth.get_headers("google")

# Estado de tokens
status = unified_oauth.get_token_status()

# Refresh masivo de tokens
results = await unified_oauth.refresh_all_tokens()
```

## 🎯 SERVICIOS SOPORTADOS:
- `google` - Gmail, Calendar, Drive, Sheets, Google Ads
- `youtube` - YouTube Data API v3
- `meta` - Facebook/Meta Ads API
- `linkedin` - LinkedIn Ads API
- `tiktok` - TikTok Ads API

## 🚀 BENEFICIOS:
- ✅ Refresh automático en background
- ✅ Cache inteligente con expiración
- ✅ Un solo punto de configuración
- ✅ Manejo de errores unificado  
- ✅ Sin duplicación de código
- ✅ Fallbacks automáticos
"""
    
    with open("OAUTH_MIGRATION_GUIDE.md", "w", encoding='utf-8') as f:
        f.write(guide_content)
    
    logger.info("📖 Guía de migración creada: OAUTH_MIGRATION_GUIDE.md")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    
    print("🔄 Iniciando migración al sistema OAuth unificado...")
    
    # Migrar archivos
    migrate_actions_directory()
    
    # Crear guía
    create_unified_import_guide()
    
    print("✅ Migración completada!")
    print("📖 Revisa OAUTH_MIGRATION_GUIDE.md para la documentación completa")
    print("🔍 Los archivos originales están respaldados con extensión .bak")