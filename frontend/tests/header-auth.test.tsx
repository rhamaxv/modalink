import { readdirSync, statSync } from "node:fs";
import path from "node:path";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { AppHeader } from "@/components/AppHeader";
import { NavRole } from "@/components/NavRole";
import { RequireRole } from "@/components/RouteGuard";
import Masuk from "@/app/(auth)/masuk/page";
import Daftar from "@/app/(auth)/daftar/page";
import MyCampaignsPage from "@/app/investor/campaign/page";

const { push, replace, notFound, getCurrentPathname, setCurrentPathname } = vi.hoisted(() => {
  let pathname = "/investor/milestone";
  return {
    push: vi.fn(),
    replace: vi.fn(),
    // Tidak melempar error sungguhan di sini: notFound() asli melempar
    // error bertanda khusus yang ditangkap boundary Next.js, tapi tidak ada
    // boundary semacam itu di lingkungan jsdom test ini. Bukti bahwa 404
    // sungguhan muncul di browser ada di e2e/auth-guard.spec.ts; test unit
    // ini hanya membuktikan RequireRole memanggil notFound() pada kondisi
    // yang tepat, bukan membuktikan ulang perilaku Next.js sendiri.
    notFound: vi.fn(),
    getCurrentPathname: () => pathname,
    setCurrentPathname: (next: string) => {
      pathname = next;
    },
  };
});

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push, replace, refresh: vi.fn() }),
  usePathname: () => getCurrentPathname(),
  useSearchParams: () => new URLSearchParams(),
  notFound,
}));

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

afterEach(() => {
  push.mockClear();
  replace.mockClear();
  notFound.mockClear();
  vi.unstubAllGlobals();
  try {
    localStorage.clear();
  } catch {
    // jsdom selalu punya localStorage di test; abaikan kalau tidak.
  }
});

describe("AppHeader appears on every route", () => {
  it("renders the header with ThemeToggle alongside three unrelated pages, unconditionally", () => {
    const pages = [<Masuk key="masuk" />, <Daftar key="daftar" />, <MyCampaignsPage key="campaign" />];
    pages.forEach((page) => {
      const { unmount } = render(
        <>
          <AppHeader />
          {page}
        </>,
      );
      expect(screen.getByText("Modalink")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: /tema/i })).toBeInTheDocument();
      unmount();
    });
  });
});

describe("RequireRole", () => {
  it("redirects a signed-out visitor to /masuk, keeping the originally intended page", async () => {
    vi.stubGlobal("fetch", vi.fn(() => fakeResponse(401, { error: { code: "tidak_sah", message: "Tidak sah" } })));
    setCurrentPathname("/investor/milestone");
    render(
      <RequireRole role="investor">
        <p>Konten investor</p>
      </RequireRole>,
    );
    await waitFor(() => expect(replace).toHaveBeenCalledWith("/masuk?next=%2Finvestor%2Fmilestone"));
    expect(screen.queryByText("Konten investor")).not.toBeInTheDocument();
  });

  it("gives a role mismatch a 404, not a 403, matching the backend's pattern", async () => {
    localStorage.setItem("modalink_token", "token-investor");
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        fakeResponse(200, {
          id: "u1",
          email: "investor@contoh.id",
          name: "Investor Satu",
          role: "investor",
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );
    render(
      <RequireRole role="umkm">
        <p>Konten UMKM</p>
      </RequireRole>,
    );
    await waitFor(() => expect(notFound).toHaveBeenCalled());
    expect(replace).not.toHaveBeenCalled();
  });

  it("renders its children once the signed-in account matches the required role", async () => {
    localStorage.setItem("modalink_token", "token-investor");
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        fakeResponse(200, {
          id: "u1",
          email: "investor@contoh.id",
          name: "Investor Satu",
          role: "investor",
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );
    render(
      <RequireRole role="investor">
        <p>Konten investor</p>
      </RequireRole>,
    );
    expect(await screen.findByText("Konten investor")).toBeInTheDocument();
    expect(replace).not.toHaveBeenCalled();
    expect(notFound).not.toHaveBeenCalled();
  });
});

describe("sign out", () => {
  it("clears the token and sends the visitor to / when Keluar is clicked", async () => {
    localStorage.setItem("modalink_token", "token-investor");
    vi.stubGlobal(
      "fetch",
      vi.fn(() =>
        fakeResponse(200, {
          id: "u1",
          email: "investor@contoh.id",
          name: "Investor Satu",
          role: "investor",
          created_at: "2026-01-01T00:00:00Z",
        }),
      ),
    );
    render(<AppHeader />);
    await screen.findByRole("button", { name: /keluar/i });
    await userEvent.click(screen.getByRole("button", { name: /keluar/i }));
    expect(localStorage.getItem("modalink_token")).toBeNull();
    expect(push).toHaveBeenCalledWith("/");
  });
});

describe("a malformed stored token is treated as signed out", () => {
  it("does not call the API and shows the guest nav for the literal string \"undefined\"", async () => {
    localStorage.setItem("modalink_token", "undefined");
    const fetchSpy = vi.fn(() => fakeResponse(200, {}));
    vi.stubGlobal("fetch", fetchSpy);
    render(<AppHeader />);
    expect(await screen.findByRole("link", { name: /masuk/i })).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

describe("navigation differs by role, and no link points at a route that does not exist", () => {
  // Rute ini dibangun stream lain di worktree lain (f11-c), tapi rutenya
  // nyata: struktur filenya sudah dikunci di .claude/plan/phase-11-frontend-alur.md
  // (dikutip juga di brief f11-d1) sebelum tiga stream dibuka paralel.
  // Pagar ini menyatukan dua sumber yang sama validnya: rute yang memang
  // ada di worktree ini (dibaca dari filesystem, bukan ditulis tangan,
  // supaya rute yang dihapus ikut tertangkap) dan rute yang pasti ada
  // begitu stream itu bergabung (didaftar di sini, bernama dan diberi
  // alasan, bukan ditebak atau diabaikan).
  const UMKM_ROUTES_UNDER_CONSTRUCTION = [
    "/umkm/beranda",
    "/umkm/proposal/baru",
    "/umkm/milestone/[id]/lapor",
  ];

  function collectAppRoutes(dir: string, segments: string[] = []): string[] {
    const found: string[] = [];
    for (const entry of readdirSync(dir)) {
      const fullPath = path.join(dir, entry);
      if (statSync(fullPath).isDirectory()) {
        const isGroup = entry.startsWith("(") && entry.endsWith(")");
        found.push(...collectAppRoutes(fullPath, isGroup ? segments : [...segments, entry]));
      } else if (entry === "page.tsx") {
        found.push(`/${segments.join("/")}`);
      }
    }
    return found;
  }

  function routeToPattern(route: string): RegExp {
    const body = route
      .split("/")
      .map((segment) => (segment.startsWith("[") ? "[^/]+" : segment.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")))
      .join("/");
    return new RegExp(`^${body}$`);
  }

  function knownRoutePatterns(): RegExp[] {
    const routes = [...collectAppRoutes(path.resolve("app")), ...UMKM_ROUTES_UNDER_CONSTRUCTION];
    return routes.map(routeToPattern);
  }

  function expectEveryLinkToResolve(hrefs: string[]) {
    const patterns = knownRoutePatterns();
    hrefs.forEach((href) => {
      const path_ = href.split("#")[0] ?? href;
      if (!path_.startsWith("/")) return;
      expect(patterns.some((pattern) => pattern.test(path_))).toBe(true);
    });
  }

  it("shows the investor's own nav items, none of them dead", () => {
    render(<NavRole role="investor" />);
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href") ?? "");
    expect(hrefs.length).toBeGreaterThan(0);
    expectEveryLinkToResolve(hrefs);
  });

  it("shows the UMKM's own nav items, distinct from the investor's, none of them dead", () => {
    render(<NavRole role="umkm" />);
    const hrefs = screen.getAllByRole("link").map((a) => a.getAttribute("href") ?? "");
    expect(hrefs.length).toBeGreaterThan(0);
    expectEveryLinkToResolve(hrefs);
    expect(hrefs.some((href) => href.startsWith("/investor"))).toBe(false);
  });

  it("shows no role-specific nav item for the community role", () => {
    const { container } = render(<NavRole role="community" />);
    expect(container.querySelectorAll("a")).toHaveLength(0);
  });

  it("proves the guard actually fails on a fabricated route (checked, then reverted)", () => {
    // Pembuktian bahwa pagar ini bisa merah, bukan hanya dijalankan sekali
    // dan dipercaya: tautan ke rute karangan yang sengaja tidak pernah
    // dibuat di mana pun, termasuk daftar rute umkm di atas.
    expect(() => expectEveryLinkToResolve(["/investor/rute-karangan-yang-tidak-pernah-dibuat"])).toThrow();
  });
});
