# GitApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**gitBranchesApiV2ProjectsProjectIdGitBranchesGet**](GitApi.md#gitbranchesapiv2projectsprojectidgitbranchesget) | **GET** /api/v2/projects/{project_id}/git/branches | Git Branches |
| [**gitCommitApiV2ProjectsProjectIdGitCommitPost**](GitApi.md#gitcommitapiv2projectsprojectidgitcommitpost) | **POST** /api/v2/projects/{project_id}/git/commit | Git Commit |
| [**gitDiffApiV2ProjectsProjectIdGitDiffGet**](GitApi.md#gitdiffapiv2projectsprojectidgitdiffget) | **GET** /api/v2/projects/{project_id}/git/diff | Git Diff |
| [**gitLogApiV2ProjectsProjectIdGitLogGet**](GitApi.md#gitlogapiv2projectsprojectidgitlogget) | **GET** /api/v2/projects/{project_id}/git/log | Git Log |
| [**gitStatusApiV2ProjectsProjectIdGitStatusGet**](GitApi.md#gitstatusapiv2projectsprojectidgitstatusget) | **GET** /api/v2/projects/{project_id}/git/status | Git Status |



## gitBranchesApiV2ProjectsProjectIdGitBranchesGet

> Array&lt;GitBranchResponse&gt; gitBranchesApiV2ProjectsProjectIdGitBranchesGet(projectId)

Git Branches

### Example

```ts
import {
  Configuration,
  GitApi,
} from '';
import type { GitBranchesApiV2ProjectsProjectIdGitBranchesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new GitApi(config);

  const body = {
    // string
    projectId: projectId_example,
  } satisfies GitBranchesApiV2ProjectsProjectIdGitBranchesGetRequest;

  try {
    const data = await api.gitBranchesApiV2ProjectsProjectIdGitBranchesGet(body);
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
| **projectId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**Array&lt;GitBranchResponse&gt;**](GitBranchResponse.md)

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


## gitCommitApiV2ProjectsProjectIdGitCommitPost

> { [key: string]: string | null; } gitCommitApiV2ProjectsProjectIdGitCommitPost(projectId, gitCommitRequest)

Git Commit

### Example

```ts
import {
  Configuration,
  GitApi,
} from '';
import type { GitCommitApiV2ProjectsProjectIdGitCommitPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new GitApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // GitCommitRequest
    gitCommitRequest: ...,
  } satisfies GitCommitApiV2ProjectsProjectIdGitCommitPostRequest;

  try {
    const data = await api.gitCommitApiV2ProjectsProjectIdGitCommitPost(body);
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
| **projectId** | `string` |  | [Defaults to `undefined`] |
| **gitCommitRequest** | [GitCommitRequest](GitCommitRequest.md) |  | |

### Return type

**{ [key: string]: string | null; }**

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


## gitDiffApiV2ProjectsProjectIdGitDiffGet

> Array&lt;GitDiffResponse&gt; gitDiffApiV2ProjectsProjectIdGitDiffGet(projectId, staged, path)

Git Diff

### Example

```ts
import {
  Configuration,
  GitApi,
} from '';
import type { GitDiffApiV2ProjectsProjectIdGitDiffGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new GitApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // boolean (optional)
    staged: true,
    // string (optional)
    path: path_example,
  } satisfies GitDiffApiV2ProjectsProjectIdGitDiffGetRequest;

  try {
    const data = await api.gitDiffApiV2ProjectsProjectIdGitDiffGet(body);
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
| **projectId** | `string` |  | [Defaults to `undefined`] |
| **staged** | `boolean` |  | [Optional] [Defaults to `false`] |
| **path** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;GitDiffResponse&gt;**](GitDiffResponse.md)

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


## gitLogApiV2ProjectsProjectIdGitLogGet

> Array&lt;GitCommitResponse&gt; gitLogApiV2ProjectsProjectIdGitLogGet(projectId, limit)

Git Log

### Example

```ts
import {
  Configuration,
  GitApi,
} from '';
import type { GitLogApiV2ProjectsProjectIdGitLogGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new GitApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // number (optional)
    limit: 56,
  } satisfies GitLogApiV2ProjectsProjectIdGitLogGetRequest;

  try {
    const data = await api.gitLogApiV2ProjectsProjectIdGitLogGet(body);
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
| **projectId** | `string` |  | [Defaults to `undefined`] |
| **limit** | `number` |  | [Optional] [Defaults to `20`] |

### Return type

[**Array&lt;GitCommitResponse&gt;**](GitCommitResponse.md)

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


## gitStatusApiV2ProjectsProjectIdGitStatusGet

> GitStatusResponse gitStatusApiV2ProjectsProjectIdGitStatusGet(projectId)

Git Status

### Example

```ts
import {
  Configuration,
  GitApi,
} from '';
import type { GitStatusApiV2ProjectsProjectIdGitStatusGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new GitApi(config);

  const body = {
    // string
    projectId: projectId_example,
  } satisfies GitStatusApiV2ProjectsProjectIdGitStatusGetRequest;

  try {
    const data = await api.gitStatusApiV2ProjectsProjectIdGitStatusGet(body);
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
| **projectId** | `string` |  | [Defaults to `undefined`] |

### Return type

[**GitStatusResponse**](GitStatusResponse.md)

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

