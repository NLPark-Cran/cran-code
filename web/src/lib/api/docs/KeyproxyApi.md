# KeyproxyApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**proxyPxV1PathPost**](KeyproxyApi.md#proxypxv1pathpost) | **GET** /px/v1/{path} | Proxy |
| [**proxyPxV1PathPost_0**](KeyproxyApi.md#proxypxv1pathpost_0) | **PUT** /px/v1/{path} | Proxy |
| [**proxyPxV1PathPost_1**](KeyproxyApi.md#proxypxv1pathpost_1) | **POST** /px/v1/{path} | Proxy |
| [**proxyPxV1PathPost_2**](KeyproxyApi.md#proxypxv1pathpost_2) | **DELETE** /px/v1/{path} | Proxy |
| [**proxyPxV1PathPost_3**](KeyproxyApi.md#proxypxv1pathpost_3) | **PATCH** /px/v1/{path} | Proxy |



## proxyPxV1PathPost

> any proxyPxV1PathPost(path)

Proxy

Forward a provider API call with the resolved real key.

### Example

```ts
import {
  Configuration,
  KeyproxyApi,
} from '';
import type { ProxyPxV1PathPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new KeyproxyApi();

  const body = {
    // string
    path: path_example,
  } satisfies ProxyPxV1PathPostRequest;

  try {
    const data = await api.proxyPxV1PathPost(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## proxyPxV1PathPost_0

> any proxyPxV1PathPost_0(path)

Proxy

Forward a provider API call with the resolved real key.

### Example

```ts
import {
  Configuration,
  KeyproxyApi,
} from '';
import type { ProxyPxV1PathPost0Request } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new KeyproxyApi();

  const body = {
    // string
    path: path_example,
  } satisfies ProxyPxV1PathPost0Request;

  try {
    const data = await api.proxyPxV1PathPost_0(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## proxyPxV1PathPost_1

> any proxyPxV1PathPost_1(path)

Proxy

Forward a provider API call with the resolved real key.

### Example

```ts
import {
  Configuration,
  KeyproxyApi,
} from '';
import type { ProxyPxV1PathPost1Request } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new KeyproxyApi();

  const body = {
    // string
    path: path_example,
  } satisfies ProxyPxV1PathPost1Request;

  try {
    const data = await api.proxyPxV1PathPost_1(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## proxyPxV1PathPost_2

> any proxyPxV1PathPost_2(path)

Proxy

Forward a provider API call with the resolved real key.

### Example

```ts
import {
  Configuration,
  KeyproxyApi,
} from '';
import type { ProxyPxV1PathPost2Request } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new KeyproxyApi();

  const body = {
    // string
    path: path_example,
  } satisfies ProxyPxV1PathPost2Request;

  try {
    const data = await api.proxyPxV1PathPost_2(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## proxyPxV1PathPost_3

> any proxyPxV1PathPost_3(path)

Proxy

Forward a provider API call with the resolved real key.

### Example

```ts
import {
  Configuration,
  KeyproxyApi,
} from '';
import type { ProxyPxV1PathPost3Request } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new KeyproxyApi();

  const body = {
    // string
    path: path_example,
  } satisfies ProxyPxV1PathPost3Request;

  try {
    const data = await api.proxyPxV1PathPost_3(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: Not defined
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

