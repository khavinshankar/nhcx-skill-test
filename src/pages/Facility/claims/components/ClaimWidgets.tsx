import { Copy } from "lucide-react";
import { ReactNode, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { cn } from "@/lib/utils";

import { Badge } from "@/components/ui/badge";
import { Button, ButtonVariant } from "@/components/ui/button";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

import ConfirmActionDialog from "@/components/Common/ConfirmActionDialog";

import { TONE_VARIANT, Tone } from "@/pages/Facility/claims/utils";

export function Chip({
  tone,
  children,
  className,
}: {
  tone: Tone;
  children: ReactNode;
  className?: string;
}) {
  return (
    <Badge variant={TONE_VARIANT[tone]} className={cn("rounded-sm", className)}>
      {children}
    </Badge>
  );
}

// "Correlation id": shown in full on hover, copied on a click (S6).
export function CorrelationId({ value }: { value?: string | null }) {
  const { t } = useTranslation();
  if (!value) return <span>-</span>;
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <button
          type="button"
          className="inline-flex max-w-full items-center gap-1 font-mono text-xs text-gray-700 hover:text-primary-700"
          onClick={() => {
            navigator.clipboard?.writeText(value);
            toast.success(t("nhcx_copied"));
          }}
        >
          <span className="truncate">{value}</span>
          <Copy className="size-3 shrink-0" />
        </button>
      </TooltipTrigger>
      <TooltipContent>{value}</TooltipContent>
    </Tooltip>
  );
}

export interface DetailItem {
  label: string;
  value: ReactNode;
}

export function DetailList({
  items,
  columns = 3,
}: {
  items: DetailItem[];
  columns?: 2 | 3;
}) {
  return (
    <dl
      className={cn(
        "grid grid-cols-1 gap-x-6 gap-y-3 sm:grid-cols-2",
        columns === 3 && "lg:grid-cols-3",
      )}
    >
      {items.map((item) => (
        <div key={item.label} className="min-w-0">
          <dt className="text-xs font-medium text-gray-500">{item.label}</dt>
          <dd className="text-sm text-gray-900 break-words">
            {item.value === null ||
            item.value === undefined ||
            item.value === ""
              ? "-"
              : item.value}
          </dd>
        </div>
      ))}
    </dl>
  );
}

export function StatTile({
  label,
  value,
  tone,
}: {
  label: string;
  value: ReactNode;
  tone?: Tone;
}) {
  return (
    <div
      className={cn(
        "rounded-md border bg-white p-3",
        tone === "success" && "border-green-300 bg-green-50",
        tone === "warning" && "border-yellow-300 bg-yellow-50",
        tone === "danger" && "border-red-300 bg-red-50",
      )}
    >
      <div className="text-xs font-medium text-gray-500">{label}</div>
      <div className="text-lg font-semibold text-gray-900">{value}</div>
    </div>
  );
}

export function StatGrid({ children }: { children: ReactNode }) {
  return (
    <div className="grid grid-cols-2 gap-3 lg:grid-cols-3">{children}</div>
  );
}

export function Muted({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return <p className={cn("text-sm text-gray-500", className)}>{children}</p>;
}

export function ErrorText({ children }: { children: ReactNode }) {
  return <p className="text-sm text-red-700 whitespace-pre-wrap">{children}</p>;
}

// A button that asks for confirmation first when `confirm` is set.
export function ConfirmButton({
  confirm,
  title,
  onConfirm,
  children,
  variant = "primary",
  size = "sm",
  disabled,
  className,
}: {
  confirm?: string;
  title?: string;
  onConfirm: () => void;
  children: ReactNode;
  variant?: ButtonVariant;
  size?: "sm" | "default" | "xs";
  disabled?: boolean;
  className?: string;
}) {
  const { t } = useTranslation();
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button
        type="button"
        variant={variant}
        size={size}
        disabled={disabled}
        className={className}
        onClick={() => (confirm ? setOpen(true) : onConfirm())}
      >
        {children}
      </Button>
      {confirm && (
        <ConfirmActionDialog
          open={open}
          onOpenChange={setOpen}
          title={title || t("confirm")}
          description={confirm}
          confirmText={t("confirm")}
          variant={variant === "destructive" ? "destructive" : "primary"}
          onConfirm={() => {
            setOpen(false);
            onConfirm();
          }}
        />
      )}
    </>
  );
}
