# 🔧 CONFIGURACIÓN DEL ASISTENTE OPENAI

## 📋 INSTRUCCIONES DE CONFIGURACIÓN

### 1. **CARGAR LA ESPECIFICACIÓN OpenAPI**
- Archivo: `TODAS_LAS_RUTAS_REALES.json`
- Ubicación: En el directorio raíz del proyecto
- Contiene: 22 rutas reales del backend con schemas válidos

### 2. **CONFIGURAR EL ASISTENTE**

#### 🎯 **Prompt del Sistema:**
```
Eres un asistente especializado en EliteDynamicsAPI. Tienes acceso a 476+ acciones automatizadas para tareas empresariales, marketing digital, gestión de datos y generación de contenido con IA.

REGLAS:
- Siempre usa POST a /api/v1/dynamics para ejecutar acciones
- Formato: {"action": "nombre_accion", "params": {}}
- Explica qué vas a hacer antes de ejecutar
- Si devuelve job_id, consulta estado con /api/v1/jobs/{job_id}
- Para Runway ML: está funcional y listo para generar videos

CAPACIDADES PRINCIPALES:
- 📧 Email y comunicación (Teams, Outlook)
- 📊 Gestión de datos (SharePoint, OneDrive, Power BI)
- 🤖 IA generativa (OpenAI, Gemini, Runway ML)
- 📈 Marketing digital (Meta, Google, LinkedIn, TikTok Ads)
- 📋 CRM y gestión (HubSpot, Notion, Planner)
- 🔍 Investigación web y análisis

Eres proactivo, educativo y siempre buscas optimizar procesos.
```

#### 🛠️ **Herramientas (Tools):**
- ✅ **Actions**: Habilitado (usa la especificación OpenAPI)
- ✅ **Code Interpreter**: Habilitado (para análisis de datos)
- ✅ **File Search**: Habilitado (para documentos)

#### 📁 **Archivos de Conocimiento:**
1. `MANUAL_ASISTENTE_OPENAI.md` - Manual completo
2. `TODAS_LAS_RUTAS_REALES.json` - Especificación API
3. Cualquier documentación adicional del proyecto

### 3. **CONFIGURACIÓN DE ACTIONS**

#### 🔗 **Importar Schema:**
1. Ve a Actions en tu asistente
2. Clic en "Import from OpenAPI"
3. Carga el archivo `TODAS_LAS_RUTAS_REALES.json`
4. Verifica que todas las 22 rutas se importen correctamente

#### ✅ **Verificar Configuración:**
- Base URL: `https://elitedynamicsapi.azurewebsites.net`
- Authentication: None (sin autenticación en el schema)
- Headers: Content-Type: application/json

### 4. **TESTING INICIAL**

#### 🧪 **Pruebas Básicas:**
```json
// 1. Health Check
{
  "action": "health_check",
  "params": {}
}

// 2. Verificar Runway
{
  "action": "runway_check_configuration", 
  "params": {}
}

// 3. Listar acciones disponibles
{
  "action": "listar_todas_las_acciones",
  "params": {}
}
```

## 🎯 FUNCIONALIDADES CLAVE

### 🎬 **RUNWAY ML (FUNCIONAL)**
- ✅ Estado: Operativo con nueva API key
- ✅ Text-to-Video: Crear videos desde descripciones
- ✅ Image-to-Video: Animar imágenes estáticas
- ✅ Task Status: Consultar progreso de generación

### 📊 **MICROSOFT 365**
- SharePoint: Gestión completa de sitios y archivos
- OneDrive: Subida y organización de documentos
- Teams: Mensajería y reuniones automatizadas
- Power BI: Creación de reportes y dashboards

### 📈 **MARKETING AUTOMATION**
- Meta Ads: Facebook e Instagram completo
- Google Ads: Campañas y optimización
- LinkedIn Ads: Marketing B2B profesional
- TikTok Ads: Campañas para audiencias jóvenes

### 🤖 **IA GENERATIVA**
- OpenAI: GPT para texto e imágenes
- Gemini: Capacidades avanzadas de Google
- Runway: Generación de videos con IA

## 🚨 RESOLUCIÓN DE PROBLEMAS

### ❌ **Errores Comunes:**

1. **Error 401 - Unauthorized**
   - Causa: Problema de configuración API
   - Solución: Verificar variables de entorno en Azure

2. **Error 400 - Bad Request**
   - Causa: Parámetros incorrectos
   - Solución: Revisar formato JSON y campos requeridos

3. **Error 500 - Internal Server Error**
   - Causa: Error interno del servidor
   - Solución: Reintentar después de unos segundos

### 🔍 **Diagnóstico:**
```json
// Verificar estado general
{
  "action": "system_status",
  "params": {}
}

// Verificar configuraciones específicas
{
  "action": "check_all_configurations",
  "params": {}
}
```

## 📈 EJEMPLOS DE USO AVANZADO

### 🎯 **Flujo Completo de Marketing:**
1. Investigar tendencias → `webresearch_buscar_informacion`
2. Crear contenido → `openai_generar_texto`
3. Generar video → `runway_text_to_video`
4. Crear campaña → `metaads_crear_campana`
5. Programar publicación → `teams_programar_mensaje`

### 📊 **Automatización Empresarial:**
1. Extraer datos → `powerbi_obtener_datos`
2. Generar análisis → `openai_analizar_datos`
3. Crear presentación → `sharepoint_crear_documento`
4. Enviar reporte → `correo_enviar_con_adjunto`

## 🎉 RESULTADO ESPERADO

Tu asistente podrá:
- ✅ Ejecutar cualquiera de las 476+ acciones disponibles
- ✅ Generar videos con Runway ML
- ✅ Automatizar procesos empresariales complejos
- ✅ Integrar múltiples plataformas en un solo flujo
- ✅ Proporcionar respuestas inteligentes y proactivas

## 📞 SOPORTE

Si encuentras problemas:
1. Verifica la configuración de Actions
2. Revisa los logs en Azure (si tienes acceso)
3. Prueba acciones básicas primero
4. Contacta al equipo técnico con detalles específicos

---

**¡Tu asistente está listo para transformar cualquier tarea manual en un proceso automatizado inteligente!** 🚀
