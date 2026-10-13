import {
  ClipboardList,
  Download,
  RefreshCw,
  SearchIcon,
  X,
} from "lucide-react";
import { useQueryParams } from "raviger";
import { useEffect, useMemo, useState } from "react";
import { Trans, useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
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

import { Benefit, ClaimForm } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  ConfirmButton,
  CorrelationId,
  DetailList,
  ErrorText,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import FormDetail from "@/pages/Facility/claims/components/FormDetail";
import PackageDetail from "@/pages/Facility/claims/components/PackageDetail";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  Tone,
  formatDateTime,
  formatMoney,
} from "@/pages/Facility/claims/utils";

const PAGE = 100;
const ALL = "__all";

const PLAN_STATUS: Record<string, { label: string; tone: Tone }> = {
  fetching: { label: "nhcx_awaiting_payer", tone: "info" },
  ready: { label: "nhcx_plan_ready", tone: "success" },
  empty: { label: "nhcx_plan_empty", tone: "warning" },
  error: { label: "nhcx_status_error", tone: "danger" },
};

function Pager({
  page,
  pages,
  onChange,
}: {
  page: number;
  pages: number;
  onChange: (p: number) => void;
}) {
  const { t } = useTranslation();
  if (pages <= 1) return null;
  return (
    <div className="mt-3 flex items-center gap-3 text-sm">
      <Button
        size="sm"
        variant="outline"
        disabled={page <= 1}
        onClick={() => onChange(page - 1)}
      >
        {t("previous")}
      </Button>
      <span>{t("nhcx_page_of", { page, pages })}</span>
      <Button
        size="sm"
        variant="outline"
        disabled={page >= pages}
        onClick={() => onChange(page + 1)}
      >
        {t("next")}
      </Button>
    </div>
  );
}

export function allPlanForms(state: ClaimTabProps["state"]): ClaimForm[] {
  if (state.plan_forms?.length) return state.plan_forms;
  const seen = new Map<string, ClaimForm>();
  [...state.forms.preauth, ...state.forms.claim].forEach((f) =>
    seen.set(f.url, f),
  );
  return [...seen.values()];
}

// S7 Insurance Plan tab, with S7.1 (package modal), S7.2 and S7.3 (forms modal).
export default function InsurancePlanTab({
  facilityId,
  claimId,
  state,
}: ClaimTabProps) {
  const { t } = useTranslation();
  const { plan, benefits } = state;
  const forms = useMemo(() => allPlanForms(state), [state]);

  const [qParams, setQParams] = useQueryParams<{
    plan_q?: string;
    plan_speciality?: string;
    plan_type?: string;
  }>();
  const [search, setSearch] = useState(qParams.plan_q || "");
  const [speciality, setSpeciality] = useState(qParams.plan_speciality || "");
  const [kind, setKind] = useState(qParams.plan_type || "");
  const [page, setPage] = useState(1);
  const [open, setOpen] = useState<Benefit | null>(null);
  const [formsOpen, setFormsOpen] = useState(false);
  const [formSearch, setFormSearch] = useState("");
  const [formPage, setFormPage] = useState(1);
  const [openForm, setOpenForm] = useState<ClaimForm | null>(null);

  useEffect(
    () => setPage(1),
    [qParams.plan_q, qParams.plan_speciality, qParams.plan_type],
  );

  const fetchPlan = useClaimAction(
    claimId,
    (refresh: boolean) =>
      nhcxCall(nhcxApi.fetchPlan, {
        pathParams: { facilityId, claimId },
        body: { refresh },
      }),
    t("nhcx_plan_requested"),
  );

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

  const filtered = useMemo(() => {
    const q = (qParams.plan_q || "").toLowerCase();
    return benefits.filter(
      (b) =>
        (!q ||
          b.code.toLowerCase().includes(q) ||
          (b.display || "").toLowerCase().includes(q)) &&
        (!qParams.plan_speciality ||
          (b.category_code || b.category_display) ===
            qParams.plan_speciality) &&
        (!qParams.plan_type || b.kind === qParams.plan_type),
    );
  }, [benefits, qParams.plan_q, qParams.plan_speciality, qParams.plan_type]);

  const pages = Math.max(1, Math.ceil(filtered.length / PAGE));
  const shown = filtered.slice((page - 1) * PAGE, page * PAGE);
  const filterSet = !!(
    qParams.plan_q ||
    qParams.plan_speciality ||
    qParams.plan_type
  );

  const applyFilters = (e?: React.SyntheticEvent) => {
    e?.preventDefault();
    setQParams({
      ...qParams,
      plan_q: search || undefined,
      plan_speciality: speciality || undefined,
      plan_type: kind || undefined,
    });
  };

  const filteredForms = forms
    .filter((f) => {
      const q = formSearch.toLowerCase();
      return (
        !q ||
        f.title.toLowerCase().includes(q) ||
        f.url.toLowerCase().includes(q)
      );
    })
    .sort((a, b) => a.title.localeCompare(b.title));
  const formPages = Math.max(1, Math.ceil(filteredForms.length / PAGE));

  const intro = (
    <p className="text-sm text-gray-700">
      <Trans i18nKey="nhcx_plan_intro" components={{ b: <strong /> }} />
    </p>
  );

  if (!plan) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_insurance_plan")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {intro}
          <Button
            variant="primary"
            disabled={fetchPlan.isPending}
            onClick={() => fetchPlan.mutate(false)}
          >
            <Download className="size-4" />
            {t("nhcx_fetch_plan")}
          </Button>
        </CardContent>
      </Card>
    );
  }

  const status = PLAN_STATUS[plan.status];

  if (plan.status === "fetching" || plan.status === "error") {
    return (
      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            {t("nhcx_insurance_plan")}
            {status && <Chip tone={status.tone}>{t(status.label)}</Chip>}
          </CardTitle>
          <ConfirmButton
            variant={plan.status === "error" ? "primary" : "secondary"}
            confirm={
              plan.status === "fetching"
                ? t("nhcx_fetch_again_waiting_confirm")
                : undefined
            }
            disabled={fetchPlan.isPending}
            onConfirm={() => fetchPlan.mutate(true)}
          >
            <RefreshCw className="size-4" />
            {t("nhcx_fetch_again")}
          </ConfirmButton>
        </CardHeader>
        <CardContent className="space-y-3">
          {intro}
          {plan.status === "fetching" ? (
            <>
              <p className="text-sm">{t("nhcx_plan_waiting")}</p>
              {state.poll_notes.map((n) => (
                <Muted key={n}>{t("nhcx_could_not_poll", { error: n })}</Muted>
              ))}
              <DetailList
                items={[
                  {
                    label: t("nhcx_sent_at"),
                    value: formatDateTime(plan.requested_at),
                  },
                  {
                    label: t("nhcx_transaction"),
                    value: <CorrelationId value={plan.txn_id} />,
                  },
                  {
                    label: t("nhcx_correlation_id"),
                    value: <CorrelationId value={plan.correlation_id} />,
                  },
                ]}
              />
            </>
          ) : (
            <ErrorText>
              {plan.error_message || t("nhcx_exchange_failed")}
            </ErrorText>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      <Card>
        <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-2">
          <CardTitle className="flex items-center gap-2">
            {t("nhcx_insurance_plan")}
            {status && <Chip tone={status.tone}>{t(status.label)}</Chip>}
          </CardTitle>
          <div className="flex gap-2">
            {forms.length > 0 && (
              <Button
                variant="outline"
                size="sm"
                onClick={() => setFormsOpen(true)}
              >
                <ClipboardList className="size-4" />
                {t("nhcx_all_forms")}
              </Button>
            )}
            <ConfirmButton
              confirm={t("nhcx_fetch_again_confirm")}
              disabled={fetchPlan.isPending}
              onConfirm={() => fetchPlan.mutate(true)}
            >
              <RefreshCw className="size-4" />
              {t("nhcx_fetch_again")}
            </ConfirmButton>
          </div>
        </CardHeader>
        <CardContent>
          <DetailList
            items={[
              { label: t("nhcx_plan"), value: plan.plan_title },
              { label: t("nhcx_plan_identifier"), value: plan.plan_identifier },
              { label: t("nhcx_plan_type"), value: plan.plan_type },
              {
                label: t("nhcx_overall_sum_insured"),
                value: formatMoney(plan.sum_insured),
              },
              {
                label: t("nhcx_asked_with"),
                value: [plan.policy_code, plan.provider_id]
                  .filter(Boolean)
                  .join(", "),
              },
              {
                label: t("nhcx_fetched_at"),
                value: formatDateTime(plan.fetched_at),
              },
              {
                label: t("nhcx_correlation_id"),
                value: <CorrelationId value={plan.correlation_id} />,
              },
            ]}
          />
        </CardContent>
      </Card>

      {plan.status === "empty" && (
        <Card>
          <CardContent className="pt-6 space-y-2">
            {plan.error_message && <Muted>{plan.error_message}</Muted>}
            <p className="text-sm">{t("nhcx_plan_empty_text")}</p>
          </CardContent>
        </Card>
      )}

      {plan.status === "ready" && (
        <>
          <form
            onSubmit={applyFilters}
            className="flex flex-wrap items-end gap-3"
          >
            <div className="flex flex-col gap-1">
              <Label htmlFor="nhcx-plan-search">{t("search")}</Label>
              <Input
                id="nhcx-plan-search"
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
                  <SelectItem value={ALL}>
                    {t("nhcx_all_specialities")}
                  </SelectItem>
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
                  <SelectItem value="Implant">
                    {t("nhcx_kind_implant")}
                  </SelectItem>
                </SelectContent>
              </Select>
            </div>
            <Button type="submit" variant="primary">
              <SearchIcon className="size-4" />
              {t("search")}
            </Button>
            {filterSet && (
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  setSearch("");
                  setSpeciality("");
                  setKind("");
                  setQParams({
                    ...qParams,
                    plan_q: undefined,
                    plan_speciality: undefined,
                    plan_type: undefined,
                  });
                }}
              >
                <X className="size-4" />
                {t("clear")}
              </Button>
            )}
          </form>

          <Card>
            <CardHeader>
              <CardTitle>
                {t("nhcx_n_packages", { n: filtered.length })}
              </CardTitle>
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
                        <TableHead />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {shown.map((b) => (
                        <TableRow key={b.id}>
                          <TableCell>{b.code}</TableCell>
                          <TableCell>{b.display || b.code}</TableCell>
                          <TableCell>
                            {b.category_display || b.category_code || "-"}
                          </TableCell>
                          <TableCell>
                            {b.kind ? (
                              <Chip
                                tone={
                                  b.kind === "Procedure" ? "info" : "warning"
                                }
                              >
                                {b.kind}
                              </Chip>
                            ) : (
                              "-"
                            )}
                          </TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() => setOpen(b)}
                            >
                              {t("view")}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                  <Pager page={page} pages={pages} onChange={setPage} />
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}

      <Dialog open={!!open} onOpenChange={(o) => !o && setOpen(null)}>
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>{open?.display || open?.code}</DialogTitle>
          </DialogHeader>
          {open && (
            <PackageDetail
              benefit={open}
              benefits={benefits}
              forms={forms}
              planTitle={plan.plan_title}
              onOpen={setOpen}
            />
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{t("close")}</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog
        open={formsOpen}
        onOpenChange={(o) => {
          setFormsOpen(o);
          if (!o) setOpenForm(null);
        }}
      >
        <DialogContent className="max-h-[90vh] overflow-y-auto sm:max-w-3xl">
          <DialogHeader>
            <DialogTitle>
              {openForm
                ? openForm.title
                : t("nhcx_n_forms", { n: filteredForms.length })}
            </DialogTitle>
          </DialogHeader>
          {openForm ? (
            <>
              <Button
                variant="link"
                size="sm"
                className="self-start px-0"
                onClick={() => setOpenForm(null)}
              >
                {t("back")}
              </Button>
              <FormDetail form={openForm} />
            </>
          ) : (
            <>
              <div className="flex items-end gap-2">
                <Input
                  className="min-w-64"
                  placeholder={t("search")}
                  value={formSearch}
                  onChange={(e) => {
                    setFormSearch(e.target.value);
                    setFormPage(1);
                  }}
                />
              </div>
              {!filteredForms.length ? (
                <Muted>{t("nhcx_nothing_matches")}</Muted>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("nhcx_form")}</TableHead>
                      <TableHead>{t("nhcx_kind")}</TableHead>
                      <TableHead>{t("nhcx_questions")}</TableHead>
                      <TableHead />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {filteredForms
                      .slice((formPage - 1) * PAGE, formPage * PAGE)
                      .map((f) => (
                        <TableRow key={f.url}>
                          <TableCell>
                            <div>{f.title}</div>
                            <div className="text-xs text-gray-500 break-all">
                              {f.url}
                            </div>
                          </TableCell>
                          <TableCell>
                            {f.url.includes("/stgquestionnaire/") ? (
                              <Chip tone="warning">STG</Chip>
                            ) : (
                              <Chip tone="info">{t("nhcx_policy_chip")}</Chip>
                            )}
                          </TableCell>
                          <TableCell>{f.questions.length}</TableCell>
                          <TableCell>
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() => setOpenForm(f)}
                            >
                              {t("view")}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                  </TableBody>
                </Table>
              )}
              <Pager page={formPage} pages={formPages} onChange={setFormPage} />
            </>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button variant="outline">{t("close")}</Button>
            </DialogClose>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
