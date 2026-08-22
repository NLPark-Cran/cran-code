# ProjectsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**addProjectMemberApiV2ProjectsProjectIdMembersPost**](ProjectsApi.md#addprojectmemberapiv2projectsprojectidmemberspost) | **POST** /api/v2/projects/{project_id}/members | Add Project Member |
| [**createProjectActivityApiV2ProjectsProjectIdActivitiesPost**](ProjectsApi.md#createprojectactivityapiv2projectsprojectidactivitiespost) | **POST** /api/v2/projects/{project_id}/activities | Create Project Activity |
| [**createProjectApiV2ProjectsPost**](ProjectsApi.md#createprojectapiv2projectspost) | **POST** /api/v2/projects | Create Project |
| [**getProjectApiV2ProjectsProjectIdGet**](ProjectsApi.md#getprojectapiv2projectsprojectidget) | **GET** /api/v2/projects/{project_id} | Get Project |
| [**listProjectActivitiesApiV2ProjectsProjectIdActivitiesGet**](ProjectsApi.md#listprojectactivitiesapiv2projectsprojectidactivitiesget) | **GET** /api/v2/projects/{project_id}/activities | List Project Activities |
| [**listProjectsApiV2ProjectsGet**](ProjectsApi.md#listprojectsapiv2projectsget) | **GET** /api/v2/projects | List Projects |
| [**removeProjectMemberApiV2ProjectsProjectIdMembersMemberIdDelete**](ProjectsApi.md#removeprojectmemberapiv2projectsprojectidmembersmemberiddelete) | **DELETE** /api/v2/projects/{project_id}/members/{member_id} | Remove Project Member |
| [**updateProjectApiV2ProjectsProjectIdPatch**](ProjectsApi.md#updateprojectapiv2projectsprojectidpatch) | **PATCH** /api/v2/projects/{project_id} | Update Project |
| [**updateProjectMemberRoleApiV2ProjectsProjectIdMembersMemberIdPatch**](ProjectsApi.md#updateprojectmemberroleapiv2projectsprojectidmembersmemberidpatch) | **PATCH** /api/v2/projects/{project_id}/members/{member_id} | Update Project Member Role |



## addProjectMemberApiV2ProjectsProjectIdMembersPost

> ProjectResponse addProjectMemberApiV2ProjectsProjectIdMembersPost(projectId, userId, role)

Add Project Member

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { AddProjectMemberApiV2ProjectsProjectIdMembersPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    userId: userId_example,
    // string (optional)
    role: role_example,
  } satisfies AddProjectMemberApiV2ProjectsProjectIdMembersPostRequest;

  try {
    const data = await api.addProjectMemberApiV2ProjectsProjectIdMembersPost(body);
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
| **userId** | `string` |  | [Defaults to `undefined`] |
| **role** | `string` |  | [Optional] [Defaults to `&#39;member&#39;`] |

### Return type

[**ProjectResponse**](ProjectResponse.md)

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


## createProjectActivityApiV2ProjectsProjectIdActivitiesPost

> ActivityResponse createProjectActivityApiV2ProjectsProjectIdActivitiesPost(projectId, activityCreate)

Create Project Activity

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { CreateProjectActivityApiV2ProjectsProjectIdActivitiesPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // ActivityCreate
    activityCreate: ...,
  } satisfies CreateProjectActivityApiV2ProjectsProjectIdActivitiesPostRequest;

  try {
    const data = await api.createProjectActivityApiV2ProjectsProjectIdActivitiesPost(body);
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
| **activityCreate** | [ActivityCreate](ActivityCreate.md) |  | |

### Return type

[**ActivityResponse**](ActivityResponse.md)

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


## createProjectApiV2ProjectsPost

> ProjectResponse createProjectApiV2ProjectsPost(projectCreate)

Create Project

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { CreateProjectApiV2ProjectsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // ProjectCreate
    projectCreate: ...,
  } satisfies CreateProjectApiV2ProjectsPostRequest;

  try {
    const data = await api.createProjectApiV2ProjectsPost(body);
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
| **projectCreate** | [ProjectCreate](ProjectCreate.md) |  | |

### Return type

[**ProjectResponse**](ProjectResponse.md)

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


## getProjectApiV2ProjectsProjectIdGet

> ProjectResponse getProjectApiV2ProjectsProjectIdGet(projectId)

Get Project

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { GetProjectApiV2ProjectsProjectIdGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
  } satisfies GetProjectApiV2ProjectsProjectIdGetRequest;

  try {
    const data = await api.getProjectApiV2ProjectsProjectIdGet(body);
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

[**ProjectResponse**](ProjectResponse.md)

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


## listProjectActivitiesApiV2ProjectsProjectIdActivitiesGet

> Array&lt;ActivityResponse&gt; listProjectActivitiesApiV2ProjectsProjectIdActivitiesGet(projectId, limit)

List Project Activities

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { ListProjectActivitiesApiV2ProjectsProjectIdActivitiesGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // number (optional)
    limit: 56,
  } satisfies ListProjectActivitiesApiV2ProjectsProjectIdActivitiesGetRequest;

  try {
    const data = await api.listProjectActivitiesApiV2ProjectsProjectIdActivitiesGet(body);
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
| **limit** | `number` |  | [Optional] [Defaults to `50`] |

### Return type

[**Array&lt;ActivityResponse&gt;**](ActivityResponse.md)

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


## listProjectsApiV2ProjectsGet

> Array&lt;ProjectResponse&gt; listProjectsApiV2ProjectsGet(teamId)

List Projects

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { ListProjectsApiV2ProjectsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string (optional)
    teamId: teamId_example,
  } satisfies ListProjectsApiV2ProjectsGetRequest;

  try {
    const data = await api.listProjectsApiV2ProjectsGet(body);
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
| **teamId** | `string` |  | [Optional] [Defaults to `undefined`] |

### Return type

[**Array&lt;ProjectResponse&gt;**](ProjectResponse.md)

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


## removeProjectMemberApiV2ProjectsProjectIdMembersMemberIdDelete

> { [key: string]: string | null; } removeProjectMemberApiV2ProjectsProjectIdMembersMemberIdDelete(projectId, memberId)

Remove Project Member

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { RemoveProjectMemberApiV2ProjectsProjectIdMembersMemberIdDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    memberId: memberId_example,
  } satisfies RemoveProjectMemberApiV2ProjectsProjectIdMembersMemberIdDeleteRequest;

  try {
    const data = await api.removeProjectMemberApiV2ProjectsProjectIdMembersMemberIdDelete(body);
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


## updateProjectApiV2ProjectsProjectIdPatch

> ProjectResponse updateProjectApiV2ProjectsProjectIdPatch(projectId, projectUpdate)

Update Project

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { UpdateProjectApiV2ProjectsProjectIdPatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // ProjectUpdate
    projectUpdate: ...,
  } satisfies UpdateProjectApiV2ProjectsProjectIdPatchRequest;

  try {
    const data = await api.updateProjectApiV2ProjectsProjectIdPatch(body);
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
| **projectUpdate** | [ProjectUpdate](ProjectUpdate.md) |  | |

### Return type

[**ProjectResponse**](ProjectResponse.md)

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


## updateProjectMemberRoleApiV2ProjectsProjectIdMembersMemberIdPatch

> ProjectResponse updateProjectMemberRoleApiV2ProjectsProjectIdMembersMemberIdPatch(projectId, memberId, projectMemberUpdateRole)

Update Project Member Role

### Example

```ts
import {
  Configuration,
  ProjectsApi,
} from '';
import type { UpdateProjectMemberRoleApiV2ProjectsProjectIdMembersMemberIdPatchRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new ProjectsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    memberId: memberId_example,
    // ProjectMemberUpdateRole
    projectMemberUpdateRole: ...,
  } satisfies UpdateProjectMemberRoleApiV2ProjectsProjectIdMembersMemberIdPatchRequest;

  try {
    const data = await api.updateProjectMemberRoleApiV2ProjectsProjectIdMembersMemberIdPatch(body);
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
| **memberId** | `string` |  | [Defaults to `undefined`] |
| **projectMemberUpdateRole** | [ProjectMemberUpdateRole](ProjectMemberUpdateRole.md) |  | |

### Return type

[**ProjectResponse**](ProjectResponse.md)

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

