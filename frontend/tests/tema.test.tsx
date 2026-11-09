import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { SakelarTema } from "@/components/SakelarTema";

beforeEach(() => {
  document.documentElement.removeAttribute("data-theme");
  localStorage.clear();
});

afterEach(() => {
  document.documentElement.removeAttribute("data-theme");
  localStorage.clear();
});

describe("sakelar tema", () => {
  it("mengubah data-theme di elemen html", async () => {
    render(<SakelarTema />);
    await userEvent.click(screen.getByRole("button", { name: /tema/i }));
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("bisa dioperasikan dengan keyboard", async () => {
    render(<SakelarTema />);
    await userEvent.tab();
    await userEvent.keyboard("{Enter}");
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("menyimpan pilihan dan memulihkannya", () => {
    localStorage.setItem("tema", "dark");
    render(<SakelarTema />);
    expect(document.documentElement.dataset.theme).toBe("dark");
  });

  it("aria-pressed mencerminkan status tema saat ini", async () => {
    render(<SakelarTema />);
    const tombol = screen.getByRole("button", { name: /tema/i });
    expect(tombol).toHaveAttribute("aria-pressed", "false");
    await userEvent.click(tombol);
    expect(tombol).toHaveAttribute("aria-pressed", "true");
  });
});
