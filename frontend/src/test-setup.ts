import "@testing-library/jest-dom/vitest";
import { afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
afterEach(cleanup);
class ResizeObserverStub {
  observe() {}
  unobserve() {}
  disconnect() {}
}
vi.stubGlobal("ResizeObserver", ResizeObserverStub);
// jsdom has no layout; provide deterministic chart container dimensions.
Object.defineProperty(HTMLElement.prototype, "getBoundingClientRect", {
  value() {
    return {
      width: 600,
      height: 220,
      top: 0,
      left: 0,
      bottom: 220,
      right: 600,
      x: 0,
      y: 0,
      toJSON() {
        return {};
      },
    };
  },
});
