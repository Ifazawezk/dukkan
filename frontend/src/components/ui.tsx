import { X } from "lucide-react";
import { useEffect, useId } from "react";
import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";

function cx(...classes: (string | false | null | undefined)[]) {
  return classes.filter(Boolean).join(" ");
}

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variants: Record<Variant, string> = {
  primary: "bg-brand-700 text-white hover:bg-brand-800 disabled:bg-brand-300",
  secondary:
    "bg-white text-stone-800 ring-1 ring-stone-300 hover:bg-stone-50 disabled:text-stone-400",
  ghost: "text-stone-700 hover:bg-stone-200/70 disabled:text-stone-400",
  danger: "bg-red-600 text-white hover:bg-red-700 disabled:bg-red-300",
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: "sm" | "md" | "lg";
  icon?: ReactNode;
}

export function Button({
  variant = "primary",
  size = "md",
  icon,
  className,
  children,
  type = "button",
  ...props
}: ButtonProps) {
  const sizes = { sm: "h-8 px-3 text-sm", md: "h-10 px-4 text-sm", lg: "h-12 px-5 text-base" };
  return (
    <button
      type={type}
      className={cx(
        "inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-colors",
        "focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand-600",
        "disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    >
      {icon}
      {children}
    </button>
  );
}

const fieldClass =
  "w-full rounded-lg border border-stone-300 bg-white px-3 h-10 text-sm text-stone-900 " +
  "placeholder:text-stone-400 focus:border-brand-600 focus:outline-none focus:ring-2 " +
  "focus:ring-brand-600/20 disabled:bg-stone-100";

interface FieldProps {
  label?: string;
  hint?: string;
  error?: string;
}

export function Input({
  label,
  hint,
  error,
  className,
  id,
  ...props
}: FieldProps & InputHTMLAttributes<HTMLInputElement>) {
  const autoId = useId();
  const inputId = id ?? autoId;
  return (
    <div className={className}>
      {label && (
        <label htmlFor={inputId} className="mb-1 block text-sm font-medium text-stone-700">
          {label}
        </label>
      )}
      <input id={inputId} className={cx(fieldClass, error && "border-red-500")} {...props} />
      {hint && !error && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Select({
  label,
  hint,
  error,
  className,
  id,
  children,
  ...props
}: FieldProps & SelectHTMLAttributes<HTMLSelectElement>) {
  const autoId = useId();
  const selectId = id ?? autoId;
  return (
    <div className={className}>
      {label && (
        <label htmlFor={selectId} className="mb-1 block text-sm font-medium text-stone-700">
          {label}
        </label>
      )}
      <select id={selectId} className={fieldClass} {...props}>
        {children}
      </select>
      {hint && <p className="mt-1 text-xs text-stone-500">{hint}</p>}
      {error && <p className="mt-1 text-xs text-red-600">{error}</p>}
    </div>
  );
}

export function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-stone-700">
      <input
        type="checkbox"
        className="size-4 rounded border-stone-300 accent-brand-700"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
      />
      {label}
    </label>
  );
}

export function Card({
  title,
  actions,
  children,
  className,
}: {
  title?: ReactNode;
  actions?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={cx("rounded-xl bg-white shadow-sm ring-1 ring-stone-200", className)}>
      {(title || actions) && (
        <header className="flex items-center justify-between gap-3 border-b border-stone-100 px-4 py-3">
          <h2 className="text-sm font-semibold text-stone-800">{title}</h2>
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

const tones = {
  gray: "bg-stone-100 text-stone-700",
  green: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
  red: "bg-red-50 text-red-700 ring-red-600/20",
  amber: "bg-amber-50 text-amber-800 ring-amber-600/20",
  blue: "bg-sky-50 text-sky-700 ring-sky-600/20",
  brand: "bg-brand-50 text-brand-700 ring-brand-600/20",
};

export function Badge({
  tone = "gray",
  children,
}: {
  tone?: keyof typeof tones;
  children: ReactNode;
}) {
  return (
    <span
      className={cx(
        "inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ring-stone-500/10",
        tones[tone],
      )}
    >
      {children}
    </span>
  );
}

export function Modal({
  open,
  title,
  onClose,
  children,
  footer,
  wide = false,
}: {
  open: boolean;
  title: ReactNode;
  onClose: () => void;
  children: ReactNode;
  footer?: ReactNode;
  wide?: boolean;
}) {
  useEffect(() => {
    if (!open) return;
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  if (!open) return null;
  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-stone-900/40 p-4 sm:items-center">
      <div
        role="dialog"
        aria-modal="true"
        className={cx(
          "w-full rounded-2xl bg-white shadow-xl ring-1 ring-stone-200",
          wide ? "max-w-3xl" : "max-w-lg",
        )}
      >
        <div className="flex items-center justify-between border-b border-stone-100 px-5 py-4">
          <h2 className="text-base font-semibold">{title}</h2>
          <button
            onClick={onClose}
            className="rounded-md p-1 text-stone-500 hover:bg-stone-100"
            aria-label="Close"
          >
            <X className="size-5" />
          </button>
        </div>
        <div className="px-5 py-4">{children}</div>
        {footer && (
          <div className="flex justify-end gap-2 border-t border-stone-100 px-5 py-3">{footer}</div>
        )}
      </div>
    </div>
  );
}

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}) {
  return (
    <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
      <div>
        <h1 className="text-xl font-semibold text-stone-900">{title}</h1>
        {subtitle && <p className="mt-0.5 text-sm text-stone-500">{subtitle}</p>}
      </div>
      {actions && <div className="flex flex-wrap gap-2">{actions}</div>}
    </div>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center justify-center gap-2 py-10 text-sm text-stone-500">
      <span className="size-4 animate-spin rounded-full border-2 border-stone-300 border-t-brand-700" />
      {label}
    </div>
  );
}

export function EmptyState({ children }: { children: ReactNode }) {
  return <div className="py-12 text-center text-sm text-stone-500">{children}</div>;
}

export function ErrorText({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof Error ? error.message : String(error);
  return (
    <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">
      {message}
    </p>
  );
}

const thBase = "px-4 py-2.5 text-xs font-semibold uppercase tracking-wide text-stone-500";
export const th = `${thBase} text-start`;
/** Header for a numeric column. */
export const thEnd = `${thBase} text-end`;
export const td = "px-4 py-2.5 text-sm text-stone-800";

export { cx };
