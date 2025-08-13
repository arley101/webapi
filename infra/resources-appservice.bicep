param environmentName string
param location string = resourceGroup().location
param resourceToken string
param tags object

// Variables
var abbrs = loadJsonContent('./abbreviations.json')

// Log Analytics Workspace
resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
  location: location
  tags: tags
  properties: {
    retentionInDays: 30
    sku: {
      name: 'PerGB2018'
    }
  }
}

// App Service Plan
resource appServicePlan 'Microsoft.Web/serverfarms@2022-03-01' = {
  name: '${abbrs.webServerFarms}${resourceToken}'
  location: location
  tags: tags
  sku: {
    name: 'B1'  // Basic tier - puedes cambiar a 'F1' para gratuito
    tier: 'Basic'
  }
  kind: 'linux'
  properties: {
    reserved: true  // Required for Linux
  }
}

// User Assigned Managed Identity
resource userIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
  location: location
  tags: tags
}

// App Service (Web App)
resource appService 'Microsoft.Web/sites@2022-03-01' = {
  name: '${abbrs.webSitesAppService}${resourceToken}'
  location: location
  tags: tags
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${userIdentity.id}': {}
    }
  }
  properties: {
    serverFarmId: appServicePlan.id
    httpsOnly: true
    siteConfig: {
      linuxFxVersion: 'PYTHON|3.11'
      alwaysOn: true
      appSettings: [
        {
          name: 'SCM_DO_BUILD_DURING_DEPLOYMENT'
          value: 'true'
        }
        {
          name: 'AZURE_OPENAI_API_KEY'
          value: '@Microsoft.KeyVault(SecretUri=https://kv-${resourceToken}.vault.azure.net/secrets/azure-openai-api-key/)'
        }
        {
          name: 'AZURE_OPENAI_ENDPOINT'
          value: '@Microsoft.KeyVault(SecretUri=https://kv-${resourceToken}.vault.azure.net/secrets/azure-openai-endpoint/)'
        }
        {
          name: 'SHAREPOINT_CLIENT_ID'
          value: '@Microsoft.KeyVault(SecretUri=https://kv-${resourceToken}.vault.azure.net/secrets/sharepoint-client-id/)'
        }
        {
          name: 'SHAREPOINT_SITE_ID'
          value: '@Microsoft.KeyVault(SecretUri=https://kv-${resourceToken}.vault.azure.net/secrets/sharepoint-site-id/)'
        }
        {
          name: 'NOTION_TOKEN'
          value: '@Microsoft.KeyVault(SecretUri=https://kv-${resourceToken}.vault.azure.net/secrets/notion-token/)'
        }
        {
          name: 'GEMINI_API_KEY'
          value: '@Microsoft.KeyVault(SecretUri=https://kv-${resourceToken}.vault.azure.net/secrets/gemini-api-key/)'
        }
      ]
      cors: {
        allowedOrigins: ['*']
        supportCredentials: false
      }
    }
  }
}

// Key Vault para secretos
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: 'kv-${resourceToken}'
  location: location
  tags: tags
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenant().tenantId
    accessPolicies: [
      {
        tenantId: tenant().tenantId
        objectId: userIdentity.properties.principalId
        permissions: {
          secrets: ['get', 'list']
        }
      }
    ]
    enableRbacAuthorization: false
  }
}

// Application Insights
resource applicationInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: '${abbrs.insightsComponents}${resourceToken}'
  location: location
  tags: tags
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalyticsWorkspace.id
  }
}

// Outputs
output AZURE_APP_SERVICE_ENDPOINT string = 'https://${appService.properties.defaultHostName}'
output AZURE_APP_SERVICE_NAME string = appService.name
output AZURE_LOG_ANALYTICS_WORKSPACE_NAME string = logAnalyticsWorkspace.name
output AZURE_KEY_VAULT_NAME string = keyVault.name
output AZURE_APPLICATION_INSIGHTS_NAME string = applicationInsights.name
