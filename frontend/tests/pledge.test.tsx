import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { FundingBar } from "@/components/FundingBar";
import { PledgeForm } from "@/components/PledgeForm";

function fakeResponse(status: number, body: unknown) {
  return Promise.resolve(new Response(JSON.stringify(body), { status }));
}

async function fillAndSubmit(nilai: string) {
  await userEvent.type(screen.getByLabelText(/nominal/i), nilai);
  await userEvent.click(screen.getByRole("button", { name: /danai/i }));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("funding bar", () => {
  it("shows raised, target, and remaining amounts", () => {
    render(<FundingBar terkumpul={4_000_000} target={10_000_000} pendana={2} />);
    expect(screen.getByText("Rp4.000.000")).toBeInTheDocument();
    expect(screen.getByText(/dari Rp10.000.000/)).toBeInTheDocument();
    expect(screen.getByText(/sisa Rp6.000.000/i)).toBeInTheDocument();
  });

  it("names the number of funders, because co-funding is the point", () => {
    render(<FundingBar terkumpul={4_000_000} target={10_000_000} pendana={3} />);
    expect(screen.getByText(/3 investor/i)).toBeInTheDocument();
  });

  it("exposes progress to screen readers via progressbar, not only a div's width", () => {
    render(<FundingBar terkumpul={4_000_000} target={10_000_000} pendana={1} />);
    const bar = screen.getByRole("progressbar");
    expect(bar).toHaveAttribute("aria-valuenow", "40");
    expect(bar).toHaveAttribute("aria-valuetext", "Rp4.000.000 dari Rp10.000.000");
  });
});

describe("pledge form", () => {
  it("shows the remaining amount before the user types anything", () => {
    render(<PledgeForm sisa={6_000_000} />);
    expect(screen.getByText(/maksimal Rp6.000.000/i)).toBeInTheDocument();
  });

  it("warns before submit when the amount exceeds the remaining need", async () => {
    render(<PledgeForm sisa={6_000_000} />);
    await userEvent.type(screen.getByLabelText(/nominal/i), "7000000");
    expect(screen.getByRole("button", { name: /danai/i })).toBeDisabled();
    expect(screen.getByRole("status")).toHaveTextContent(/melebihi sisa/i);
  });

  it("shows the backend message as is when the server rejects a funding race", async () => {
    // Investor lain mendahului; klien tidak bisa mencegahnya, hanya menjelaskannya.
    vi.stubGlobal("fetch", () =>
      fakeResponse(409, {
        error: {
          code: "pledge_melebihi_sisa",
          message: "Pledge melebihi sisa dana yang dibutuhkan, sisa Rp1.000.000.",
          detail: { remaining_amount: 1_000_000 },
        },
      }),
    );
    render(<PledgeForm sisa={6_000_000} />);
    await fillAndSubmit("5000000");
    expect(await screen.findByRole("alert")).toHaveTextContent("sisa Rp1.000.000");
  });

  it("updates the remaining amount from the error detail after a rejection", async () => {
    vi.stubGlobal("fetch", () =>
      fakeResponse(409, {
        error: {
          code: "pledge_melebihi_sisa",
          message: "Pledge melebihi sisa dana yang dibutuhkan, sisa Rp1.000.000.",
          detail: { remaining_amount: 1_000_000 },
        },
      }),
    );
    render(<PledgeForm sisa={6_000_000} />);
    await fillAndSubmit("5000000");
    expect(await screen.findByText(/maksimal Rp1.000.000/i)).toBeInTheDocument();
  });
});
