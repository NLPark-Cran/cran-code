declare module "shiki/langs/*" {
  const lang: import("@shikijs/core").LanguageRegistration;
  export default lang;
}

declare module "shiki/themes/*" {
  const theme: import("@shikijs/core").ThemeRegistration;
  export default theme;
}
