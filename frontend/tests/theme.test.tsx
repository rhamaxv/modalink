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

describe("theme toggle", () => {
  it("changes data-theme on the html element", async () => {
    render(<ThemeToggle />);
    await userEvent.click(screen.getByRole("button", { name: /tema/i }));
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("can be operated with the keyboard", async () => {
    render(<ThemeToggle />);
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("persists the choice and restores it", () => {
    localStorage.setItem("theme", "dark");
    render(<ThemeToggle />);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("aria-pressed reflects the current theme state", async () => {
    render(<ThemeToggle />);
    const button = screen.getByRole("button", { name: /tema/i });
    expect(button).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(button);
    expect(button).toHaveAttribute("aria-pressed", "true");
  });
});
