
# TeamResponse


## Properties

Name | Type
------------ | -------------
`id` | string
`name` | string
`slug` | string
`description` | string
`timezone` | string
`ownerId` | string
`members` | [Array&lt;TeamMemberResponse&gt;](TeamMemberResponse.md)
`createdAt` | string

## Example

```typescript
import type { TeamResponse } from ''

// TODO: Update the object below with actual values
const example = {
  "id": null,
  "name": null,
  "slug": null,
  "description": null,
  "timezone": null,
  "ownerId": null,
  "members": null,
  "createdAt": null,
} satisfies TeamResponse

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as TeamResponse
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


