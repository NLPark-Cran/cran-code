import { describe, expect, it } from "vitest";
import { resources } from "./index";

const namespaces = Object.keys(resources.zh) as (keyof typeof resources.zh)[];

describe("i18n key parity", () => {
  it("zh and en declare the same namespaces", () => {
    expect(Object.keys(resources.en).sort()).toEqual(namespaces.sort());
  });

  for (const ns of namespaces) {
    it(`namespace "${ns}" has identical keys in zh and en`, () => {
      const zhKeys = Object.keys(resources.zh[ns]).sort();
      const enKeys = Object.keys(resources.en[ns]).sort();
      expect(zhKeys).toEqual(enKeys);
    });

    it(`namespace "${ns}" has no empty values`, () => {
      for (const value of Object.values(resources.zh[ns])) {
        expect(typeof value).toBe("string");
        expect((value as string).trim().length).toBeGreaterThan(0);
      }
      for (const value of Object.values(resources.en[ns])) {
        expect(typeof value).toBe("string");
        expect((value as string).trim().length).toBeGreaterThan(0);
      }
    });
  }
});
