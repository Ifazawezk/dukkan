import { ChevronLeft, ChevronRight } from "lucide-react";
import { useI18n } from "../i18n";
import { Button } from "./ui";

export function Pager({
  offset,
  limit,
  total,
  onChange,
}: {
  offset: number;
  limit: number;
  total: number;
  onChange: (offset: number) => void;
}) {
  const { t } = useI18n();
  if (total <= limit) return null;
  return (
    <div className="flex items-center justify-between border-t border-stone-100 px-4 py-3 text-sm text-stone-600">
      <span>
        {t("common.showing", { from: offset + 1, to: Math.min(offset + limit, total), total })}
      </span>
      <div className="flex gap-2">
        <Button
          size="sm"
          variant="secondary"
          disabled={offset === 0}
          onClick={() => onChange(Math.max(0, offset - limit))}
          icon={<ChevronLeft className="size-4 rtl:-scale-x-100" />}
        >
          {t("common.previous")}
        </Button>
        <Button
          size="sm"
          variant="secondary"
          disabled={offset + limit >= total}
          onClick={() => onChange(offset + limit)}
        >
          {t("common.next")}
          <ChevronRight className="size-4 rtl:-scale-x-100" />
        </Button>
      </div>
    </div>
  );
}
