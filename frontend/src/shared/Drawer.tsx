import { useEffect, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";

/** Modal evidence surface; source records remain unmodified and inspectable. */
export function Drawer({
  children,
  label,
  onClose,
}: {
  children: ReactNode;
  label: string;
  onClose: () => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const close = useRef(onClose);
  close.current = onClose;
  useEffect(() => {
    const previous = document.activeElement as HTMLElement | null;
    const overflow = document.body.style.overflow;
    const siblings = [...document.body.children].filter(
      (el): el is HTMLElement =>
        el instanceof HTMLElement && !el.contains(ref.current),
    );
    const states = siblings.map((el) => [el, el.inert] as const);
    states.forEach(([el]) => {
      el.inert = true;
    });
    document.body.style.overflow = "hidden";
    const initial = ref.current?.querySelector<HTMLElement>(".evidence-detail");
    initial?.setAttribute("tabindex", "-1");
    (initial ?? ref.current)?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        close.current();
      }
      if (e.key !== "Tab") return;
      const controls = ref.current?.querySelectorAll<HTMLElement>(
        "button:not(:disabled), a[href], select, input, textarea, [tabindex='0']",
      );
      const first = controls?.[0],
        last = controls?.[controls.length - 1];
      if (!first || !last) {
        e.preventDefault();
        return;
      }
      if (
        e.shiftKey &&
        (document.activeElement === first ||
          document.activeElement === ref.current ||
          document.activeElement === initial)
      ) {
        e.preventDefault();
        last.focus();
      } else if (
        !e.shiftKey &&
        (document.activeElement === last ||
          document.activeElement === ref.current ||
          document.activeElement === initial)
      ) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKey);
    return () => {
      document.body.style.overflow = overflow;
      states.forEach(([el, inert]) => {
        el.inert = inert;
      });
      document.removeEventListener("keydown", onKey);
      previous?.focus();
    };
  }, []);
  return createPortal(
    <div className="drawer-layer">
      <div
        className="evidence-drawer-backdrop"
        aria-hidden="true"
        onClick={onClose}
      />
      <div
        ref={ref}
        className="evidence-drawer"
        role="dialog"
        aria-modal="true"
        aria-label={label}
        tabIndex={-1}
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}
