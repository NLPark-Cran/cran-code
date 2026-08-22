# FsApi

All URIs are relative to *http://localhost*

| Method | HTTP request | Description |
|------------- | ------------- | -------------|
| [**compressFsApiV2ProjectsProjectIdFsCompressPost**](FsApi.md#compressfsapiv2projectsprojectidfscompresspost) | **POST** /api/v2/projects/{project_id}/fs/compress | Compress Fs |
| [**copyFsApiV2ProjectsProjectIdFsCopyPost**](FsApi.md#copyfsapiv2projectsprojectidfscopypost) | **POST** /api/v2/projects/{project_id}/fs/copy | Copy Fs |
| [**deleteFsApiV2ProjectsProjectIdFsDelete**](FsApi.md#deletefsapiv2projectsprojectidfsdelete) | **DELETE** /api/v2/projects/{project_id}/fs | Delete Fs |
| [**downloadFsApiV2ProjectsProjectIdFsDownloadGet**](FsApi.md#downloadfsapiv2projectsprojectidfsdownloadget) | **GET** /api/v2/projects/{project_id}/fs/download | Download Fs |
| [**extractFsApiV2ProjectsProjectIdFsExtractPost**](FsApi.md#extractfsapiv2projectsprojectidfsextractpost) | **POST** /api/v2/projects/{project_id}/fs/extract | Extract Fs |
| [**moveFsApiV2ProjectsProjectIdFsMovePost**](FsApi.md#movefsapiv2projectsprojectidfsmovepost) | **POST** /api/v2/projects/{project_id}/fs/move | Move Fs |
| [**readFsApiV2ProjectsProjectIdFsGet**](FsApi.md#readfsapiv2projectsprojectidfsget) | **GET** /api/v2/projects/{project_id}/fs | Read Fs |
| [**uploadFsApiV2ProjectsProjectIdFsUploadPost**](FsApi.md#uploadfsapiv2projectsprojectidfsuploadpost) | **POST** /api/v2/projects/{project_id}/fs/upload | Upload Fs |
| [**writeFsApiV2ProjectsProjectIdFsPost**](FsApi.md#writefsapiv2projectsprojectidfspost) | **POST** /api/v2/projects/{project_id}/fs | Write Fs |



## compressFsApiV2ProjectsProjectIdFsCompressPost

> { [key: string]: string | null; } compressFsApiV2ProjectsProjectIdFsCompressPost(projectId, path, archive)

Compress Fs

Compress a file or directory into a zip archive inside the project.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { CompressFsApiV2ProjectsProjectIdFsCompressPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    path: path_example,
    // string
    archive: archive_example,
  } satisfies CompressFsApiV2ProjectsProjectIdFsCompressPostRequest;

  try {
    const data = await api.compressFsApiV2ProjectsProjectIdFsCompressPost(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |
| **archive** | `string` |  | [Defaults to `undefined`] |

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


## copyFsApiV2ProjectsProjectIdFsCopyPost

> { [key: string]: string | null; } copyFsApiV2ProjectsProjectIdFsCopyPost(projectId, src, dst)

Copy Fs

Copy a file or directory to another path inside the project.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { CopyFsApiV2ProjectsProjectIdFsCopyPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    src: src_example,
    // string
    dst: dst_example,
  } satisfies CopyFsApiV2ProjectsProjectIdFsCopyPostRequest;

  try {
    const data = await api.copyFsApiV2ProjectsProjectIdFsCopyPost(body);
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
| **src** | `string` |  | [Defaults to `undefined`] |
| **dst** | `string` |  | [Defaults to `undefined`] |

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


## deleteFsApiV2ProjectsProjectIdFsDelete

> { [key: string]: string | null; } deleteFsApiV2ProjectsProjectIdFsDelete(projectId, path)

Delete Fs

Delete a file or directory inside the project working directory.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { DeleteFsApiV2ProjectsProjectIdFsDeleteRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    path: path_example,
  } satisfies DeleteFsApiV2ProjectsProjectIdFsDeleteRequest;

  try {
    const data = await api.deleteFsApiV2ProjectsProjectIdFsDelete(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

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


## downloadFsApiV2ProjectsProjectIdFsDownloadGet

> any downloadFsApiV2ProjectsProjectIdFsDownloadGet(projectId, path)

Download Fs

Download a file from the project working directory.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { DownloadFsApiV2ProjectsProjectIdFsDownloadGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    path: path_example,
  } satisfies DownloadFsApiV2ProjectsProjectIdFsDownloadGetRequest;

  try {
    const data = await api.downloadFsApiV2ProjectsProjectIdFsDownloadGet(body);
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
| **path** | `string` |  | [Defaults to `undefined`] |

### Return type

**any**

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


## extractFsApiV2ProjectsProjectIdFsExtractPost

> { [key: string]: string | null; } extractFsApiV2ProjectsProjectIdFsExtractPost(projectId, archive, dest)

Extract Fs

Extract a zip archive inside the project working directory.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { ExtractFsApiV2ProjectsProjectIdFsExtractPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    archive: archive_example,
    // string (optional)
    dest: dest_example,
  } satisfies ExtractFsApiV2ProjectsProjectIdFsExtractPostRequest;

  try {
    const data = await api.extractFsApiV2ProjectsProjectIdFsExtractPost(body);
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
| **archive** | `string` |  | [Defaults to `undefined`] |
| **dest** | `string` |  | [Optional] [Defaults to `&#39;&#39;`] |

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


## moveFsApiV2ProjectsProjectIdFsMovePost

> { [key: string]: string | null; } moveFsApiV2ProjectsProjectIdFsMovePost(projectId, src, dst)

Move Fs

Move (rename) a file or directory to another path inside the project.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { MoveFsApiV2ProjectsProjectIdFsMovePostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string
    src: src_example,
    // string
    dst: dst_example,
  } satisfies MoveFsApiV2ProjectsProjectIdFsMovePostRequest;

  try {
    const data = await api.moveFsApiV2ProjectsProjectIdFsMovePost(body);
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
| **src** | `string` |  | [Defaults to `undefined`] |
| **dst** | `string` |  | [Defaults to `undefined`] |

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


## readFsApiV2ProjectsProjectIdFsGet

> ResponseReadFsApiV2ProjectsProjectIdFsGet readFsApiV2ProjectsProjectIdFsGet(projectId, path)

Read Fs

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { ReadFsApiV2ProjectsProjectIdFsGetRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // string (optional)
    path: path_example,
  } satisfies ReadFsApiV2ProjectsProjectIdFsGetRequest;

  try {
    const data = await api.readFsApiV2ProjectsProjectIdFsGet(body);
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
| **path** | `string` |  | [Optional] [Defaults to `&#39;&#39;`] |

### Return type

[**ResponseReadFsApiV2ProjectsProjectIdFsGet**](ResponseReadFsApiV2ProjectsProjectIdFsGet.md)

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


## uploadFsApiV2ProjectsProjectIdFsUploadPost

> { [key: string]: string | null; } uploadFsApiV2ProjectsProjectIdFsUploadPost(projectId, file, path)

Upload Fs

Upload a file into the project working directory.  The &#x60;path&#x60; query parameter is the relative directory where the file should be stored. The uploaded file\&#39;s original filename is appended to it.

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { UploadFsApiV2ProjectsProjectIdFsUploadPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // Blob
    file: BINARY_DATA_HERE,
    // string (optional)
    path: path_example,
  } satisfies UploadFsApiV2ProjectsProjectIdFsUploadPostRequest;

  try {
    const data = await api.uploadFsApiV2ProjectsProjectIdFsUploadPost(body);
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
| **file** | `Blob` |  | [Defaults to `undefined`] |
| **path** | `string` |  | [Optional] [Defaults to `&#39;&#39;`] |

### Return type

**{ [key: string]: string | null; }**

### Authorization

[OAuth2PasswordBearer password](../README.md#OAuth2PasswordBearer-password)

### HTTP request headers

- **Content-Type**: `multipart/form-data`
- **Accept**: `application/json`


### HTTP response details
| Status code | Description | Response headers |
|-------------|-------------|------------------|
| **200** | Successful Response |  -  |
| **422** | Validation Error |  -  |

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


## writeFsApiV2ProjectsProjectIdFsPost

> { [key: string]: string | null; } writeFsApiV2ProjectsProjectIdFsPost(projectId, fsWriteRequest)

Write Fs

### Example

```ts
import {
  Configuration,
  FsApi,
} from '';
import type { WriteFsApiV2ProjectsProjectIdFsPostRequest } from '';

async function example() {
  console.log("🚀 Testing  SDK...");
  const config = new Configuration({ 
    // To configure OAuth2 access token for authorization: OAuth2PasswordBearer password
    accessToken: "YOUR ACCESS TOKEN",
  });
  const api = new FsApi(config);

  const body = {
    // string
    projectId: projectId_example,
    // FsWriteRequest
    fsWriteRequest: ...,
  } satisfies WriteFsApiV2ProjectsProjectIdFsPostRequest;

  try {
    const data = await api.writeFsApiV2ProjectsProjectIdFsPost(body);
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
| **fsWriteRequest** | [FsWriteRequest](FsWriteRequest.md) |  | |

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

