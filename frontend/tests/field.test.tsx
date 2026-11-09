import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Field } from "@/components/ui/Field";

describe("field", () => {
  it("exposes the required state to assistive technology, not only as a visual asterisk", () => {
    render(<Field label="Email" value="" onChange={() => {}} required />);
    expect(screen.getByLabelText(/email/i)).toBeRequired();
  });

  it("does not mark an optional input as required", () => {
    render(<Field label="Email" value="" onChange={() => {}} />);
    expect(screen.getByLabelText(/email/i)).not.toBeRequired();
  });

  it("exposes the required state on the select variant too", () => {
    render(
      <Field
        label="Peran"
        value="investor"
        onChange={() => {}}
        options={[{ value: "investor", label: "Investor" }]}
        required
      />,
    );
    expect(screen.getByLabelText(/peran/i)).toBeRequired();
  });
});
