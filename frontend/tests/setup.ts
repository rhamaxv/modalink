import { cleanup } from "@testing-library/react";
import { afterEach } from "vitest";
import "@testing-library/jest-dom/vitest";

// vitest.config.ts tidak mengaktifkan `globals`, jadi testing-library tidak
// menemukan `afterEach` global untuk auto-cleanup-nya sendiri. Didaftarkan
// manual di sini supaya render dari satu test tidak bocor ke test berikutnya.
afterEach(() => {
  cleanup();
});
