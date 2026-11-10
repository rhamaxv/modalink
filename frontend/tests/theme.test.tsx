import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { ThemeToggle } from "@/components/ThemeToggle";

beforeEach(() => {
  document.documentElement.removeAttribute("data-theme");
  localStorage.clear();
});

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
  localStorage.clear();
});

// Gelap adalah default (DESIGN.md), jadi tidak adanya atribut data-theme
// BERARTI gelap, dan yang ditulis ke <html> adalah "light" ketika pengguna
// memintanya. Arah ini pernah terbalik, dan membaliknya kembali tanpa
// membalik test juga akan membuat skrip no-flash menulis atribut yang salah
// sementara suite tetap hijau.
describe("theme toggle", () => {
  it("writes data-theme on the html element only when leaving the default", async () => {
    render(<ThemeToggle />);
    expect(document.documentElement.dataset.theme).toBeUndefined();
    await userEvent.click(screen.getByRole("button", { name: /tema/i }));
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("can be operated with the keyboard", async () => {
    render(<ThemeToggle />);
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("persists the choice and restores it", () => {
    localStorage.setItem("theme", "light");
    render(<ThemeToggle />);
    expect(document.documentElement.dataset.theme).toBe("light");
  });

  it("returns to the dark default on a second activation", async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button", { name: /tema/i });
    await userEvent.click(button);
    expect(document.documentElement.dataset.theme).toBe("light");
    await userEvent.click(button);
    expect(document.documentElement.dataset.theme).toBeUndefined();
  });

  it("aria-pressed reflects the current theme state", async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button", { name: /tema/i });
    expect(button).toHaveAttribute("aria-pressed", "true");
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "false");
  });
});
