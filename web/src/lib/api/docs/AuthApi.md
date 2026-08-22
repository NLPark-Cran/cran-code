# AuthApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**loginApiV2AuthLoginPost**](AuthApi.md#loginapiv2authloginpost) | **POST** /api/v2/auth/login | Login |
| [**registerApiV2AuthRegisterPost**](AuthApi.md#registerapiv2authregisterpost) | **POST** /api/v2/auth/register | Register |



## loginApiV2AuthLoginPost

> TokenResponse loginApiV2AuthLoginPost(loginRequest)

Login

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { LoginApiV2AuthLoginPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // LoginRequest
    loginRequest: ...,
  } satisfies LoginApiV2AuthLoginPostRequest;

  try {
    const data = await api.loginApiV2AuthLoginPost(body);
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
| **loginRequest** | [LoginRequest](LoginRequest.md) |  | |

### Return type

[**TokenResponse**](TokenResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## registerApiV2AuthRegisterPost

> TokenResponse registerApiV2AuthRegisterPost(registerRequest)

Register

### Example

```ts
import {
  Configuration,
  AuthApi,
} from '';
import type { RegisterApiV2AuthRegisterPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const api = new AuthApi();

  const body = {
    // RegisterRequest
    registerRequest: ...,
  } satisfies RegisterApiV2AuthRegisterPostRequest;

  try {
    const data = await api.registerApiV2AuthRegisterPost(body);
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
| **registerRequest** | [RegisterRequest](RegisterRequest.md) |  | |

### Return type

[**TokenResponse**](TokenResponse.md)

### Authorization

No authorization required

### HTTP request headers

- **Content-Type**: `application/json`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **201** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)

