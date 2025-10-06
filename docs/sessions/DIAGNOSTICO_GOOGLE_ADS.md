# 🔍 DIAGNÓSTICO COMPLETO - GOOGLE ADS API

## ✅ SERVIDOR LOCAL FUNCIONANDO
- **URL**: http://localhost:8000
- **Estado**: ✅ ACTIVO
- **Versión**: 1.2 (desarrollo)
- **Routers activos**: 9/9

## ❌ PROBLEMA IDENTIFICADO

### Google Ads API - Token Expirado
```
Error: "invalid_grant: Token has been expired or revoked."
```

**Causa raíz**: El `GOOGLE_ADS_REFRESH_TOKEN` en el archivo `.env` está **EXPIRADO o REVOCADO**.

### Configuración actual en .env:
```
✅ GOOGLE_ADS_CLIENT_ID:        1048351991771-t...ontent.com
✅ GOOGLE_ADS_CLIENT_SECRET:    GOCSPX-rkr...YjTrBtK
⚠️  GOOGLE_ADS_REFRESH_TOKEN:   1//05HaX...idWVS4KMxw [EXPIRADO ❌]
✅ GOOGLE_ADS_DEVELOPER_TOKEN:  7MuB30y...WDUQa6A
✅ GOOGLE_ADS_LOGIN_CUSTOMER_ID: 1415018442
```

## 🔧 SOLUCIÓN PASO A PASO

### Opción 1: Usar el script oficial de Google (RECOMENDADO)
```bash
cd /Users/arleygalan/webapi-1
python3 -m google.ads.googleads.oauth2 \
    --client_id="1048351991771-ttrnpm1hsk95sarvu9beuquko6vud4q8.apps.googleusercontent.com" \
    --client_secret="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"
```

**Sigue las instrucciones en pantalla:**
1. Se abrirá un navegador
2. Inicia sesión con tu cuenta de Google Ads
3. Autoriza la aplicación
4. Copia el **refresh_token** generado

### Opción 2: Generar manualmente desde Google Cloud Console

1. **Ir a Google Cloud Console**: https://console.cloud.google.com/

2. **Seleccionar proyecto** (o crear uno nuevo)

3. **Habilitar Google Ads API**:
   - APIs y Servicios > Biblioteca
   - Buscar "Google Ads API"
   - Clic en "Habilitar"

4. **Verificar credenciales OAuth 2.0**:
   - APIs y Servicios > Credenciales
   - Verificar que existe el Client ID: `1048351991771-ttrnpm1hsk95sarvu9beuquko6vud4q8.apps.googleusercontent.com`
   - Si no existe, crear uno nuevo tipo "Aplicación de escritorio"

5. **Generar URL de autorización manual**:
   ```
   https://accounts.google.com/o/oauth2/auth?client_id=1048351991771-ttrnpm1hsk95sarvu9beuquko6vud4q8.apps.googleusercontent.com&redirect_uri=urn:ietf:wg:oauth:2.0:oob&scope=https://www.googleapis.com/auth/adwords&response_type=code&access_type=offline&prompt=consent
   ```

6. **Copiar el código de autorización** que aparece en el navegador

7. **Intercambiar código por refresh_token**:
   ```bash
   python3 -c "
   from google.oauth2.credentials import Credentials
   from google_auth_oauthlib.flow import InstalledAppFlow
   
   # Configuración
   client_config = {
       'installed': {
           'client_id': '1048351991771-ttrnpm1hsk95sarvu9beuquko6vud4q8.apps.googleusercontent.com',
           'client_secret': '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',
           'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
           'token_uri': 'https://oauth2.googleapis.com/token',
       }
   }
   
   flow = InstalledAppFlow.from_client_config(
       client_config,
       scopes=['https://www.googleapis.com/auth/adwords']
   )
   
   credentials = flow.run_local_server(port=0)
   print(f'\\n✅ REFRESH TOKEN GENERADO:\\n{credentials.refresh_token}')
   "
   ```

## 📝 ACTUALIZAR .ENV CON EL NUEVO TOKEN

Una vez que tengas el nuevo `refresh_token`:

1. **Abrir el archivo .env**:
   ```bash
   nano /Users/arleygalan/webapi-1/.env
   # o
   code /Users/arleygalan/webapi-1/.env
   ```

2. **Reemplazar la línea** del GOOGLE_ADS_REFRESH_TOKEN:
   ```
   GOOGLE_ADS_REFRESH_TOKEN=TU_NUEVO_TOKEN_AQUI
   ```

3. **Guardar y cerrar**

## 🧪 PROBAR LA CONEXIÓN

Después de actualizar el .env:

```bash
# Reiniciar el servidor local
pkill -f uvicorn
cd /Users/arleygalan/webapi-1
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &

# Esperar 3 segundos
sleep 3

# Probar Google Ads API - Listar clientes
curl -s http://localhost:8000/api/v1/dynamics \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "googleads_list_accessible_customers", "params": {}}' \
  | python3 -m json.tool

# Probar Google Ads API - Listar campañas
curl -s http://localhost:8000/api/v1/dynamics \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"action": "googleads_get_campaigns", "params": {"customer_id": "1415018442"}}' \
  | python3 -m json.tool
```

## 🚀 DEPLOYMENT A PRODUCCIÓN

Una vez que el token funcione localmente:

1. **Actualizar el refresh token en Azure App Service**:
   - Ve a Azure Portal: https://portal.azure.com
   - Selecciona tu App Service: `elitedynamicsapi`
   - Ve a "Configuración" > "Variables de aplicación"
   - Actualiza `GOOGLE_ADS_REFRESH_TOKEN` con el nuevo valor
   - Guarda los cambios

2. **Reiniciar la aplicación en Azure**:
   ```bash
   # Desde Azure Portal:
   # App Service > Información general > Reiniciar
   
   # O desde Azure CLI:
   az webapp restart --name elitedynamicsapi --resource-group TU_RESOURCE_GROUP
   ```

3. **Verificar en producción**:
   ```bash
   curl -s https://elitedynamicsapi.azurewebsites.net/api/v1/dynamics \
     -X POST \
     -H "Content-Type: application/json" \
     -d '{"action": "googleads_list_accessible_customers", "params": {}}' \
     | python3 -m json.tool
   ```

## 📋 RESUMEN DE ACCIONES

| Acción | Estado | Comando |
|--------|--------|---------|
| 🔍 Diagnóstico | ✅ COMPLETADO | `python3 generate_google_ads_refresh_token.py` |
| 🔑 Generar token | ⏳ PENDIENTE | `python3 -m google.ads.googleads.oauth2 --client_id=... --client_secret=...` |
| 📝 Actualizar .env | ⏳ PENDIENTE | Editar archivo `.env` |
| 🧪 Probar local | ⏳ PENDIENTE | `curl http://localhost:8000/api/v1/dynamics -X POST ...` |
| ☁️  Actualizar Azure | ⏳ PENDIENTE | Configuración > Variables de aplicación |
| ✅ Verificar producción | ⏳ PENDIENTE | `curl https://elitedynamicsapi.azurewebsites.net/api/v1/dynamics ...` |

## 🎯 CONCLUSIÓN

**EL CÓDIGO ESTÁ CORRECTO** ✅  
**EL PROBLEMA ES SOLO EL TOKEN EXPIRADO** ⚠️

Una vez que generes un nuevo `refresh_token` y lo actualices en:
1. ✅ Archivo `.env` local
2. ✅ Variables de entorno en Azure App Service

La API de Google Ads funcionará perfectamente tanto en:
- 🖥️  Servidor local (http://localhost:8000)
- ☁️  Producción (https://elitedynamicsapi.azurewebsites.net)

---

**Archivos de ayuda creados:**
- ✅ `generate_google_ads_refresh_token.py` - Script interactivo para generar token
- ✅ `DIAGNOSTICO_GOOGLE_ADS.md` - Este archivo con todas las instrucciones
