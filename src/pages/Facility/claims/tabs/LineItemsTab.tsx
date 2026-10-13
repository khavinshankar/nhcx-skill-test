import { Download, List, Plus, Save, SearchIcon, Undo2 } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";

import { AddLineRequest, ClaimLine, LineKind } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  ConfirmButton,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import { Tone, formatMoney, toNumber } from "@/pages/Facility/claims/utils";

const PAGE = 100;
const ALL = "__all";

export const LINE_KIND: Record<LineKind, { label: string; tone: Tone }> = {
  Procedure: { label: "nhcx_kind_procedure", tone: "info" },
  Implant: { label: "nhcx_kind_implant", tone: "warning" },
  Stratification: { label: "nhcx_kind_tier", tone: "neutral" },
};

interface LineRow {
  line: ClaimLine;
  tiers: ClaimLine[];
  amount: number;
}

// Tiers hang off their procedure (or the first remaining procedure).
export function groupLines(lines: ClaimLine[]): LineRow[] {
  const rows: LineRow[] = lines
    .filter((l) => l.kind !== "Stratification")
    .map((l) => ({ line: l, tiers: [], amount: toNumber(l.amount) ?? 0 }));
  const procedures = rows.filter((r) => r.line.kind === "Procedure");
  lines
    .filter((l) => l.kind === "Stratification")
    .forEach((tier) => {
      const host =
        procedures.find((r) => r.line.code === tier.parent_code) ??
        procedures[0];
      if (host) {
        host.tiers.push(tier);
        host.amount += toNumber(tier.amount) ?? 0;
      } else {
        rows.push({
          line: tier,
          tiers: [],
          amount: toNumber(tier.amount) ?? 0,
        });
      }
    });
  return rows;
}

export function linesTotal(lines: ClaimLine[]): number {
  return lines.reduce((sum, l) => sum + (toNumber(l.amount) ?? 0), 0);
}

const qty = (n: number | string) => String(Number(n));

function TierChips({
  tiers,
  onRemove,
}: {
  tiers: ClaimLine[];
  onRemove?: (line: ClaimLine) => void;
}) {
  const { t } = useTranslation();
  if (!tiers.length) return <>-</>;
  return (
    <div className="flex flex-col gap-1">
      {tiers.map((tier) => (
        <div key={tier.id} className="flex flex-wrap items-center gap-1">
          <Chip tone="neutral">
            {tier.display || tier.code} · {tier.code}
          </Chip>
          <span className="text-xs">+{formatMoney(tier.amount)}</span>
          {onRemove && (
            <ConfirmButton
              size="xs"
              variant="destructive"
              confirm={t("nhcx_remove_tier_confirm")}
              onConfirm={() => onRemove(tier)}
            >
              {t("remove")}
            </ConfirmButton>
          )}
        </div>
      ))}
    </div>
  );
}

// The read-only quoted lines table (S8, and the package box of S4).
export function QuotedLinesTable({
  lines,
  empty,
}: {
  lines: ClaimLine[];
  empty: string;
}) {
  const { t } = useTranslation();
  const rows = groupLines(lines);
  return (
    <>
      {!rows.length ? (
        <Muted>{empty}</Muted>
      ) : (
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>{t("nhcx_kind")}</TableHead>
                <TableHead>{t("nhcx_item")}</TableHead>
                <TableHead>{t("nhcx_kind_tier")}</TableHead>
                <TableHead className="text-right">{t("nhcx_rate")}</TableHead>
                <TableHead className="text-right">
                  {t("nhcx_quantity")}
                </TableHead>
                <TableHead className="text-right">{t("nhcx_amount")}</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rows.map(({ line, tiers, amount }) => (
                <TableRow key={line.id}>
                  <TableCell>
                    <Chip tone={LINE_KIND[line.kind]?.tone ?? "neutral"}>
                      {t(LINE_KIND[line.kind]?.label ?? line.kind)}
                    </Chip>
                  </TableCell>
                  <TableCell>
                    <div>{line.display || line.code}</div>
                    <div className="text-xs text-gray-500">{line.code}</div>
                  </TableCell>
                  <TableCell>
                    <TierChips tiers={tiers} />
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(line.unit_price)}
                  </TableCell>
                  <TableCell className="text-right">
                    {qty(line.quantity)}
                  </TableCell>
                  <TableCell className="text-right">
                    {formatMoney(amount)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
          <p className="mt-3 text-right font-semibold">
            {t("nhcx_total", { amount: formatMoney(linesTotal(lines)) })}
          </p>
        </div>
      )}
    </>
  );
}

// S8 Line Items tab, with the S8.1 picker.
export default function LineItemsTab(props: ClaimTabProps) {
  const { t } = useTranslation();
  const { state, goTo } = props;
  const [choosing, setChoosing] = useState(false);
  const ready = state.plan?.status === "ready";

  if (!ready) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_line_items")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">{t("nhcx_lines_need_plan")}</p>
          <Button variant="primary" onClick={() => goTo("plan")}>
            <Download className="size-4" />
            {t("nhcx_go_to_plan")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (choosing) {
    return <ChooseLines {...props} onBack={() => setChoosing(false)} />;
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <CardTitle>{t("nhcx_line_items")}</CardTitle>
        <Button variant="primary" size="sm" onClick={() => setChoosing(true)}>
          <List className="size-4" />
          {t("nhcx_choose_line_items")}
        </Button>
      </CardHeader>
      <CardContent>
        <QuotedLinesTable
          lines={state.lines}
          empty={t("nhcx_nothing_quoted")}
        />
      </CardContent>
    </Card>
  );
}

function ChooseLines({
  facilityId,
  claimId,
  state,
  onBack,
}: ClaimTabProps & { onBack: () => void }) {
  const { t } = useTranslation();
  const { benefits, lines } = state;
  const benefitByCode = useMemo(
    () => new Map(benefits.map((b) => [`${b.kind}:${b.code}`, b])),
    [benefits],
  );
  const rows = groupLines(lines);
  const quoted = new Set(lines.map((l) => l.code));

  const [edits, setEdits] = useState<
    Record<string, { quantity: string; price: string }>
  >({});
  useEffect(() => {
    setEdits(
      Object.fromEntries(
        lines.map((l) => [
          l.id,
          {
            quantity: qty(l.quantity),
            price: toNumber(l.unit_price) ? qty(l.unit_price as string) : "",
          },
        ]),
      ),
    );
  }, [lines]);

  const openPrice = (line: ClaimLine) => {
    if (line.kind === "Stratification") return false;
    const b = benefitByCode.get(`${line.kind}:${line.code}`);
    const rate = toNumber(b?.rate);
    return !rate;
  };

  const add = useClaimAction(claimId, (body: AddLineRequest) =>
    nhcxCall(nhcxApi.addLine, {
      pathParams: { facilityId, claimId },
      body,
    }),
  );
  const remove = useClaimAction(
    claimId,
    (lineId: string) =>
      nhcxCall(nhcxApi.removeLine, {
        pathParams: { facilityId, claimId, lineId },
      }),
    t("nhcx_line_removed"),
  );
  const update = useClaimAction(
    claimId,
    (bodies: AddLineRequest[]) =>
      Promise.all(
        bodies.map((body) =>
          nhcxCall(nhcxApi.addLine, {
            pathParams: { facilityId, claimId },
            body,
          }),
        ),
      ).then((all) => all.find((r) => r.ok === false) ?? { ok: true }),
    t("nhcx_lines_updated"),
  );

  const saveLines = (e: React.SyntheticEvent) => {
    e.preventDefault();
    const bodies: AddLineRequest[] = [];
    for (const line of lines) {
      const edit = edits[line.id];
      if (!edit) continue;
      let quantity = Number(line.quantity);
      if (edit.quantity.trim() !== "") {
        const q = Number(edit.quantity);
        if (!Number.isFinite(q) || q <= 0) {
          toast.error(t("nhcx_enter_quantity", { code: line.code }));
          return;
        }
        if (!Number.isInteger(q)) {
          toast.error(t("nhcx_quantity_whole", { code: line.code }));
          return;
        }
        quantity = q;
      }
      let unitPrice: string | undefined;
      if (openPrice(line)) {
        const p = Number(edit.price);
        if (edit.price.trim() === "" || !Number.isFinite(p)) {
          toast.error(t("nhcx_enter_price", { code: line.code }));
          return;
        }
        if (p < 0) {
          toast.error(t("nhcx_price_negative", { code: line.code }));
          return;
        }
        unitPrice = p.toFixed(2);
      }
      const priceChanged =
        unitPrice !== undefined &&
        Number(unitPrice) !== (toNumber(line.unit_price) ?? 0);
      if (quantity !== Number(line.quantity) || priceChanged) {
        bodies.push({
          line_id: line.id,
          kind: line.kind,
          code: line.code,
          parent_code: line.parent_code || undefined,
          quantity,
          unit_price: unitPrice,
        });
      }
    }
    if (!bodies.length) {
      toast.success(t("nhcx_lines_updated"));
      return;
    }
    update.mutate(bodies);
  };

  const addLine = (body: Omit<AddLineRequest, "quantity">) =>
    add.mutate({ ...body, quantity: 1 });

  // Card 2: what the plan entries of the quoted procedures allow.
  const procedures = lines.filter((l) => l.kind === "Procedure");
  const quotedTiers = new Set(
    lines
      .filter((l) => l.kind === "Stratification")
      .map((l) => `${l.parent_code}:${l.code}`),
  );
  const suggestedImplants = new Map<
    string,
    { code: string; label: string; rate: unknown }
  >();
  const suggestedTiers: {
    code: string;
    label: string;
    rate: unknown;
    parent: ClaimLine;
  }[] = [];
  procedures.forEach((p) => {
    const b = benefitByCode.get(`Procedure:${p.code}`);
    (b?.extras ?? []).forEach((e) => {
      if (e.type === "Implant") {
        if (!quoted.has(e.code) && !suggestedImplants.has(e.code)) {
          suggestedImplants.set(e.code, {
            code: e.code,
            label: e.label || e.code,
            rate: e.rate,
          });
        }
      } else if (e.type === "Stratification") {
        const key = `${p.code}:${e.code}`;
        if (
          !quotedTiers.has(key) &&
          !suggestedTiers.some((s) => s.code === e.code)
        ) {
          suggestedTiers.push({
            code: e.code,
            label: e.label || e.code,
            rate: e.rate,
            parent: p,
          });
        }
      }
    });
  });

  // Card 3: the package master.
  const [search, setSearch] = useState("");
  const [speciality, setSpeciality] = useState("");
  const [kind, setKind] = useState("");
  const [applied, setApplied] = useState({ q: "", speciality: "", kind: "" });
  const [page, setPage] = useState(1);
  const specialities = useMemo(() => {
    const map = new Map<string, { name: string; n: number }>();
    benefits.forEach((b) => {
      const key = b.category_code || b.category_display || "";
      if (!key) return;
      const cur = map.get(key) ?? {
        name: b.category_display || b.category_code || key,
        n: 0,
      };
      cur.n += 1;
      map.set(key, cur);
    });
    return [...map.entries()].sort((a, b) =>
      a[1].name.localeCompare(b[1].name),
    );
  }, [benefits]);
  const filtered = benefits.filter((b) => {
    const q = applied.q.toLowerCase();
    return (
      (!q ||
        b.code.toLowerCase().includes(q) ||
        (b.display || "").toLowerCase().includes(q)) &&
      (!applied.speciality ||
        (b.category_code || b.category_display) === applied.speciality) &&
      (!applied.kind || b.kind === applied.kind)
    );
  });
  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));

  return (
    <div className="flex flex-col gap-4">
      <div className="flex justify-end">
        <Button variant="outline" size="sm" onClick={onBack}>
          <Undo2 className="size-4" />
          {t("nhcx_back_to_claim")}
        </Button>
      </div>

      <Card>
        <form onSubmit={saveLines}>
          <CardHeader>
            <CardTitle>{t("nhcx_on_this_preauth")}</CardTitle>
          </CardHeader>
          <CardContent>
            {!rows.length ? (
              <Muted>{t("nhcx_nothing_quoted_add")}</Muted>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("nhcx_kind")}</TableHead>
                      <TableHead>{t("nhcx_item")}</TableHead>
                      <TableHead>{t("nhcx_speciality")}</TableHead>
                      <TableHead>{t("nhcx_kind_tier")}</TableHead>
                      <TableHead>{t("nhcx_rate")}</TableHead>
                      <TableHead>{t("nhcx_quantity")}</TableHead>
                      <TableHead className="text-right">
                        {t("nhcx_amount")}
                      </TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {rows.map(({ line, tiers, amount }) => (
                      <TableRow key={line.id}>
                        <TableCell>
                          <Chip tone={LINE_KIND[line.kind]?.tone ?? "neutral"}>
                            {t(LINE_KIND[line.kind]?.label ?? line.kind)}
                          </Chip>
                        </TableCell>
                        <TableCell>
                          <div>{line.display || line.code}</div>
                          <div className="text-xs text-gray-500">
                            {line.code}
                          </div>
                        </TableCell>
                        <TableCell>
                          {line.category_display || line.category_code || "-"}
                        </TableCell>
                        <TableCell>
                          <TierChips
                            tiers={tiers}
                            onRemove={(tier) => remove.mutate(tier.id)}
                          />
                        </TableCell>
                        <TableCell>
                          {openPrice(line) ? (
                            <Input
                              type="number"
                              min={0}
                              step={0.01}
                              className="w-32"
                              value={edits[line.id]?.price ?? ""}
                              onChange={(e) =>
                                setEdits((cur) => ({
                                  ...cur,
                                  [line.id]: {
                                    ...cur[line.id],
                                    price: e.target.value,
                                  },
                                }))
                              }
                            />
                          ) : (
                            formatMoney(line.unit_price)
                          )}
                        </TableCell>
                        <TableCell>
                          <Input
                            type="number"
                            min={1}
                            step={1}
                            className="w-24"
                            value={edits[line.id]?.quantity ?? ""}
                            onChange={(e) =>
                              setEdits((cur) => ({
                                ...cur,
                                [line.id]: {
                                  ...cur[line.id],
                                  quantity: e.target.value,
                                },
                              }))
                            }
                          />
                        </TableCell>
                        <TableCell className="text-right">
                          {formatMoney(amount)}
                        </TableCell>
                        <TableCell>
                          <ConfirmButton
                            size="xs"
                            variant="destructive"
                            confirm={t("nhcx_remove_line_confirm")}
                            onConfirm={() => remove.mutate(line.id)}
                          >
                            {t("remove")}
                          </ConfirmButton>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
                <p className="mt-3 text-right font-semibold">
                  {t("nhcx_total", { amount: formatMoney(linesTotal(lines)) })}
                </p>
              </div>
            )}
          </CardContent>
          {rows.length > 0 && (
            <CardFooter className="justify-end">
              <Button
                type="submit"
                variant="primary"
                disabled={update.isPending}
              >
                <Save className="size-4" />
                {t("nhcx_update_lines")}
              </Button>
            </CardFooter>
          )}
        </form>
      </Card>

      {(suggestedImplants.size > 0 || suggestedTiers.length > 0) && (
        <Card>
          <CardHeader>
            <CardTitle>{t("nhcx_suggested_by_plan")}</CardTitle>
          </CardHeader>
          <CardContent>
            <Accordion type="multiple" defaultValue={["implants", "tiers"]}>
              {suggestedImplants.size > 0 && (
                <AccordionItem value="implants">
                  <AccordionTrigger>
                    {t("nhcx_implants_for_procedures")}
                  </AccordionTrigger>
                  <AccordionContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t("nhcx_code")}</TableHead>
                          <TableHead>{t("nhcx_implant")}</TableHead>
                          <TableHead>{t("nhcx_rate")}</TableHead>
                          <TableHead />
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {[...suggestedImplants.values()].map((s) => (
                          <TableRow key={s.code}>
                            <TableCell>{s.code}</TableCell>
                            <TableCell>{s.label}</TableCell>
                            <TableCell>
                              {formatMoney(s.rate as string)}
                            </TableCell>
                            <TableCell>
                              <Button
                                size="xs"
                                variant="primary"
                                disabled={add.isPending}
                                onClick={() =>
                                  addLine({ kind: "Implant", code: s.code })
                                }
                              >
                                <Plus className="size-3" />
                                {t("add")}
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </AccordionContent>
                </AccordionItem>
              )}
              {suggestedTiers.length > 0 && (
                <AccordionItem value="tiers">
                  <AccordionTrigger>
                    {t("nhcx_ward_icu_tiers_title")}
                  </AccordionTrigger>
                  <AccordionContent>
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t("nhcx_code")}</TableHead>
                          <TableHead>{t("nhcx_tier")}</TableHead>
                          <TableHead>{t("nhcx_for")}</TableHead>
                          <TableHead>{t("nhcx_rate")}</TableHead>
                          <TableHead />
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {suggestedTiers.map((s) => (
                          <TableRow key={`${s.parent.code}:${s.code}`}>
                            <TableCell>{s.code}</TableCell>
                            <TableCell>{s.label}</TableCell>
                            <TableCell>
                              <div>{s.parent.display || s.parent.code}</div>
                              <div className="text-xs text-gray-500">
                                {s.parent.code}
                              </div>
                            </TableCell>
                            <TableCell>
                              {formatMoney(s.rate as string)}
                            </TableCell>
                            <TableCell>
                              <Button
                                size="xs"
                                variant="primary"
                                disabled={add.isPending}
                                onClick={() =>
                                  addLine({
                                    kind: "Stratification",
                                    code: s.code,
                                    parent_code: s.parent.code,
                                  })
                                }
                              >
                                <Plus className="size-3" />
                                {t("add")}
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          </CardContent>
        </Card>
      )}

      <form
        className="flex flex-wrap items-end gap-3"
        onSubmit={(e) => {
          e.preventDefault();
          setApplied({ q: search, speciality, kind });
          setPage(1);
        }}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor="nhcx-lines-search">{t("search")}</Label>
          <Input
            id="nhcx-lines-search"
            className="min-w-72"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label>{t("nhcx_speciality")}</Label>
          <Select
            value={speciality || ALL}
            onValueChange={(v) => setSpeciality(v === ALL ? "" : v)}
          >
            <SelectTrigger className="w-60">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t("nhcx_all_specialities")}</SelectItem>
              {specialities.map(([key, s]) => (
                <SelectItem key={key} value={key}>
                  {s.name} ({s.n})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label>{t("nhcx_type")}</Label>
          <Select
            value={kind || ALL}
            onValueChange={(v) => setKind(v === ALL ? "" : v)}
          >
            <SelectTrigger className="w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL}>{t("nhcx_any_type")}</SelectItem>
              <SelectItem value="Procedure">
                {t("nhcx_kind_procedure")}
              </SelectItem>
              <SelectItem value="Implant">{t("nhcx_kind_implant")}</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <Button type="submit" variant="primary">
          <SearchIcon className="size-4" />
          {t("search")}
        </Button>
      </form>

      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_n_in_master", { n: filtered.length })}</CardTitle>
        </CardHeader>
        <CardContent>
          {!filtered.length ? (
            <Muted>{t("nhcx_nothing_matches")}</Muted>
          ) : (
            <div className="overflow-x-auto">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("nhcx_code")}</TableHead>
                    <TableHead>{t("nhcx_package")}</TableHead>
                    <TableHead>{t("nhcx_speciality")}</TableHead>
                    <TableHead>{t("nhcx_type")}</TableHead>
                    <TableHead className="text-right">
                      {t("nhcx_rate")}
                    </TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {filtered.slice((page - 1) * PAGE, page * PAGE).map((b) => (
                    <TableRow key={b.id}>
                      <TableCell>{b.code}</TableCell>
                      <TableCell>{b.display || b.code}</TableCell>
                      <TableCell>
                        {b.category_display || b.category_code || "-"}
                      </TableCell>
                      <TableCell>
                        <Chip
                          tone={b.kind === "Procedure" ? "info" : "warning"}
                        >
                          {b.kind}
                        </Chip>
                      </TableCell>
                      <TableCell className="text-right">
                        {formatMoney(b.rate)}
                      </TableCell>
                      <TableCell className="text-right">
                        {(b.kind === "Procedure" || b.kind === "Implant") && (
                          <Button
                            size="xs"
                            variant="primary"
                            disabled={add.isPending}
                            onClick={() =>
                              addLine({
                                kind: b.kind as LineKind,
                                code: b.code,
                              })
                            }
                          >
                            <Plus className="size-3" />
                            {t("add")}
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
              {pages > 1 && (
                <div className="mt-3 flex items-center gap-3 text-sm">
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page <= 1}
                    onClick={() => setPage(page - 1)}
                  >
                    {t("previous")}
                  </Button>
                  <span>{t("nhcx_page_of", { page, pages })}</span>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={page >= pages}
                    onClick={() => setPage(page + 1)}
                  >
                    {t("next")}
                  </Button>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
