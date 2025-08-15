# Asistente Inteligente - API de Automatización

API robusta para automatización empresarial con integraciones múltiples.

## 🚀 Características

- **512 acciones automatizadas** completamente funcionales
- **Integraciones empresariales**: Microsoft 365, Google Workspace, Azure, AWS
- **Social Media**: LinkedIn, Meta, TikTok, X (Twitter), YouTube
- **CRM & Marketing**: HubSpot, Notion, WordPress
- **IA & ML**: OpenAI, Gemini, análisis inteligente
- **Comunicación**: Teams, WhatsApp bots
- **Gestión**: Calendarios, tareas, formularios

## 📦 Instalación

```bash
# Clonar repositorio
git clone [URL_DEL_REPO]
cd assistant_clean

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp ENV_VARIABLES.md .env
# Editar .env con tus credenciales

# Ejecutar
python main.py
```

## 🛠️ Despliegue

Ver `DEPLOYMENT_GUIDE_NO_DOCKER.md` para instrucciones detalladas.

## 📚 Documentación

- `INTEGRATION_GUIDE.md` - Guía de integraciones
- `ENV_VARIABLES.md` - Variables de entorno requeridas
- `DEPLOYMENT_GUIDE_NO_DOCKER.md` - Guía de despliegue

## 🎯 Endpoints Principales

- `/health` - Estado del sistema
- `/chat` - Interface de chat
- `/actions` - Listado de acciones disponibles
- `/execute` - Ejecutar acciones específicas

## 🔧 Tecnologías

- **Backend**: FastAPI + Python 3.11+
- **Base de datos**: Configuración flexible
- **Autenticación**: Azure AD, OAuth2
- **Infraestructura**: Azure App Service compatible

## 📄 Licencia

Proyecto privado - Todos los derechos reservados
