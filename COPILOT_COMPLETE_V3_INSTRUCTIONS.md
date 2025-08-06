[
# 🔍 INSTRUCCIONES PARA GITHUB COPILOT - ANÁLISIS Y FUSIÓN V3

## 🎯 OBJETIVO
Analizar el código existente en producción y los nuevos archivos V3 creados para determinar si son compatibles y cómo fusionarlos correctamente.

## 📋 TU TAREA COPILOT:

### 1. ANALIZAR EL CÓDIGO ACTUAL EN PRODUCCIÓN

Por favor revisa estos archivos críticos del sistema actual:
- `/app/main.py` - Punto de entrada principal
- `/app/core/action_mapper.py` - Las 353 acciones existentes
- `/app/core/auth_manager.py` - Sistema de autenticación
- `/app/actions/wordpress_actions.py` - Ejemplo de módulo de acciones
- `/app/api/routes/dynamics_actions.py` - Router principal
- `/.env` - Variables de entorno (NO modificar)

### 2. ANALIZAR LOS NUEVOS ARCHIVOS V3

Revisa estos archivos nuevos en la rama `integrate-proxy-into-backend`:
- `/app/core/v3/state_manager.py` - Gestión de memoria persistente
- `/app/core/v3/event_bus.py` - Sistema de eventos
- `/app/core/v3/audit_manager.py` - Auditoría con Notion
- `/app/core/v3/orchestrator.py` - Orquestador principal
- `/app/routers/v3/orchestrate.py` - Nuevos endpoints
- `/app/middleware/audit_middleware.py` - Middleware de auditoría

### 3. VERIFICAR COMPATIBILIDAD

#### 3.1 Verificar que NO se rompen las 353 acciones
- ¿El nuevo orchestrator puede ejecutar TODAS las acciones existentes?
- ¿Se mantienen los mismos parámetros y respuestas?
- ¿La autenticación sigue funcionando igual?

#### 3.2 Verificar la autenticación de WordPress
El sistema actual usa 3 métodos de autenticación para WordPress:
1. JWT Token
2. Application Password  
3. Basic Auth (fallback)

**PREGUNTA CRÍTICA**: ¿Los nuevos módulos V3 respetan estos 3 métodos?

#### 3.3 Verificar variables de entorno
- NO se deben agregar nuevas variables de entorno obligatorias
- Las existentes deben seguir funcionando igual

### 4. IDENTIFICAR CONFLICTOS

Lista todos los conflictos encontrados:
- [ ] Conflictos en imports
- [ ] Conflictos en rutas/endpoints
- [ ] Conflictos en autenticación
- [ ] Conflictos en estructura de respuestas
- [ ] Conflictos en manejo de errores

### 5. GENERAR PLAN DE FUSIÓN

Crea un plan paso a paso para fusionar V3 con el código actual:

```python
# EJEMPLO DE ESTRUCTURA ESPERADA
merge_plan = {
    "phase_1": {
        "description": "Preparar el código base",
        "steps": [
            "1. Backup del código actual",
            "2. Verificar que todos los tests pasan",
            "3. Documentar el estado actual"
        ]
    },
    "phase_2": {
        "description": "Integrar módulos V3",
        "steps": [
            "1. Copiar archivos V3 sin modificar main.py",
            "2. Verificar imports",
            "3. Ejecutar tests unitarios"
        ]
    },
    "phase_3": {
        "description": "Activar V3",
        "steps": [
            "1. Actualizar main.py con imports V3",
            "2. Agregar middlewares",
            "3. Incluir nuevo router"
        ]
    }
}
```

### 6. CREAR SUITE DE TESTS

Genera tests para verificar que TODO funciona:

```python
# tests/test_v3_compatibility.py
def test_all_actions_still_work():
    """Las 353 acciones deben seguir funcionando"""
    pass

def test_wordpress_auth_methods():
    """Los 3 métodos de auth de WordPress deben funcionar"""
    pass

def test_no_breaking_changes():
    """No debe haber cambios breaking"""
    pass
```

### 7. DOCUMENTAR RIESGOS

Lista TODOS los riesgos identificados:
1. **Riesgo**: [Descripción]
   **Mitigación**: [Cómo evitarlo]

### 8. GENERAR REPORTE FINAL

Crea un archivo `V3_COMPATIBILITY_REPORT.md` con:
1. ✅ Qué es compatible
2. ⚠️ Qué necesita ajustes
3. ❌ Qué NO es compatible
4. 📋 Plan de acción detallado
5. 🧪 Tests requeridos
6. ⏱️ Tiempo estimado

## ⚠️ REGLAS CRÍTICAS:

1. **NO MODIFICAR** las 353 acciones existentes
2. **NO CAMBIAR** la autenticación de WordPress
3. **NO AGREGAR** Docker ni cambiar el despliegue
4. **NO TOCAR** las variables de entorno
5. **MANTENER** compatibilidad total con el código actual

## 📊 ENTREGABLE ESPERADO:

Un reporte completo que me diga:
- ¿Es seguro fusionar V3 con el código actual?
- ¿Qué podría romperse?
- ¿Cómo probarlo antes de producción?
- ¿Cuál es el plan paso a paso?

---
**NOTA**: NO ejecutes ningún cambio. Solo analiza y reporta.
]
