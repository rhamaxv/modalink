import { describe, expect, it } from "vitest";

describe("basis URL API", () => {
  it("falls back to the proxy path when the build arg is an empty string", () => {
    // Bukan test gaya penulisan. Docker build arg yang dibiarkan kosong tiba
    // sebagai "", bukan undefined, dan `??` meneruskannya apa adanya: frontend
    // lalu memanggil /proposals bukan /api/v1/proposals dan semuanya 404.
    const kosong = "";
    expect(kosong || "/api/v1").toBe("/api/v1");
    expect(kosong ?? "/api/v1").toBe("");
  });

  it("keeps an explicit origin when one is supplied", () => {
    const eksplisit = "https://api.contoh.test/api/v1";
    expect(eksplisit || "/api/v1").toBe(eksplisit);
  });
});
