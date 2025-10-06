# 🔧 SOLUCIÓN DEFINITIVA: Error redirect_uri_mismatch

## ❌ El Problema

```
Error 400: redirect_uri_mismatch
```

Esto significa que Google Cloud Console **NO tiene configurado** el redirect_uri que estamos usando.

---

## ✅ SOLUCIÓN MÁS RÁPIDA (5 minutos)

### Paso 1: Ir a Google Cloud Console

Ve a: **https://console.cloud.google.com/apis/credentials**

### Paso 2: Encontrar tu Client ID

Busca en la lista:
```
1048351991771-ttrnpm1hsk95sarvu9beuquko6vud4q8
```

Haz clic en el **ícono de lápiz** (editar) a la derecha.

### Paso 3: Agregar Redirect URIs

En la sección **"URIs de redireccionamiento autorizados"**, haz clic en **"+ AGREGAR URI"**

Agrega ESTAS DOS URIs:

```
http://localhost:8080
http://localhost:8080/
```

### Paso 4: Guardar

Haz clic en **GUARDAR** en la parte inferior.

### Paso 5: Ejecutar Script

Espera 1 minuto y ejecuta:

```bash
python3 generar_token_automatico.py
```

---

## 🎯 SOLUCIÓN ALTERNATIVA (Sin modificar Google Console)

Si NO quieres o NO puedes modificar Google Cloud Console, usa este método:

### Opción A: Generar desde Google Ads API Center

1. Ve a: **https://ads.google.com/aw/apicenter**

2. Inicia sesión con tu cuenta de Google Ads

3. Haz clic en **"Generar token de actualización"**

4. Sigue las instrucciones

5. Copia el refresh_token que te da

6. Actualiza tu `.env`:
   ```bash
   GOOGLE_ADS_REFRESH_TOKEN=el_token_que_copiaste
   ```

### Opción B: Usar OAuth Playground de Google

1. Ve a: **https://developers.google.com/oauthplayground**

2. En **"Step 1 - Select & authorize APIs"**:
   - Busca: `Google Ads API v17`
   - Marca: `https://www.googleapis.com/auth/adwords`
   - Haz clic en **"Authorize APIs"**

3. En **"Step 2 - Exchange authorization code for tokens"**:
   - Haz clic en **"Exchange authorization code for tokens"**

4. En **"Step 3 - Configure request to API"**:
   - Verás el **refresh_token**
   - Cópialo

5. Actualiza tu `.env`:
   ```bash
   GOOGLE_ADS_REFRESH_TOKEN=el_token_que_copiaste
   ```

---

## 🚀 DESPUÉS DE OBTENER EL TOKEN

### 1. Actualizar .env local

```bash
nano .env
# Reemplaza la línea:
GOOGLE_ADS_REFRESH_TOKEN=tu_nuevo_token_aqui
```

### 2. Actualizar Azure App Service

```bash
# Ve a Azure Portal
https://portal.azure.com

# Navega a:
elitedynamicsapi > Configuración > Variables de aplicación

# Actualiza:
GOOGLE_ADS_REFRESH_TOKEN = tu_nuevo_token_aqui

# Haz clic en GUARDAR
```

### 3. Probar Localmente

```bash
# Reiniciar servidor
pkill -f uvicorn
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Probar Google Ads API
curl -s -X POST http://localhost:8000/api/v1/dynamics \
  -H "Content-Type: application/json" \
  -d '{"action":"googleads_list_accessible_customers","params":{}}' \
  | python3 -m json.tool
```

### 4. Deploy a Producción

```bash
# Commit del workflow arreglado
git add .github/workflows/azure_webapp_deploy.yml
git commit -m "🔧 FIX: Eliminar paso duplicado en workflow"
git push origin production

# Monitorear deployment
gh run watch
```

---

## 📋 RESUMEN

| Método | Tiempo | Dificultad | Recomendado |
|--------|--------|------------|-------------|
| Agregar redirect_uri | 5 min | Fácil | ⭐⭐⭐⭐⭐ |
| Google Ads API Center | 3 min | Muy fácil | ⭐⭐⭐⭐ |
| OAuth Playground | 5 min | Fácil | ⭐⭐⭐ |

---

## ❓ ¿Cuál método usar?

- **Si tienes acceso a Google Cloud Console**: Usa el método principal (agregar redirect_uri)
- **Si NO tienes acceso**: Usa Google Ads API Center
- **Si prefieres interface visual**: Usa OAuth Playground

Todos los métodos funcionan perfectamente. Elige el que te sea más cómodo.
