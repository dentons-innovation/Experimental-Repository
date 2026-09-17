import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

export interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title?: ReactNode;
  description?: ReactNode;
  children: ReactNode;
  footer?: ReactNode;
  maxWidth?: string | number;
  className?: string;
  "aria-label"?: string;
}

let lastFocusedOutsideModal: HTMLElement | null = null;

if (typeof document !== "undefined") {
  document.addEventListener(
    "focusin",
    (e) => {
      const target = e.target as HTMLElement | null;
      if (target && !target.closest?.(".modal-content")) {
        lastFocusedOutsideModal = target;
      }
    },
    true,
  );
}

export function Modal({
  isOpen,
  onClose,
  title,
  description,
  children,
  footer,
  maxWidth = 560,
  className = "",
  "aria-label": ariaLabel,
}: ModalProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  const previousActiveElementRef = useRef<HTMLElement | null>(null);

  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  const id = useId();
  const titleId = `modal-title-${id.replace(/:/g, "")}`;
  const descId = `modal-desc-${id.replace(/:/g, "")}`;

  // Focus management: store previous active element, trap focus, restore on close
  useEffect(() => {
    if (!isOpen) return;

    if (lastFocusedOutsideModal) {
      previousActiveElementRef.current = lastFocusedOutsideModal;
    }

    // Move focus inside dialog
    const timer = setTimeout(() => {
      if (!contentRef.current) return;
      const autofocusEl =
        contentRef.current.querySelector<HTMLElement>("[autofocus]");
      if (autofocusEl) {
        autofocusEl.focus();
        return;
      }
      const bodyInput = contentRef.current.querySelector<HTMLElement>(
        ".modal-body input:not([disabled]), .modal-body textarea:not([disabled]), .modal-body select:not([disabled])",
      );
      if (bodyInput) {
        bodyInput.focus();
        return;
      }
      const focusable = contentRef.current.querySelectorAll<HTMLElement>(
        'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
      );
      if (focusable.length > 0 && focusable[0]) {
        focusable[0].focus();
      } else {
        contentRef.current.focus();
      }
    }, 0);

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }

      if (e.key === "Tab" && contentRef.current) {
        const focusable = Array.from(
          contentRef.current.querySelectorAll<HTMLElement>(
            'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
          ),
        ).filter(
          (el) =>
            el.offsetParent !== null ||
            el.offsetWidth > 0 ||
            el.offsetHeight > 0,
        );

        if (focusable.length === 0) {
          e.preventDefault();
          return;
        }

        const first = focusable[0];
        const last = focusable[focusable.length - 1];

        if (e.shiftKey) {
          if (
            document.activeElement === first ||
            !contentRef.current.contains(document.activeElement)
          ) {
            e.preventDefault();
            last?.focus();
          }
        } else {
          if (
            document.activeElement === last ||
            !contentRef.current.contains(document.activeElement)
          ) {
            e.preventDefault();
            first?.focus();
          }
        }
      }
    };

    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    window.addEventListener("keydown", handleKeyDown);

    return () => {
      clearTimeout(timer);
      document.body.style.overflow =
        prevOverflow === "hidden" ? "" : prevOverflow;
      window.removeEventListener("keydown", handleKeyDown);
      const toRestore = previousActiveElementRef.current;
      if (toRestore && typeof toRestore.focus === "function") {
        setTimeout(() => {
          toRestore.focus();
        }, 0);
      }
    };
  }, [isOpen]);

  if (!isOpen) return null;

  return createPortal(
    <div
      className="modal-overlay"
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        ref={contentRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={title ? titleId : undefined}
        aria-describedby={description ? descId : undefined}
        aria-label={!title ? ariaLabel : undefined}
        tabIndex={-1}
        className={`modal-content ${className}`}
        style={{ maxWidth, outline: "none" }}
        onClick={(e) => e.stopPropagation()}
      >
        {title && (
          <div className="modal-header">
            <div>
              <h2 id={titleId} className="modal-title">
                {title}
              </h2>
              {description && (
                <p
                  id={descId}
                  className="text-secondary text-sm"
                  style={{ marginTop: "4px" }}
                >
                  {description}
                </p>
              )}
            </div>
            <button
              type="button"
              className="btn btn-ghost btn-icon"
              onClick={onClose}
              aria-label="Close dialog"
            >
              <X size={16} />
            </button>
          </div>
        )}

        <div className="modal-body">{children}</div>

        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>,
    document.body,
  );
}

export function ModalHeader({
  title,
  description,
  onClose,
  titleId,
  descriptionId,
}: {
  title: ReactNode;
  description?: ReactNode;
  onClose?: () => void;
  titleId?: string;
  descriptionId?: string;
}) {
  return (
    <div className="modal-header">
      <div>
        <h2 id={titleId} className="modal-title">
          {title}
        </h2>
        {description && (
          <p
            id={descriptionId}
            className="text-secondary text-sm"
            style={{ marginTop: "4px" }}
          >
            {description}
          </p>
        )}
      </div>
      {onClose && (
        <button
          type="button"
          className="btn btn-ghost btn-icon"
          onClick={onClose}
          aria-label="Close dialog"
        >
          <X size={16} />
        </button>
      )}
    </div>
  );
}

export function ModalBody({ children }: { children: ReactNode }) {
  return <div className="modal-body">{children}</div>;
}

export function ModalFooter({ children }: { children: ReactNode }) {
  return <div className="modal-footer">{children}</div>;
}
