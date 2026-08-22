
# ProjectCreate


## Properties

Name | Type
------------ | -------------
`teamId` | string
`name` | string
`slug` | string
`description` | string
`workDir` | string
`gitRepoUrl` | string
`defaultModel` | string

## Example

```typescript
import type { ProjectCreate } from ''

// TODO: Update the object below with actual values
const example = {
  "teamId": null,
  "name": null,
  "slug": null,
  "description": null,
  "workDir": null,
  "gitRepoUrl": null,
  "defaultModel": null,
} satisfies ProjectCreate

console.log(example)

// Convert the instance to a JSON string
const exampleJSON: string = JSON.stringify(example)
console.log(exampleJSON)

// Parse the JSON string back to an object
const exampleParsed = JSON.parse(exampleJSON) as ProjectCreate
console.log(exampleParsed)
```

[[Back to top]](#) [[Back to API list]](../README.md#api-endpoints) [[Back to Model list]](../README.md#models) [[Back to README]](../README.md)


