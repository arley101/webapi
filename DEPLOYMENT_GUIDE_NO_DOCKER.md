# 🚀 DESPLIEGUE EN AZURE SIN DOCKER

## 🎯 OPCIÓN PRINCIPAL: AZURE APP SERVICE

Tu aplicación se desplegará en **Azure App Service** (similar a Heroku), que es perfecto para aplicaciones Python/FastAPI **SIN necesidad de Docker**.

## 📋 PASOS PARA DESPLEGAR:

### 1. **INSTALAR AZURE CLI** (si no lo tienes)
```bash
# En macOS
brew install azure-cli

# O descargar desde: https://aka.ms/installazureclimacos
```

### 2. **INSTALAR AZURE DEVELOPER CLI**
```bash
# En macOS
brew tap azure/azd && brew install azd

# O descargar desde: https://aka.ms/install-azd.sh
```

### 3. **INICIAR SESIÓN EN AZURE**
```bash
az login
azd auth login
```

### 4. **CONFIGURAR VARIABLES DE ENTORNO**
```bash
# Navegar a tu proyecto
cd "/Users/arleygalan/Downloads/output (desplegado)"

# Configurar variables (usa las que ya tienes)
azd env set AZURE_OPENAI_API_KEY "tu-clave-actual"
azd env set AZURE_OPENAI_ENDPOINT "tu-endpoint-actual"
azd env set SHAREPOINT_CLIENT_ID "tu-client-id"
azd env set SHAREPOINT_SITE_ID "tu-site-id"
azd env set NOTION_TOKEN "tu-notion-token"
azd env set GEMINI_API_KEY "tu-gemini-key"  # Opcional
```

### 5. **DESPLEGAR CON UN COMANDO**
```bash
azd up
```

¡Y LISTO! Azure se encarga de todo automáticamente:
- ✅ Crea el App Service
- ✅ Instala Python 3.11
- ✅ Instala tus dependencias
- ✅ Configura las variables de entorno
- ✅ Inicia tu aplicación
- ✅ Te da una URL pública

## 🌐 LO QUE OBTIENES:

```
https://tu-asistente-inteligente.azurewebsites.net
├── /api/v1/docs (Swagger UI)
├── /api/v1/dynamics (Tus 405 acciones)
├── /api/v1/chatgpt (ChatGPT Proxy)
└── /api/v1/intelligent-assistant (Asistente IA)
```

## 💰 COSTOS:

- **Plan B1 (Basic)**: ~$13 USD/mes
- **Plan F1 (Gratuito)**: $0/mes (con limitaciones)

## 🔧 CAMBIAR A PLAN GRATUITO:

Si quieres probarlo gratis primero, edita el archivo:
`infra/resources-appservice.bicep` línea 32:

```bicep
sku: {
  name: 'F1'     // Cambia de 'B1' a 'F1'
  tier: 'Free'   // Cambia de 'Basic' a 'Free'
}
```

## ⚡ COMANDOS ÚTILES:

```bash
# Ver el estado del despliegue
azd show

# Ver logs en tiempo real
azd logs

# Actualizar la aplicación
azd deploy

# Eliminar todo (si quieres)
azd down
```

## 🎉 RESULTADO FINAL:

Tu EliteDynamicsAPI con Asistente Inteligente estará disponible públicamente en Azure, **sin Docker, sin complicaciones**.

---

**¿Listo para desplegarlo?** Solo ejecuta: `azd up` 🚀
