import {
  forwardRef,
  type InputHTMLAttributes,
  type TextareaHTMLAttributes,
  type SelectHTMLAttributes,
  type ReactNode,
} from "react";

export interface FormFieldProps {
  label?: ReactNode;
  htmlFor?: string;
  required?: boolean;
  error?: string | null;
  helperText?: string;
  children: ReactNode;
  className?: string;
}

export function FormField({
  label,
  htmlFor,
  required,
  error,
  helperText,
  children,
  className = "",
}: FormFieldProps) {
  return (
    <div className={`form-group ${className}`}>
      {label && (
        <label className="input-label" htmlFor={htmlFor}>
          {label}
          {required && (
            <span
              style={{ color: "var(--color-danger)", marginLeft: "4px" }}
              aria-hidden="true"
            >
              *
            </span>
          )}
        </label>
      )}
      {children}
      {error && (
        <span
          style={{
            fontSize: "12px",
            color: "var(--color-danger)",
            marginTop: "4px",
            display: "block",
          }}
          role="alert"
        >
          {error}
        </span>
      )}
      {!error && helperText && (
        <span
          style={{
            fontSize: "12px",
            color: "var(--color-text-tertiary)",
            marginTop: "4px",
            display: "block",
          }}
        >
          {helperText}
        </span>
      )}
    </div>
  );
}

export interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  hasError?: boolean;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", hasError, ...props }, ref) => {
    return (
      <input
        ref={ref}
        className={`input ${hasError ? "input-error" : ""} ${className}`}
        {...props}
      />
    );
  },
);
Input.displayName = "Input";

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  hasError?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className = "", hasError, ...props }, ref) => {
    return (
      <textarea
        ref={ref}
        className={`input textarea ${hasError ? "input-error" : ""} ${className}`}
        {...props}
      />
    );
  },
);
Textarea.displayName = "Textarea";

export interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  hasError?: boolean;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className = "", hasError, children, ...props }, ref) => {
    return (
      <select
        ref={ref}
        className={`input select ${hasError ? "input-error" : ""} ${className}`}
        {...props}
      >
        {children}
      </select>
    );
  },
);
Select.displayName = "Select";
