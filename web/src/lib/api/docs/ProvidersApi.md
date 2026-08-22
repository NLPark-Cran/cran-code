# ProvidersApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**createProviderApiV2ProvidersPost**](ProvidersApi.md#createproviderapiv2providerspost) | **POST** /api/v2/providers/ | Add a provider (models fetched from /models when omitted) |
| [**deleteProviderApiV2ProvidersKeyDelete**](ProvidersApi.md#deleteproviderapiv2providerskeydelete) | **DELETE** /api/v2/providers/{key} | Delete a provider and its models |
| [**fetchModelsApiV2ProvidersFetchModelsPost**](ProvidersApi.md#fetchmodelsapiv2providersfetchmodelspost) | **POST** /api/v2/providers/fetch-models | Probe {base_url}/models for a provider |
| [**listProvidersApiV2ProvidersGet**](ProvidersApi.md#listprovidersapiv2providersget) | **GET** /api/v2/providers/ | List providers and their models |
| [**selectModelApiV2ProvidersSelectPost**](ProvidersApi.md#selectmodelapiv2providersselectpost) | **POST** /api/v2/providers/select | Switch the global default model (restarts running workers) |
| [**setModelContextApiV2ProvidersModelsModelKeyContextPost**](ProvidersApi.md#setmodelcontextapiv2providersmodelsmodelkeycontextpost) | **POST** /api/v2/providers/models/{model_key}/context | Set a model\&#39;s context window (e.g. K3 256K/512K/1M tiers) |
| [**updateProviderApiV2ProvidersKeyPut**](ProvidersApi.md#updateproviderapiv2providerskeyput) | **PUT** /api/v2/providers/{key} | Update a provider\&#39;s endpoint, key, or models |



## createProviderApiV2ProvidersPost

> ProviderListResponse createProviderApiV2ProvidersPost(providerUpsertRequest)

Add a provider (models fetched from /models when omitted)

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { CreateProviderApiV2ProvidersPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  const body = {
    // ProviderUpsertRequest
    providerUpsertRequest: ...,
  } satisfies CreateProviderApiV2ProvidersPostRequest;

  try {
    const data = await api.createProviderApiV2ProvidersPost(body);
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
| **providerUpsertRequest** | [ProviderUpsertRequest](ProviderUpsertRequest.md) |  | |

### Return type

[**ProviderListResponse**](ProviderListResponse.md)

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


## deleteProviderApiV2ProvidersKeyDelete

> ProviderListResponse deleteProviderApiV2ProvidersKeyDelete(key)

Delete a provider and its models

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { DeleteProviderApiV2ProvidersKeyDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  const body = {
    // string
    key: key_example,
  } satisfies DeleteProviderApiV2ProvidersKeyDeleteRequest;

  try {
    const data = await api.deleteProviderApiV2ProvidersKeyDelete(body);
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
| **key** | `string` |  | [Defaults to `undefined`] |

### Return type

[**ProviderListResponse**](ProviderListResponse.md)

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


## fetchModelsApiV2ProvidersFetchModelsPost

> FetchModelsResponse fetchModelsApiV2ProvidersFetchModelsPost(fetchModelsRequest)

Probe {base_url}/models for a provider

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { FetchModelsApiV2ProvidersFetchModelsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  const body = {
    // FetchModelsRequest
    fetchModelsRequest: ...,
  } satisfies FetchModelsApiV2ProvidersFetchModelsPostRequest;

  try {
    const data = await api.fetchModelsApiV2ProvidersFetchModelsPost(body);
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
| **fetchModelsRequest** | [FetchModelsRequest](FetchModelsRequest.md) |  | |

### Return type

[**FetchModelsResponse**](FetchModelsResponse.md)

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


## listProvidersApiV2ProvidersGet

> ProviderListResponse listProvidersApiV2ProvidersGet()

List providers and their models

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { ListProvidersApiV2ProvidersGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  try {
    const data = await api.listProvidersApiV2ProvidersGet();
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

[**ProviderListResponse**](ProviderListResponse.md)

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


## selectModelApiV2ProvidersSelectPost

> SelectModelResponse selectModelApiV2ProvidersSelectPost(selectModelRequest)

Switch the global default model (restarts running workers)

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { SelectModelApiV2ProvidersSelectPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  const body = {
    // SelectModelRequest
    selectModelRequest: ...,
  } satisfies SelectModelApiV2ProvidersSelectPostRequest;

  try {
    const data = await api.selectModelApiV2ProvidersSelectPost(body);
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
| **selectModelRequest** | [SelectModelRequest](SelectModelRequest.md) |  | |

### Return type

[**SelectModelResponse**](SelectModelResponse.md)

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


## setModelContextApiV2ProvidersModelsModelKeyContextPost

> ProviderListResponse setModelContextApiV2ProvidersModelsModelKeyContextPost(modelKey, modelContextRequest)

Set a model\&#39;s context window (e.g. K3 256K/512K/1M tiers)

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { SetModelContextApiV2ProvidersModelsModelKeyContextPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  const body = {
    // string
    modelKey: modelKey_example,
    // ModelContextRequest
    modelContextRequest: ...,
  } satisfies SetModelContextApiV2ProvidersModelsModelKeyContextPostRequest;

  try {
    const data = await api.setModelContextApiV2ProvidersModelsModelKeyContextPost(body);
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
| **modelKey** | `string` |  | [Defaults to `undefined`] |
| **modelContextRequest** | [ModelContextRequest](ModelContextRequest.md) |  | |

### Return type

[**ProviderListResponse**](ProviderListResponse.md)

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


## updateProviderApiV2ProvidersKeyPut

> ProviderListResponse updateProviderApiV2ProvidersKeyPut(key, providerUpsertRequest)

Update a provider\&#39;s endpoint, key, or models

### Example

```ts
import {
  Configuration,
  ProvidersApi,
} from '';
import type { UpdateProviderApiV2ProvidersKeyPutRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProvidersApi(config);

  const body = {
    // string
    key: key_example,
    // ProviderUpsertRequest
    providerUpsertRequest: ...,
  } satisfies UpdateProviderApiV2ProvidersKeyPutRequest;

  try {
    const data = await api.updateProviderApiV2ProvidersKeyPut(body);
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
| **key** | `string` |  | [Defaults to `undefined`] |
| **providerUpsertRequest** | [ProviderUpsertRequest](ProviderUpsertRequest.md) |  | |

### Return type

[**ProviderListResponse**](ProviderListResponse.md)

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

