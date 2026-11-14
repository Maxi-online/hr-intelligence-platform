# Employer OAuth setup for Candidate Ranking

The HH integration needs an employer-authorized session to read responses to
vacancies that the account can access. Application credentials alone do not
grant those permissions. OpenAI authentication is a separate setting used by
the analysis service.

## Register an application

Register an application in the [HH developer console](https://dev.hh.ru/admin).
Choose your own application name and contact identity. Record its client ID,
client secret and exact redirect URI in private configuration. Use a redirect
URI controlled by your deployment. The repository's gateway port does not, by
itself, provide a production OAuth callback/session implementation.

The [official HH authorization guide](https://github.com/hhru/api/blob/master/docs/authorization_for_user.md)
describes the authorization-code and refresh-token flows.

## Obtain an authorization code

The following PowerShell example reads existing process variables and asks for
the registered redirect URI. It generates an authorization URL without printing
the client secret.

```powershell
if (-not $env:HH_API_CLIENT_ID) { throw 'Set HH_API_CLIENT_ID in the private process environment first.' }
$redirectUri = Read-Host 'Registered HH redirect URI'
$authorizationUri = 'https://hh.ru/oauth/authorize?response_type=code&client_id=' +
    [uri]::EscapeDataString($env:HH_API_CLIENT_ID) + '&redirect_uri=' +
    [uri]::EscapeDataString($redirectUri)
Start-Process $authorizationUri
```

Sign in with the employer account, approve access, and obtain the authorization
code from your callback. Keep the redirect URI identical during the exchange.

## Exchange the code

This step makes a real provider request when an operator runs it. It is not part
of the repository's offline checks.

```powershell
if (-not $env:HH_API_CLIENT_SECRET) { throw 'Set HH_API_CLIENT_SECRET in the private process environment first.' }
$authorizationCode = Read-Host 'Authorization code returned to your callback'
$tokenResponse = Invoke-RestMethod -Method Post -Uri 'https://hh.ru/oauth/token' -ContentType 'application/x-www-form-urlencoded' -Body @{
    grant_type = 'authorization_code'
    client_id = $env:HH_API_CLIENT_ID
    client_secret = $env:HH_API_CLIENT_SECRET
    code = $authorizationCode
    redirect_uri = $redirectUri
}
$env:HH_API_USER_TOKENS_ACCESS_TOKEN = $tokenResponse.access_token
$env:HH_API_USER_TOKENS_REFRESH_TOKEN = $tokenResponse.refresh_token
```

Persist the returned tokens and expiry in your private deployment configuration
or secret store. Do not print `$tokenResponse` in shared logs or commit it.
Refresh tokens through the provider's refresh flow when the access token expires.

## Connect the component

The public YAML refers to `HH_API_CLIENT_ID`, `HH_API_CLIENT_SECRET`,
`HH_API_USER_AGENT`, `HH_API_USER_TOKENS_ACCESS_TOKEN` and
`HH_API_USER_TOKENS_REFRESH_TOKEN`. See [environment variables](ENVIRONMENT_VARIABLES.md).
Use a private `config/settings.yaml`, based on `config/settings.example.yaml`.

Once configured, start the component as described in [INSTALL.md](INSTALL.md),
open the frontend at `http://localhost:8501`, and select a vacancy accessible to
the employer session. The API schema is at `http://localhost:8088/docs`.

## Troubleshooting

| Response | Check |
| --- | --- |
| 401 | Token validity, refresh status and application credentials |
| 403 | Employer permissions and access to the selected vacancy |
| 404 | Vacancy existence and visibility to that account |
| 429 | Provider rate limits; reduce request concurrency and retry after the limit window |

The offline suite does not authorize an employer account or verify live HH access.
