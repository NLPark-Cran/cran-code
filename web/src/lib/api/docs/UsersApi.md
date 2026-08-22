# UsersApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**deleteMyProviderKeyApiV2UsersMeProviderKeysProviderKeyDelete**](UsersApi.md#deletemyproviderkeyapiv2usersmeproviderkeysproviderkeydelete) | **DELETE** /api/v2/users/me/provider-keys/{provider_key} | Delete My Provider Key |
| [**getMeApiV2UsersMeGet**](UsersApi.md#getmeapiv2usersmeget) | **GET** /api/v2/users/me | Get Me |
| [**getMyUsageApiV2UsersMeUsageGet**](UsersApi.md#getmyusageapiv2usersmeusageget) | **GET** /api/v2/users/me/usage | Get My Usage |
| [**getMyUsageDailyApiV2UsersMeUsageDailyGet**](UsersApi.md#getmyusagedailyapiv2usersmeusagedailyget) | **GET** /api/v2/users/me/usage/daily | Get My Usage Daily |
| [**listMyProviderKeysApiV2UsersMeProviderKeysGet**](UsersApi.md#listmyproviderkeysapiv2usersmeproviderkeysget) | **GET** /api/v2/users/me/provider-keys | List My Provider Keys |
| [**searchUsersApiV2UsersSearchGet**](UsersApi.md#searchusersapiv2userssearchget) | **GET** /api/v2/users/search | Search Users |
| [**updateMeApiV2UsersMePatch**](UsersApi.md#updatemeapiv2usersmepatch) | **PATCH** /api/v2/users/me | Update Me |
| [**updateUserRoleApiV2UsersUserIdRolePatch**](UsersApi.md#updateuserroleapiv2usersuseridrolepatch) | **PATCH** /api/v2/users/{user_id}/role | Update User Role |
| [**upsertMyProviderKeyApiV2UsersMeProviderKeysProviderKeyPut**](UsersApi.md#upsertmyproviderkeyapiv2usersmeproviderkeysproviderkeyput) | **PUT** /api/v2/users/me/provider-keys/{provider_key} | Upsert My Provider Key |



## deleteMyProviderKeyApiV2UsersMeProviderKeysProviderKeyDelete

> { [key: string]: string | null; } deleteMyProviderKeyApiV2UsersMeProviderKeysProviderKeyDelete(providerKey)

Delete My Provider Key

Delete the current user\&#39;s API key for a provider.

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { DeleteMyProviderKeyApiV2UsersMeProviderKeysProviderKeyDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  const body = {
    // string
    providerKey: providerKey_example,
  } satisfies DeleteMyProviderKeyApiV2UsersMeProviderKeysProviderKeyDeleteRequest;

  try {
    const data = await api.deleteMyProviderKeyApiV2UsersMeProviderKeysProviderKeyDelete(body);
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


## getMeApiV2UsersMeGet

> CranCodeWebApiV2UsersUserResponse getMeApiV2UsersMeGet()

Get Me

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { GetMeApiV2UsersMeGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  try {
    const data = await api.getMeApiV2UsersMeGet();
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

[**CranCodeWebApiV2UsersUserResponse**](CranCodeWebApiV2UsersUserResponse.md)

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


## getMyUsageApiV2UsersMeUsageGet

> Array&lt;UsageSummary&gt; getMyUsageApiV2UsersMeUsageGet()

Get My Usage

Per-provider token usage summary for the current user.  Rows are grouped by &#x60;&#x60;(provider_key, source)&#x60;&#x60;. Rows with &#x60;&#x60;source&#x3D;\&#39;shared\&#39;&#x60;&#x60; additionally carry &#x60;&#x60;quota_tokens&#x60;&#x60; / &#x60;&#x60;remaining_tokens&#x60;&#x60; when a restricted-mode grant covers the user (&#x60;&#x60;None&#x60;&#x60; &#x3D; unlimited / not applicable).

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { GetMyUsageApiV2UsersMeUsageGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  try {
    const data = await api.getMyUsageApiV2UsersMeUsageGet();
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

[**Array&lt;UsageSummary&gt;**](UsageSummary.md)

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


## getMyUsageDailyApiV2UsersMeUsageDailyGet

> Array&lt;UsageDailyPoint&gt; getMyUsageDailyApiV2UsersMeUsageDailyGet(days, tz)

Get My Usage Daily

Per-day token usage for the current user over the last &#x60;&#x60;days&#x60;&#x60; days.  Rows are grouped by &#x60;&#x60;(date, provider_key, model, source)&#x60;&#x60; and ordered chronologically. Days are calendar days in the &#x60;&#x60;tz&#x60;&#x60; timezone (IANA name, default UTC); pass the browser\&#39;s timezone for a local \&quot;today\&quot;. &#x60;&#x60;days&#x60;&#x60; is clamped to [1, 90].

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { GetMyUsageDailyApiV2UsersMeUsageDailyGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  const body = {
    // number (optional)
    days: 56,
    // string (optional)
    tz: tz_example,
  } satisfies GetMyUsageDailyApiV2UsersMeUsageDailyGetRequest;

  try {
    const data = await api.getMyUsageDailyApiV2UsersMeUsageDailyGet(body);
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
| **days** | `number` |  | [Optional] [Defaults to `30`] |
| **tz** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;UsageDailyPoint&gt;**](UsageDailyPoint.md)

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


## listMyProviderKeysApiV2UsersMeProviderKeysGet

> Array&lt;ProviderKeyResponse&gt; listMyProviderKeysApiV2UsersMeProviderKeysGet()

List My Provider Keys

List the current user\&#39;s stored provider keys (masked).

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { ListMyProviderKeysApiV2UsersMeProviderKeysGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  try {
    const data = await api.listMyProviderKeysApiV2UsersMeProviderKeysGet();
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

[**Array&lt;ProviderKeyResponse&gt;**](ProviderKeyResponse.md)

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


## searchUsersApiV2UsersSearchGet

> Array&lt;CranCodeWebApiV2UsersUserResponse&gt; searchUsersApiV2UsersSearchGet(q)

Search Users

Search users by username, email, or display_name.

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { SearchUsersApiV2UsersSearchGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  const body = {
    // string
    q: q_example,
  } satisfies SearchUsersApiV2UsersSearchGetRequest;

  try {
    const data = await api.searchUsersApiV2UsersSearchGet(body);
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
| **q** | `string` |  | [Defaults to `undefined`] |

### Return type

[**Array&lt;CranCodeWebApiV2UsersUserResponse&gt;**](CranCodeWebApiV2UsersUserResponse.md)

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


## updateMeApiV2UsersMePatch

> CranCodeWebApiV2UsersUserResponse updateMeApiV2UsersMePatch(userProfileUpdate)

Update Me

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { UpdateMeApiV2UsersMePatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  const body = {
    // UserProfileUpdate
    userProfileUpdate: ...,
  } satisfies UpdateMeApiV2UsersMePatchRequest;

  try {
    const data = await api.updateMeApiV2UsersMePatch(body);
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
| **userProfileUpdate** | [UserProfileUpdate](UserProfileUpdate.md) |  | |

### Return type

[**CranCodeWebApiV2UsersUserResponse**](CranCodeWebApiV2UsersUserResponse.md)

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


## updateUserRoleApiV2UsersUserIdRolePatch

> CranCodeWebApiV2UsersUserResponse updateUserRoleApiV2UsersUserIdRolePatch(userId, userRoleUpdate)

Update User Role

Change a user\&#39;s global role (admin only).

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { UpdateUserRoleApiV2UsersUserIdRolePatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  const body = {
    // string
    userId: userId_example,
    // UserRoleUpdate
    userRoleUpdate: ...,
  } satisfies UpdateUserRoleApiV2UsersUserIdRolePatchRequest;

  try {
    const data = await api.updateUserRoleApiV2UsersUserIdRolePatch(body);
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
| **userId** | `string` |  | [Defaults to `undefined`] |
| **userRoleUpdate** | [UserRoleUpdate](UserRoleUpdate.md) |  | |

### Return type

[**CranCodeWebApiV2UsersUserResponse**](CranCodeWebApiV2UsersUserResponse.md)

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


## upsertMyProviderKeyApiV2UsersMeProviderKeysProviderKeyPut

> ProviderKeyResponse upsertMyProviderKeyApiV2UsersMeProviderKeysProviderKeyPut(providerKey, providerKeyUpsertRequest)

Upsert My Provider Key

Create or replace the current user\&#39;s API key for a provider.

### Example

```ts
import {
  Configuration,
  UsersApi,
} from '';
import type { UpsertMyProviderKeyApiV2UsersMeProviderKeysProviderKeyPutRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new UsersApi(config);

  const body = {
    // string
    providerKey: providerKey_example,
    // ProviderKeyUpsertRequest
    providerKeyUpsertRequest: ...,
  } satisfies UpsertMyProviderKeyApiV2UsersMeProviderKeysProviderKeyPutRequest;

  try {
    const data = await api.upsertMyProviderKeyApiV2UsersMeProviderKeysProviderKeyPut(body);
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
| **providerKey** | `string` |  | [Defaults to `undefined`] |
| **providerKeyUpsertRequest** | [ProviderKeyUpsertRequest](ProviderKeyUpsertRequest.md) |  | |

### Return type

[**ProviderKeyResponse**](ProviderKeyResponse.md)

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

