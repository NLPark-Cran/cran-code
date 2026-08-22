# TeamsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**addTeamMemberApiV2TeamsTeamIdMembersPost**](TeamsApi.md#addteammemberapiv2teamsteamidmemberspost) | **POST** /api/v2/teams/{team_id}/members | Add Team Member |
| [**createTeamApiV2TeamsPost**](TeamsApi.md#createteamapiv2teamspost) | **POST** /api/v2/teams | Create Team |
| [**deleteTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyDelete**](TeamsApi.md#deleteteamproviderkeyapiv2teamsteamidproviderkeysproviderkeydelete) | **DELETE** /api/v2/teams/{team_id}/provider-keys/{provider_key} | Delete Team Provider Key |
| [**getTeamApiV2TeamsTeamIdGet**](TeamsApi.md#getteamapiv2teamsteamidget) | **GET** /api/v2/teams/{team_id} | Get Team |
| [**listTeamProviderKeysApiV2TeamsTeamIdProviderKeysGet**](TeamsApi.md#listteamproviderkeysapiv2teamsteamidproviderkeysget) | **GET** /api/v2/teams/{team_id}/provider-keys | List Team Provider Keys |
| [**listTeamsApiV2TeamsGet**](TeamsApi.md#listteamsapiv2teamsget) | **GET** /api/v2/teams | List Teams |
| [**removeTeamMemberApiV2TeamsTeamIdMembersMemberIdDelete**](TeamsApi.md#removeteammemberapiv2teamsteamidmembersmemberiddelete) | **DELETE** /api/v2/teams/{team_id}/members/{member_id} | Remove Team Member |
| [**updateTeamApiV2TeamsTeamIdPatch**](TeamsApi.md#updateteamapiv2teamsteamidpatch) | **PATCH** /api/v2/teams/{team_id} | Update Team |
| [**updateTeamMemberRoleApiV2TeamsTeamIdMembersMemberIdPatch**](TeamsApi.md#updateteammemberroleapiv2teamsteamidmembersmemberidpatch) | **PATCH** /api/v2/teams/{team_id}/members/{member_id} | Update Team Member Role |
| [**upsertTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyPut**](TeamsApi.md#upsertteamproviderkeyapiv2teamsteamidproviderkeysproviderkeyput) | **PUT** /api/v2/teams/{team_id}/provider-keys/{provider_key} | Upsert Team Provider Key |



## addTeamMemberApiV2TeamsTeamIdMembersPost

> TeamResponse addTeamMemberApiV2TeamsTeamIdMembersPost(teamId, userId, role)

Add Team Member

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { AddTeamMemberApiV2TeamsTeamIdMembersPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
    // string
    userId: userId_example,
    // string (optional)
    role: role_example,
  } satisfies AddTeamMemberApiV2TeamsTeamIdMembersPostRequest;

  try {
    const data = await api.addTeamMemberApiV2TeamsTeamIdMembersPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |
| **userId** | `string` |  | [Defaults to `undefined`] |
| **role** | `string` |  | [Optional] [Defaults to `&#39;member&#39;`] |

### Return type

[**TeamResponse**](TeamResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## createTeamApiV2TeamsPost

> TeamResponse createTeamApiV2TeamsPost(teamCreate)

Create Team

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { CreateTeamApiV2TeamsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // TeamCreate
    teamCreate: ...,
  } satisfies CreateTeamApiV2TeamsPostRequest;

  try {
    const data = await api.createTeamApiV2TeamsPost(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamCreate** | [TeamCreate](TeamCreate.md) |  | |

### Return type

[**TeamResponse**](TeamResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **201** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## deleteTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyDelete

> { [key: string]: string | null; } deleteTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyDelete(teamId, providerKey)

Delete Team Provider Key

Delete a team\&#39;s API key for a provider. Team owner/admin only.

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { DeleteTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
    // string
    providerKey: providerKey_example,
  } satisfies DeleteTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyDeleteRequest;

  try {
    const data = await api.deleteTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyDelete(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |
| **providerKey** | `string` |  | [Defaults to `undefined`] |

### Return type

**{ [key: string]: string | null; }**

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## getTeamApiV2TeamsTeamIdGet

> TeamResponse getTeamApiV2TeamsTeamIdGet(teamId)

Get Team

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { GetTeamApiV2TeamsTeamIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
  } satisfies GetTeamApiV2TeamsTeamIdGetRequest;

  try {
    const data = await api.getTeamApiV2TeamsTeamIdGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**TeamResponse**](TeamResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listTeamProviderKeysApiV2TeamsTeamIdProviderKeysGet

> Array&lt;TeamProviderKeyResponse&gt; listTeamProviderKeysApiV2TeamsTeamIdProviderKeysGet(teamId)

List Team Provider Keys

List a team\&#39;s stored provider keys (masked). Team owner/admin only.

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { ListTeamProviderKeysApiV2TeamsTeamIdProviderKeysGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
  } satisfies ListTeamProviderKeysApiV2TeamsTeamIdProviderKeysGetRequest;

  try {
    const data = await api.listTeamProviderKeysApiV2TeamsTeamIdProviderKeysGet(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**Array&lt;TeamProviderKeyResponse&gt;**](TeamProviderKeyResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## listTeamsApiV2TeamsGet

> Array&lt;TeamResponse&gt; listTeamsApiV2TeamsGet()

List Teams

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { ListTeamsApiV2TeamsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  try {
    const data = await api.listTeamsApiV2TeamsGet();
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters

This endpoint does not need any parameter.

### Return type

[**Array&lt;TeamResponse&gt;**](TeamResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## removeTeamMemberApiV2TeamsTeamIdMembersMemberIdDelete

> { [key: string]: string | null; } removeTeamMemberApiV2TeamsTeamIdMembersMemberIdDelete(teamId, memberId)

Remove Team Member

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { RemoveTeamMemberApiV2TeamsTeamIdMembersMemberIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
    // string
    memberId: memberId_example,
  } satisfies RemoveTeamMemberApiV2TeamsTeamIdMembersMemberIdDeleteRequest;

  try {
    const data = await api.removeTeamMemberApiV2TeamsTeamIdMembersMemberIdDelete(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |
| **memberId** | `string` |  | [Defaults to `undefined`] |

### Return type

**{ [key: string]: string | null; }**

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## updateTeamApiV2TeamsTeamIdPatch

> TeamResponse updateTeamApiV2TeamsTeamIdPatch(teamId, teamUpdate)

Update Team

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { UpdateTeamApiV2TeamsTeamIdPatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
    // TeamUpdate
    teamUpdate: ...,
  } satisfies UpdateTeamApiV2TeamsTeamIdPatchRequest;

  try {
    const data = await api.updateTeamApiV2TeamsTeamIdPatch(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |
| **teamUpdate** | [TeamUpdate](TeamUpdate.md) |  | |

### Return type

[**TeamResponse**](TeamResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## updateTeamMemberRoleApiV2TeamsTeamIdMembersMemberIdPatch

> TeamResponse updateTeamMemberRoleApiV2TeamsTeamIdMembersMemberIdPatch(teamId, memberId, teamMemberUpdateRole)

Update Team Member Role

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { UpdateTeamMemberRoleApiV2TeamsTeamIdMembersMemberIdPatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
    // string
    memberId: memberId_example,
    // TeamMemberUpdateRole
    teamMemberUpdateRole: ...,
  } satisfies UpdateTeamMemberRoleApiV2TeamsTeamIdMembersMemberIdPatchRequest;

  try {
    const data = await api.updateTeamMemberRoleApiV2TeamsTeamIdMembersMemberIdPatch(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |
| **memberId** | `string` |  | [Defaults to `undefined`] |
| **teamMemberUpdateRole** | [TeamMemberUpdateRole](TeamMemberUpdateRole.md) |  | |

### Return type

[**TeamResponse**](TeamResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## upsertTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyPut

> TeamProviderKeyResponse upsertTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyPut(teamId, providerKey, teamProviderKeyUpsertRequest)

Upsert Team Provider Key

Create or replace a team\&#39;s API key for a provider. Team owner/admin only.

### Example

```ts
import {
  Configuration,
  TeamsApi,
} from '';
import type { UpsertTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyPutRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new TeamsApi(config);

  const body = {
    // string
    teamId: teamId_example,
    // string
    providerKey: providerKey_example,
    // TeamProviderKeyUpsertRequest
    teamProviderKeyUpsertRequest: ...,
  } satisfies UpsertTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyPutRequest;

  try {
    const data = await api.upsertTeamProviderKeyApiV2TeamsTeamIdProviderKeysProviderKeyPut(body);
    console.log(data);
  } catch (error) {
    console.error(error);
  }
}

// Run the test
example().catch(console.error);
```

### Parameters


| Name | Type | Description  | Notes |
|------------- | ------------- | ------------- | -------------|
| **teamId** | `string` |  | [Defaults to `undefined`] |
| **providerKey** | `string` |  | [Defaults to `undefined`] |
| **teamProviderKeyUpsertRequest** | [TeamProviderKeyUpsertRequest](TeamProviderKeyUpsertRequest.md) |  | |

### Return type

[**TeamProviderKeyResponse**](TeamProviderKeyResponse.md)

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

