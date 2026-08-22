
# ActivityResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`projectId` | string
`userId` | string
`username` | string
`displayName` | string
`type` | string
`payload` | string
`createdAt` | string

## Example

```typescript
import type { ActivityResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "projectId": null,
  "userId": null,
  "username": null,
  "displayName": null,
  "type": null,
  "payload": null,
  "createdAt": null,
} satisfies ActivityResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ActivityResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


