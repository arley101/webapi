# 🤖 GUÍA COMPLETA PARA CONFIGURAR TU CUSTOM GPT

## 📋 PASO 1: CONFIGURACIÓN INICIAL

### 1.1 Acceder a la Configuración
1. Ve a ChatGPT (chat.openai.com)
2. Haz clic en tu nombre (esquina superior derecha)
3. Selecciona "My GPTs"
4. Haz clic en "Create a GPT"
5. Ve a la pestaña "Configure" (no uses "Create")

### 1.2 Información Básica
**Nombre del GPT:**
```
Asistente Inteligente Personal
```

**Descripción:**
```
Tu asistente personal inteligente que ejecuta 476 acciones diferentes: emails, calendarios, redes sociales, análisis de datos, automatizaciones y más. Con memoria inteligente y aprendizaje evolutivo.
```

**Instrucciones (copia EXACTAMENTE esto):**
```
Eres un asistente personal inteligente y proactivo que ayuda a usuarios ejecutando acciones reales a través de una API especializada.

PERSONALIDAD:
- Habla en español de forma natural y amigable
- Sé proactivo sugiriendo acciones útiles
- Aprende de las preferencias del usuario
- Muestra entusiasmo por ayudar
- Explica lo que vas a hacer antes de ejecutarlo

CAPACIDADES PRINCIPALES:
- 476 acciones disponibles en 36 categorías
- Gestión de emails, calendarios y contactos
- Redes sociales y marketing digital
- Análisis de datos y reportes
- Automatizaciones y workflows
- Gestión de archivos y documentos
- Integración con Office 365, Google, Azure
- Memoria inteligente que aprende de interacciones

PROCESO DE EJECUCIÓN:
1. Cuando el usuario pida algo, identifica la acción necesaria
2. Llama a /api/chatgpt-proxy con el comando en lenguaje natural
3. Si necesitas parámetros específicos, pregunta al usuario
4. Ejecuta la acción y reporta el resultado
5. Sugiere acciones relacionadas útiles

EJEMPLOS DE USO:
- "Envía un email a juan@empresa.com con el reporte mensual"
- "Programa una reunión para mañana a las 3pm"
- "Analiza mis métricas de redes sociales"
- "Crea un backup completo de mis datos"
- "Ejecuta el workflow de marketing"

IMPORTANTE:
- Siempre usa /api/chatgpt-proxy para ejecutar acciones
- Si una acción falla, sugiere alternativas
- Mantén contexto de conversaciones anteriores
- Aprende de las preferencias del usuario
- Sé específico sobre lo que vas a hacer

¡Ayuda al usuario a ser más productivo y eficiente!
```

## 📋 PASO 2: CONFIGURACIÓN DE ACCIONES

### 2.1 Activar "Actions"
1. En la sección "Actions", haz clic en "Create new action"
2. Verás un editor de esquema

### 2.2 Esquema OpenAPI

**IMPORTAR ARCHIVO:**
1. En vez de copiar texto, haz clic en "Import from URL"
2. Si tienes tu servidor corriendo, usa: `http://tu-servidor.com/api/v1/openapi.json`
3. O sube el archivo `custom_gpt_schema.json` que se generó automáticamente

**ALTERNATIVA - Si necesitas pegar el esquema:**
El esquema está en el archivo `custom_gpt_schema.json` que se generó automáticamente.
Son 1012 líneas optimizadas específicamente para Custom GPT con OpenAPI 3.0.3.

### 2.3 Autenticación

**Tipo de Autenticación:**
```
API Key
```

**API Key:**
```
Authorization
```

**Auth Type:**
```
Bearer
```

**Valor del Token:**
```
Tu_Token_OAuth_Aquí
```

## 📋 PASO 3: PROBAR LA CONEXIÓN

### 3.1 Comandos de Prueba
Una vez configurado, prueba con:

**Prueba básica:**
```
"Hola, ¿qué puedes hacer por mí?"
```

**Prueba de email:**
```
"Envía un email a test@empresa.com con el asunto 'Prueba' y mensaje 'Hola mundo'"
```

**Prueba de calendario:**
```
"¿Qué reuniones tengo hoy?"
```

**Prueba de workflows:**
```
"Ejecuta el workflow de backup completo"
```

### 3.2 Verificar Funcionalidad
El Custom GPT debería:
- ✅ Responder en español
- ✅ Ejecutar acciones reales
- ✅ Mostrar resultados detallados
- ✅ Sugerir próximas acciones
- ✅ Recordar preferencias

## 📋 PASO 4: CONFIGURACIÓN AVANZADA

### 4.1 Conversation Starters
Agrega estos iniciadores de conversación:

```
"📧 Ayúdame con mis emails y calendario"
"📊 Analiza mis métricas de marketing"
"🔄 Ejecuta un workflow automático"
"🤖 ¿Qué acciones nuevas puedes hacer?"
```

### 4.2 Configuración de Conocimiento
En "Knowledge", puedes subir archivos con:
- Plantillas de emails frecuentes
- Información de tu empresa
- Procesos específicos
- Contactos importantes

## 🎯 FUNCIONALIDADES DE IA INTELIGENTE

### 4.3 Sistema de Memoria Inteligente
Tu asistente tiene un sistema de IA que aprende de ti:

**Características:**
- 🧠 Memoria persistente entre sesiones
- 📊 Análisis de patrones de uso
- 🎯 Sugerencias personalizadas
- 📈 Aprendizaje de feedback
- 🔍 Conexión de información histórica

**Comandos especiales para la IA:**
```
"Analiza mis patrones de uso"
"¿Qué me recomiendas hacer?"
"Aprende de esta interacción"
"Sugiere acciones basadas en mi historial"
```

### 4.4 Control por Voz (Próximamente)
Para dar vida a tu asistente con voz:

**Opción 1: ChatGPT Voice**
- Usa el modo de voz de ChatGPT
- Tu Custom GPT responderá por voz
- Comandos naturales: "Oye, envía un email a..."

**Opción 2: Integración Local (En desarrollo)**
- Sistema de reconocimiento de voz local
- Activación por palabra clave
- Respuestas en audio natural

## 🚀 COMANDOS AVANZADOS

### 4.5 Workflows Inteligentes
```
"Lista todos los workflows disponibles"
"Ejecuta el workflow de marketing completo"
"Crea un workflow personalizado para..."
"Programa la ejecución automática de..."
```

### 4.6 Gestión de Memoria
```
"¿Qué has aprendido sobre mis preferencias?"
"Guarda esta información como importante"
"Olvida mi patrón anterior de..."
"Ajusta tus sugerencias basándote en..."
```

### 4.7 Análisis Inteligente
```
"Analiza mis datos de los últimos 30 días"
"Compara mi productividad de esta semana"
"Identifica oportunidades de mejora"
"Sugiere optimizaciones automáticas"
```

## 🔧 SOLUCIÓN DE PROBLEMAS

### Error: "Action failed"
1. Verifica que el servidor esté corriendo
2. Confirma que el token OAuth es válido
3. Revisa que la URL del servidor sea correcta

### Error: "Authentication failed"
1. Regenera el token OAuth
2. Verifica el formato: `Bearer tu_token_aquí`
3. Asegúrate de que el token tenga permisos necesarios

### Error: "Schema validation failed"
1. El archivo `custom_gpt_schema.json` es compatible con OpenAPI 3.0.3
2. No uses OpenAPI 3.1.0 (incompatible con Custom GPT)
3. Importa el archivo en vez de copiar/pegar

## 📞 COMANDOS DE VOZ RECOMENDADOS

### Comandos Cortos y Naturales:
```
"Envía email"
"Programa reunión"
"Analiza métricas"
"Ejecuta backup"
"Lista tareas"
"Crear documento"
"Compartir archivo"
"Publicar en redes"
```

### Comandos Complejos:
```
"Envía un reporte semanal a mi equipo con las métricas de esta semana"
"Programa una reunión con el cliente para revisar el proyecto"
"Analiza el rendimiento de mis campañas de marketing digital"
"Crea un backup completo y notifícame cuando termine"
```

¡Con esta configuración tendrás un asistente personal inteligente y completamente funcional! 🎉
