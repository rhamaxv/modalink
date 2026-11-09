import { describe, expect, it, vi } from "vitest";
import { ApiError, api } from "@/lib/api";

function responsPalsu(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

describe("api client", () => {
  it("menerjemahkan bentuk error backend menjadi ApiError", async () => {
    vi.stubGlobal("fetch", () => responsPalsu(409, {
      error: { code: "pledge_melebihi_sisa",
               message: "Pledge melebihi sisa dana yang dibutuhkan, sisa Rp3.000.000.",
               detail: { remaining_amount: 3_000_000 } },
    }));

    await expect(api.post("/pledges", {})).rejects.toMatchObject({
      code: "pledge_melebihi_sisa",
      status: 409,
      detail: { remaining_amount: 3_000_000 },
    });
  });

  it("respons error tanpa bentuk yang dikenal tetap jadi ApiError", async () => {
    vi.stubGlobal("fetch", () => responsPalsu(502, "<html>Bad Gateway</html>"));
    await expect(api.get("/apa-saja")).rejects.toBeInstanceOf(ApiError);
  });

  it("jaringan putus menghasilkan pesan yang bisa dibaca pengguna", async () => {
    vi.stubGlobal("fetch", () => Promise.reject(new TypeError("Failed to fetch")));
    await expect(api.get("/apa-saja")).rejects.toMatchObject({
      code: "jaringan_bermasalah",
    });
  });
});
