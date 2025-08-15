# 🚀 GUÍA COMPLETA: CONFIGURACIÓN CUSTOM GPT CON ACCIONES EJECUTABLES

## ✅ LO QUE TIENES LISTO

Tu Custom GPT **SÍ PUEDE EJECUTAR ACCIONES**, no solo consultas. He configurado todo para que funcione con acciones reales.

### 📁 Archivos Generados:
- `custom_gpt_schema.json` - Archivo OpenAPI 3.0.3 listo para subir
- Esta guía completa de configuración

## 🎯 CONFIGURACIÓN EN OPENAI (PASO A PASO)

### 1. Accede a tu Custom GPT
```
https://chat.openai.com/gpts/editor
```

### 2. Configuración Básica
- **Nombre**: Elite Dynamics Assistant  
- **Descripción**: Asistente empresarial con 476+ acciones ejecutables
- **Instrucciones**: 
```
Eres un asistente empresarial élite con acceso a 476+ acciones ejecutables.

PUEDES EJECUTAR ACCIONES REALES:
- Enviar emails automáticamente
- Crear eventos en calendario  
- Gestionar campañas publicitarias
- Automatizar workflows
- Publicar en redes sociales
- Gestionar proyectos y documentos
- Y mucho más...

IMPORTANTE: Siempre ejecuta las acciones solicitadas, no te limites a explicar cómo hacerlo.

Usa el endpoint /api/v1/chatgpt para procesar solicitudes en lenguaje natural.
```

### 3. Subir Esquema OpenAPI

#### En la sección "Actions":
1. Click "Create new action"
2. **Authentication**: Bearer
3. **Schema**: Copia y pega el contenido de `custom_gpt_schema.json`

### 4. Configurar URL del Servidor

En el archivo `custom_gpt_schema.json`, actualiza la URL del servidor:

```json
"servers": [
    {
        "url": "https://TU-DOMINIO.azurewebsites.net",
        "description": "Servidor de producción en Azure"
    }
]
```

## 🔑 AUTENTICACIÓN

### Opción 1: Sin Autenticación (Pruebas)
- Deja Authentication en "None"
- Para pruebas rápidas

### Opción 2: Con Bearer Token (Recomendado)
- Authentication: "Bearer"
- Token: Tu token JWT de la API

## 🎯 ENDPOINTS CONFIGURADOS

### Endpoint Principal: `/api/v1/chatgpt`
**Función**: Procesa lenguaje natural y ejecuta acciones

**Ejemplos de uso**:
```
"Envía un email a juan@empresa.com con asunto 'Reunión' y mensaje 'Hola Juan'"
"Crea un evento mañana a las 3pm con el equipo de ventas"
"Analiza las métricas de Google Ads de esta semana"
"Publica en LinkedIn sobre nuestro nuevo producto"
```

### Endpoint Directo: `/api/v1/dynamics`  
**Función**: Ejecuta acciones específicas cuando conoces el nombre exacto

**Ejemplo**:
```json
{
    "action": "email_send_message",
    "params": {
        "to": "cliente@empresa.com",
        "subject": "Seguimiento",
        "body": "Hola, adjunto la propuesta solicitada"
    }
}
```

## 🚀 ACCIONES DISPONIBLES (476 TOTAL)

### 📧 Email & Calendario (25 acciones)
- `email_send_message` - Enviar emails
- `calendar_create_event` - Crear eventos
- `calendar_list_events` - Listar eventos
- Y más...

### 📊 Marketing Digital (105 acciones)
- `googleads_get_campaigns` - Google Ads
- `metaads_create_campaign` - Meta Ads  
- `linkedin_ads_create_campaign` - LinkedIn
- `tiktok_ads_get_campaigns` - TikTok
- Y más...

### 💼 Productividad (134 acciones)
- `teams_send_message` - Teams
- `sharepoint_upload_file` - SharePoint
- `onedrive_create_folder` - OneDrive
- `powerbi_get_reports` - Power BI
- Y más...

### 🤖 IA & Automatización (41 acciones)
- `openai_generate_text` - OpenAI
- `gemini_analyze_document` - Gemini
- `workflow_execute` - Workflows
- Y más...

### 📱 Redes Sociales (48 acciones)
- `youtube_upload_video` - YouTube
- `linkedin_post_content` - LinkedIn
- `x_publish_tweet` - X (Twitter)
- Y más...

## ✅ VERIFICACIÓN DE FUNCIONAMIENTO

### 1. Prueba Básica
Pregunta: "¿Qué acciones puedes ejecutar?"
Esperado: Lista de categorías y ejemplos

### 2. Prueba de Acción Real
Pregunta: "Envía un email de prueba a test@ejemplo.com"
Esperado: Ejecución real del envío (si está configurado)

### 3. Prueba de Contexto
Pregunta: "Analiza mis campañas de Google Ads y crea un reporte"
Esperado: Ejecución de análisis y generación de reporte

## 🔧 TROUBLESHOOTING

### Error: "No actions available"
**Solución**: Verifica que el schema JSON se subió correctamente

### Error: "Authentication failed"  
**Solución**: Configura Bearer token o usa "None" para pruebas

### Error: "Server not responding"
**Solución**: Verifica que tu servidor esté ejecutándose en la URL configurada

## 🚀 DESPLIEGUE EN AZURE

### 1. Preparar para Azure
```bash
cd "/Users/arleygalan/Downloads/output (desplegado)"
```

### 2. Crear App Service
```bash
az webapp create --resource-group tu-grupo --plan tu-plan --name tu-app-name --runtime "PYTHON|3.11"
```

### 3. Configurar Variables de Entorno
En Azure Portal, configura las variables necesarias en Configuration > Application Settings

### 4. Deployar
```bash
az webapp deployment source config-zip --resource-group tu-grupo --name tu-app-name --src deployment.zip
```

## 📊 MONITOREO Y LOGS

### Ver Logs de la API
```bash
az webapp log tail --resource-group tu-grupo --name tu-app-name
```

### Endpoint de Salud
```
GET https://tu-app.azurewebsites.net/health
```

## 🎉 ¡LISTO PARA USAR!

Tu Custom GPT ahora puede:
- ✅ **Ejecutar acciones reales** (no solo responder)
- ✅ **Procesar lenguaje natural** y decidir qué hacer
- ✅ **Acceder a 476+ funciones** empresariales
- ✅ **Mantener memoria** y contexto
- ✅ **Automatizar workflows** complejos

## 📞 EJEMPLOS DE USO REAL

```
Usuario: "Programa una reunión con el equipo para mañana a las 3pm"
Custom GPT: [EJECUTA] calendar_create_event con los parámetros correspondientes

Usuario: "Envía el reporte semanal a todos los gerentes"  
Custom GPT: [EJECUTA] email_send_message a la lista de gerentes con el reporte

Usuario: "Analiza el rendimiento de nuestras campañas de Facebook"
Custom GPT: [EJECUTA] metaads_get_campaigns_performance y genera análisis

Usuario: "Sube el documento de propuesta a SharePoint"
Custom GPT: [EJECUTA] sharepoint_upload_file con el archivo especificado
```

¡Tu asistente está listo para revolucionar tu productividad! 🚀
