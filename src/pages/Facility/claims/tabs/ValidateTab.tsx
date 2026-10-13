import { ArrowRight, ShieldCheck } from "lucide-react";
import { useTranslation } from "react-i18next";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";

import { AuthRequirement, ClaimState } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  CorrelationId,
  DetailList,
  ErrorText,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
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

const RULING_STATUS: Record<string, { label: string; tone: Tone }> = {
  checking: { label: "nhcx_awaiting_payer", tone: "info" },
  ready: { label: "nhcx_validated", tone: "success" },
  error: { label: "nhcx_status_error", tone: "danger" },
};

// The ruling is stale when the quoted codes differ from the ones asked about
// (ward tiers and quantities ignored).
export function rulingStale(state: ClaimState): boolean {
  const ruling = state.ruling;
  if (!ruling || ruling.status !== "ready") return false;
  const asked = Array.isArray(ruling.asked_codes)
    ? ruling.asked_codes
    : (ruling.asked_codes || "").split(/[,\s|]+/);
  const a = [...new Set(asked.filter(Boolean))].sort().join(",");
  const now = [
    ...new Set(
      state.lines.filter((l) => l.kind !== "Stratification").map((l) => l.code),
    ),
  ]
    .sort()
    .join(",");
  return a !== now;
}

function RequirementTable({ rows }: { rows: AuthRequirement[] }) {
  const { t } = useTranslation();
  if (!rows.length) return <Muted>{t("nhcx_nothing_listed")}</Muted>;
  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>{t("nhcx_kind")}</TableHead>
          <TableHead>{t("nhcx_code")}</TableHead>
          <TableHead>{t("nhcx_what")}</TableHead>
          <TableHead>{t("nhcx_for")}</TableHead>
          <TableHead>{t("nhcx_stage")}</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((r) => (
          <TableRow key={`${r.seq}-${r.code}`}>
            <TableCell>
              <Chip tone={r.kind === "form" ? "info" : "warning"}>
                {r.kind === "form" ? t("nhcx_form") : t("nhcx_document")}
              </Chip>
            </TableCell>
            <TableCell>{r.code || "-"}</TableCell>
            <TableCell>{r.display || r.form_url || "-"}</TableCell>
            <TableCell>{r.for_code || "-"}</TableCell>
            <TableCell>{r.stage || "-"}</TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

// S8.2 Authorisation requirements card.
export function AuthRequirementsCard({
  facilityId,
  claimId,
  state,
}: Omit<ClaimTabProps, "goTo">) {
  const { t } = useTranslation();
  const ruling = state.ruling;
  const ask = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.authRequirements, {
        pathParams: { facilityId, claimId },
        body: {},
      }),
    t("nhcx_procedure_set_sent"),
  );
  const quoted = state.lines.filter((l) => l.kind !== "Stratification").length;
  const items = ruling?.items ?? [];
  const reqs = ruling?.requirements ?? [];
  const atPreauth = reqs.filter((r) => r.at_preauth !== false);
  const later = reqs.filter((r) => r.at_preauth === false);
  const stale = rulingStale(state);
  const status = ruling ? RULING_STATUS[ruling.status] : null;

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2">
        <div className="flex items-center gap-2">
          <CardTitle>{t("nhcx_auth_requirements")}</CardTitle>
          {status && <Chip tone={status.tone}>{t(status.label)}</Chip>}
        </div>
        <Button
          variant={ruling ? "outline" : "primary"}
          size="sm"
          disabled={ask.isPending}
          onClick={() => ask.mutate(undefined)}
        >
          <ShieldCheck className="size-4" />
          {ruling ? t("nhcx_check_again") : t("nhcx_validate_procedure_set")}
        </Button>
      </CardHeader>
      <CardContent className="space-y-4">
        {!ruling && (
          <p className="text-sm">{t("nhcx_auth_never_asked", { n: quoted })}</p>
        )}
        {ruling?.status === "checking" && (
          <>
            <p className="text-sm">{t("nhcx_auth_checking")}</p>
            <DetailList
              items={[
                {
                  label: t("nhcx_sent_at"),
                  value: formatDateTime(ruling.requested_at),
                },
                { label: t("nhcx_transaction"), value: ruling.txn_id },
                {
                  label: t("nhcx_correlation_id"),
                  value: <CorrelationId value={ruling.correlation_id} />,
                },
              ]}
            />
          </>
        )}
        {ruling?.status === "error" && (
          <ErrorText>
            {ruling.error_message || t("nhcx_exchange_failed")}
          </ErrorText>
        )}
        {ruling?.status === "ready" && (
          <>
            {stale && (
              <div className="space-y-1">
                <Badge variant="yellow">{t("nhcx_lines_changed")}</Badge>
                <Muted>{t("nhcx_lines_changed_text")}</Muted>
              </div>
            )}
            <DetailList
              items={[
                { label: t("nhcx_disposition"), value: ruling.disposition },
                { label: t("nhcx_outcome"), value: ruling.outcome },
                {
                  label: t("nhcx_checked_at"),
                  value: formatDateTime(ruling.settled_at),
                },
              ]}
            />
            <Accordion type="multiple" defaultValue={["items", "preauth"]}>
              <AccordionItem value="items">
                <AccordionTrigger>
                  {t("nhcx_ruling_on_lines", { n: items.length })}
                </AccordionTrigger>
                <AccordionContent>
                  {!items.length ? (
                    <Muted>{t("nhcx_ruled_no_lines")}</Muted>
                  ) : (
                    <Table>
                      <TableHeader>
                        <TableRow>
                          <TableHead>{t("nhcx_line")}</TableHead>
                          <TableHead>{t("nhcx_authorisation")}</TableHead>
                          <TableHead>{t("nhcx_excluded")}</TableHead>
                          <TableHead>{t("nhcx_benefit")}</TableHead>
                          <TableHead className="text-right">
                            {t("nhcx_allowed")}
                          </TableHead>
                        </TableRow>
                      </TableHeader>
                      <TableBody>
                        {items.map((i) => (
                          <TableRow key={`${i.seq}-${i.code}`}>
                            <TableCell>
                              <div>{i.display || i.code}</div>
                              <div className="text-xs text-gray-500">
                                {i.code}
                              </div>
                            </TableCell>
                            <TableCell>
                              {i.auth_required === true
                                ? t("nhcx_required")
                                : i.auth_required === false
                                  ? t("nhcx_not_required")
                                  : " - "}
                            </TableCell>
                            <TableCell>
                              {i.excluded ? (
                                <Chip tone="danger">{t("nhcx_excluded")}</Chip>
                              ) : (
                                t("no")
                              )}
                            </TableCell>
                            <TableCell>{i.benefit_type || "-"}</TableCell>
                            <TableCell className="text-right">
                              {formatMoney(i.allowed_amount)}
                            </TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  )}
                </AccordionContent>
              </AccordionItem>
              <AccordionItem value="preauth">
                <AccordionTrigger>
                  {t("nhcx_needed_for_preauth", { n: atPreauth.length })}
                </AccordionTrigger>
                <AccordionContent>
                  <RequirementTable rows={atPreauth} />
                </AccordionContent>
              </AccordionItem>
              {later.length > 0 && (
                <AccordionItem value="later">
                  <AccordionTrigger>
                    {t("nhcx_needed_later", { n: later.length })}
                  </AccordionTrigger>
                  <AccordionContent className="space-y-2">
                    <Muted>{t("nhcx_needed_later_note")}</Muted>
                    <RequirementTable rows={later} />
                  </AccordionContent>
                </AccordionItem>
              )}
            </Accordion>
          </>
        )}
        <Muted>
          {t("nhcx_payer_adapter", { adapter: state.adapter || "-" })}
        </Muted>
      </CardContent>
    </Card>
  );
}

// S4 Validate step: S8.2 plus the hand-over to the pre-authorisation.
export default function ValidateTab(props: ClaimTabProps) {
  const { t } = useTranslation();
  if (!props.state.lines.length) {
    return (
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_tab_validate")}</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm">{t("nhcx_validate_no_lines")}</p>
        </CardContent>
      </Card>
    );
  }
  return (
    <div className="flex flex-col gap-4">
      <AuthRequirementsCard {...props} />
      <Card>
        <CardContent className="flex flex-wrap items-center justify-between gap-3 pt-6">
          <p className="text-sm">{t("nhcx_validate_handover")}</p>
          <Button variant="primary" onClick={() => props.goTo("preauth")}>
            {t("nhcx_go_to_preauth")}
            <ArrowRight className="size-4" />
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
