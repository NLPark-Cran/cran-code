declare const __CRAN_CLI_VERSION__: string | undefined;

export const cranCliVersion =
  typeof __CRAN_CLI_VERSION__ !== "undefined" && __CRAN_CLI_VERSION__
    ? __CRAN_CLI_VERSION__
    : "dev";
