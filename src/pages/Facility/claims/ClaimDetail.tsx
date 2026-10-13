import { useQuery } from "@tanstack/react-query";
import { RefreshCw } from "lucide-react";
import { Link, navigate } from "raviger";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";

import Page from "@/components/Common/Page";
import { CardListSkeleton } from "@/components/Common/SkeletonLoading";

import { ClaimState } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";
import query from "@/Utils/request/query";

import { Chip } from "./components/ClaimWidgets";
import ClaimTab from "./tabs/ClaimTab";
import CommunicationTab from "./tabs/CommunicationTab";
import EligibilityTab from "./tabs/EligibilityTab";
import InsurancePlanTab from "./tabs/InsurancePlanTab";
import LineItemsTab from "./tabs/LineItemsTab";
import PaymentsTab from "./tabs/PaymentsTab";
import PreauthTab from "./tabs/PreauthTab";
import { CLAIM_TABS, ClaimTabKey, ClaimTabProps } from "./tabs/types";
import ValidateTab from "./tabs/ValidateTab";
import VerificationTab from "./tabs/VerificationTab";
import { claimStateKey } from "./useClaimAction";
import {
  STAGE_LABEL,
  SUB_STAGE,
  formatMoney,
  isRefused,
  isWaiting,
  toNumber,
  unansweredCount,
} from "./utils";

interface NextAction {
  label: string;
  tab: ClaimTabKey;
}

// S6 next actions, read off the stage and sub-stage.
export function nextActions(
  state: ClaimState,
  t: (key: string, opts?: Record<string, unknown>) => string,
): NextAction[] {
  const out: NextAction[] = [];
  const { claim, stage, sub_stage: sub } = state;
  const open = state.queries.filter(
    (q) => q.kind === "query" && (q.status === "open" || q.status === "error"),
  ).length;
  if (open > 0) {
    out.push({
      label: t("nhcx_next_answer_payer", { n: open }),
      tab: "communication",
    });
  }
  const preauthResubmits = state.next_send.preauth === "preauth_query_response";
  const claimResubmits = state.next_send.claim === "claim_query_response";
  const discharged = !!(
    state.submission?.discharge_mode || claim.discharge_mode
  );

  if (stage === "eligibility") {
    if (["draft", "error", "not-eligible"].includes(claim.status)) {
      out.push({ label: t("nhcx_next_check_cover"), tab: "eligibility" });
    } else if (claim.status === "eligible") {
      if (state.plan?.status !== "ready") {
        out.push({ label: t("nhcx_next_fetch_plan"), tab: "plan" });
      } else if (!state.lines.length) {
        out.push({ label: t("nhcx_next_quote"), tab: "lines" });
      } else if (!claim.preauth_saved_at) {
        out.push({ label: t("nhcx_next_save_draft"), tab: "preauth" });
      } else {
        out.push({ label: t("nhcx_next_send_preauth"), tab: "preauth" });
      }
    }
  } else if (stage === "preauth" || stage === "enhancement") {
    if (sub === "queried") {
      if (preauthResubmits) {
        out.push({ label: t("nhcx_next_answer_query"), tab: "preauth" });
      } else if (!open) {
        out.push({
          label: t("nhcx_next_answer_payers_query"),
          tab: "communication",
        });
      }
    } else if (sub === "draft" || sub === "refused") {
      out.push({ label: t("nhcx_next_send_preauth"), tab: "preauth" });
    } else if (sub === "rejected") {
      out.push({ label: t("nhcx_next_fresh_preauth"), tab: "preauth" });
    } else if (sub === "approved" || sub === "partial") {
      const added = state.enhancement_lines.length;
      if (added) {
        out.push({
          label: t("nhcx_next_send_enhancement", { n: added }),
          tab: "preauth",
        });
      } else if (!discharged) {
        out.push({ label: t("nhcx_next_record_discharge"), tab: "claim" });
      } else {
        out.push({ label: t("nhcx_next_file_claim"), tab: "claim" });
      }
    } else if (["requested", "answered", "resubmitted"].includes(sub)) {
      out.push({ label: t("nhcx_next_with_payer"), tab: "preauth" });
    }
  } else if (stage === "claim") {
    if (sub === "queried") {
      if (claimResubmits) {
        out.push({ label: t("nhcx_next_answer_claim_query"), tab: "claim" });
      } else if (!open) {
        out.push({
          label: t("nhcx_next_answer_payers_query"),
          tab: "communication",
        });
      }
    } else if (sub === "rejected" || sub === "partial") {
      out.push({ label: t("nhcx_next_reprocess"), tab: "claim" });
    } else if (["requested", "answered", "resubmitted"].includes(sub)) {
      out.push({ label: t("nhcx_next_with_payer"), tab: "claim" });
    } else if (sub === "refused") {
      if (isRefused(state.next_send.claim)) {
        out.push({ label: t("nhcx_next_reprocess"), tab: "claim" });
      } else {
        out.push({ label: t("nhcx_next_send_claim_again"), tab: "claim" });
      }
    } else {
      out.push({ label: t("nhcx_next_await_payment"), tab: "payments" });
    }
  } else if (stage === "payment") {
    const pending = state.payments.some((p) => p.ack_status !== "sent");
    out.push({
      label: pending ? t("nhcx_next_ack_payment") : t("nhcx_next_settled"),
      tab: "payments",
    });
  }
  return out;
}

const TAB_ALIASES: Record<string, ClaimTabKey> = { procedure: "plan" };

function resolveTab(tab?: string): ClaimTabKey {
  if (!tab) return "eligibility";
  if (TAB_ALIASES[tab]) return TAB_ALIASES[tab];
  return CLAIM_TABS.some((c) => c.key === tab)
    ? (tab as ClaimTabKey)
    : "eligibility";
}

const TAB_COMPONENTS: Record<
  ClaimTabKey,
  (props: ClaimTabProps) => React.ReactNode
> = {
  eligibility: EligibilityTab,
  plan: InsurancePlanTab,
  lines: LineItemsTab,
  validate: ValidateTab,
  verification: VerificationTab,
  preauth: PreauthTab,
  communication: CommunicationTab,
  claim: ClaimTab,
  payments: PaymentsTab,
};

// S6 Claim Detail: the case shell. Every tab reads the A17 state loaded here.
export default function ClaimDetail({
  facilityId,
  claimId,
  tab,
}: {
  facilityId: string;
  claimId: string;
  tab?: string;
}) {
  const { t } = useTranslation();
  const active = resolveTab(tab);

  const {
    data: state,
    isLoading,
    isError,
    refetch,
    isFetching,
  } = useQuery<ClaimState>({
    queryKey: claimStateKey(claimId),
    queryFn: query(nhcxApi.claimState, {
      pathParams: { facilityId, claimId },
    }),
    refetchInterval: (q) => (isWaiting(q.state.data) ? 5000 : false),
  });

  const goTo = (key: ClaimTabKey) =>
    navigate(`/facility/${facilityId}/claims/${claimId}/${key}`, {
      replace: true,
    });

  if (isLoading) {
    return (
      <Page title={t("nhcx_claim")}>
        <div className="mt-4">
          <CardListSkeleton count={3} />
        </div>
      </Page>
    );
  }

  if (isError || !state) {
    return (
      <Page title={t("nhcx_claim")}>
        <Card className="mt-4">
          <CardContent className="pt-6 text-sm text-gray-600">
            {t("nhcx_claim_not_found")}{" "}
            <Link
              href={`/facility/${facilityId}/claims`}
              className="text-primary-700 underline"
            >
              {t("nhcx_claims")}
            </Link>
          </CardContent>
        </Card>
      </Page>
    );
  }

  const { claim } = state;
  const sub = SUB_STAGE[state.sub_stage];
  const queries = unansweredCount(state.queries);
  const paid = toNumber(state.paid_total) ?? 0;
  const waiting = isWaiting(state);
  const actions = nextActions(state, t);

  return (
    <Page title={t("nhcx_claim_title", { number: claim.claim_no })}>
      <div className="mt-4 flex flex-col gap-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h2 className="text-xl font-semibold">
            {claim.beneficiary_name || claim.member_id || "-"}
          </h2>
          <div className="flex flex-wrap items-center gap-2">
            <Chip tone="info">{claim.claim_no}</Chip>
            {sub && (
              <Chip tone={sub.tone}>
                {t(STAGE_LABEL[state.stage] ?? state.stage)}: {t(sub.label)}
              </Chip>
            )}
            {queries > 0 && (
              <Chip tone="warning">
                {queries === 1
                  ? t("nhcx_one_query_awaiting")
                  : t("nhcx_n_queries_awaiting", { n: queries })}
              </Chip>
            )}
            {paid > 0 && (
              <Chip tone="success">
                {t("nhcx_paid_total", { amount: formatMoney(paid) })}
              </Chip>
            )}
            {waiting && (
              <Button
                variant="outline"
                size="sm"
                disabled={isFetching}
                onClick={() => refetch()}
              >
                <RefreshCw
                  className={isFetching ? "size-4 animate-spin" : "size-4"}
                />
                {t("refresh")}
              </Button>
            )}
          </div>
        </div>

        {actions.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm text-gray-500">{t("nhcx_next")}</span>
            {actions.map((a, i) => (
              <Button
                key={a.label}
                size="sm"
                variant={i === 0 ? "primary" : "secondary"}
                onClick={() => goTo(a.tab)}
              >
                {a.label}
              </Button>
            ))}
          </div>
        )}

        <Tabs value={active} onValueChange={(v) => goTo(v as ClaimTabKey)}>
          <TabsList className="h-auto w-full flex-wrap justify-start">
            {CLAIM_TABS.map((c) => (
              <TabsTrigger key={c.key} value={c.key}>
                {t(c.label)}
              </TabsTrigger>
            ))}
          </TabsList>
          {CLAIM_TABS.map((c) => {
            const Component = TAB_COMPONENTS[c.key];
            return (
              <TabsContent
                key={c.key}
                value={c.key}
                forceMount
                className="data-[state=inactive]:hidden"
              >
                <Component
                  facilityId={facilityId}
                  claimId={claimId}
                  state={state}
                  goTo={goTo}
                />
              </TabsContent>
            );
          })}
        </Tabs>
      </div>
    </Page>
  );
}
