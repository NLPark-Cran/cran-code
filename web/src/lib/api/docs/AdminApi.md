# AdminApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**getAdminUsageApiV2AdminUsageGet**](AdminApi.md#getadminusageapiv2adminusageget) | **GET** /api/v2/admin/usage | Get Admin Usage |



## getAdminUsageApiV2AdminUsageGet

> Array&lt;AdminUsageDailyPoint&gt; getAdminUsageApiV2AdminUsageGet(days, tz)

Get Admin Usage

Per-day token usage for ALL users (admin only).  Same bucketing as &#x60;&#x60;/users/me/usage/daily&#x60;&#x60; but additionally grouped by user, with &#x60;&#x60;username&#x60;&#x60; resolved via a join. Ordered by date, then user. Days are calendar days in the &#x60;&#x60;tz&#x60;&#x60; timezone (IANA name, default UTC). &#x60;&#x60;days&#x60;&#x60; is clamped to [1, 90].

### Example

```ts
import {
  Configuration,
  AdminApi,
} from '';
import type { GetAdminUsageApiV2AdminUsageGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new AdminApi(config);

  const body = {
    // number (optional)
    days: 56,
    // string (optional)
    tz: tz_example,
  } satisfies GetAdminUsageApiV2AdminUsageGetRequest;

  try {
    const data = await api.getAdminUsageApiV2AdminUsageGet(body);
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

[**Array&lt;AdminUsageDailyPoint&gt;**](AdminUsageDailyPoint.md)

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

