import { Check, Inbox } from "lucide-react";
import { Trans, useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

import { Payment } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import {
  Chip,
  CorrelationId,
  DetailList,
  ErrorText,
  StatGrid,
  StatTile,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import { ClaimTabProps } from "@/pages/Facility/claims/tabs/types";
import {
  nhcxCall,
  useClaimAction,
} from "@/pages/Facility/claims/useClaimAction";
import {
  Tone,
  formatDate,
  formatDateTime,
  formatMoney,
  toNumber,
} from "@/pages/Facility/claims/utils";

const ACK_STATUS: Record<Payment["ack_status"], { label: string; tone: Tone }> =
  {
    pending: { label: "nhcx_not_acknowledged", tone: "warning" },
    sent: { label: "nhcx_acknowledged", tone: "success" },
    error: { label: "nhcx_ack_failed_chip", tone: "danger" },
  };

const PAYMENT_TONE: Record<string, Tone> = {
  paid: "success",
  cleared: "success",
  issued: "info",
  pending: "warning",
  partial: "warning",
  failed: "danger",
  returned: "danger",
};

export const isInitiatedOnly = (p: Payment): boolean =>
  !p.utr && (p.disposition ?? "").toLowerCase().includes("initiat");

function PaymentCard({
  facilityId,
  claimId,
  payment: p,
}: {
  facilityId: string;
  claimId: string;
  payment: Payment;
}) {
  const { t } = useTranslation();
  const ack = useClaimAction(
    claimId,
    () =>
      nhcxCall(nhcxApi.ackPayment, {
        pathParams: { facilityId, claimId, paymentId: p.id },
        body: {},
      }),
    t("nhcx_payment_acknowledged"),
  );
  const ackChip = ACK_STATUS[p.ack_status] ?? ACK_STATUS.pending;
  const status = (p.payment_status ?? "").toLowerCase();
  return (
    <Card>
      <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
        <div className="space-y-2">
          <CardTitle>{p.disposition || t("nhcx_payment_notice")}</CardTitle>
          <div className="flex flex-wrap gap-2">
            {isInitiatedOnly(p) ? (
              <Chip tone="warning">{t("nhcx_initiated_utr_awaited")}</Chip>
            ) : (
              p.payment_status && (
                <Chip tone={PAYMENT_TONE[status] ?? "info"}>
                  {p.payment_status}
                </Chip>
              )
            )}
            <Chip tone={ackChip.tone}>{t(ackChip.label)}</Chip>
          </div>
        </div>
        {p.ack_status !== "sent" && (
          <Button
            size="sm"
            variant="primary"
            disabled={ack.isPending}
            onClick={() => ack.mutate(undefined)}
          >
            <Check className="size-4" />
            {p.ack_status === "error"
              ? t("nhcx_acknowledge_again")
              : t("nhcx_acknowledge")}
          </Button>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <DetailList
          columns={3}
          items={[
            { label: t("nhcx_amount"), value: formatMoney(p.amount) },
            { label: t("nhcx_currency"), value: p.currency },
            {
              label: t("nhcx_payment_date"),
              value: formatDate(p.payment_date),
            },
            { label: t("nhcx_utr"), value: p.utr },
            { label: t("nhcx_claim_number"), value: p.claim_ref },
            {
              label: t("nhcx_received"),
              value: formatDateTime(p.received_at),
            },
            {
              label: t("nhcx_acknowledged"),
              value: formatDateTime(p.acknowledged_at),
            },
            {
              label: t("nhcx_correlation_id"),
              value: <CorrelationId value={p.correlation_id} />,
            },
          ]}
        />
        {!!p.details?.length && (
          <div className="overflow-x-auto rounded-md border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("nhcx_reference")}</TableHead>
                  <TableHead>{t("nhcx_type")}</TableHead>
                  <TableHead>{t("nhcx_date")}</TableHead>
                  <TableHead className="text-right">
                    {t("nhcx_amount")}
                  </TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {p.details.map((d) => (
                  <TableRow key={d.seq}>
                    <TableCell>{d.reference || "-"}</TableCell>
                    <TableCell>
                      {d.type_display || d.type_code || "-"}
                    </TableCell>
                    <TableCell>{formatDate(d.date)}</TableCell>
                    <TableCell className="text-right">
                      {formatMoney(d.amount)}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}
        {p.ack_status === "error" && p.ack_error && (
          <ErrorText>{p.ack_error}</ErrorText>
        )}
      </CardContent>
    </Card>
  );
}

// S12 Payments tab.
export default function PaymentsTab({
  facilityId,
  claimId,
  state,
}: ClaimTabProps) {
  const { t } = useTranslation();
  const paid = toNumber(state.paid_total) ?? 0;
  const notices = [...state.payments].sort((a, b) =>
    (b.received_at ?? "").localeCompare(a.received_at ?? ""),
  );
  const claimed = state.submission?.requested_amount;
  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle>{t("nhcx_payments")}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm">
            <Trans
              i18nKey="nhcx_payments_intro"
              components={{ b: <strong />, code: <code /> }}
            />
          </p>
          <StatGrid>
            <StatTile
              label={t("nhcx_notices")}
              value={notices.length}
              tone="info"
            />
            <StatTile
              label={t("nhcx_paid_so_far")}
              value={formatMoney(state.paid_total)}
              tone={paid > 0 ? "success" : undefined}
            />
            <StatTile
              label={t("nhcx_claimed")}
              value={
                claimed !== null && claimed !== undefined
                  ? formatMoney(claimed)
                  : "-"
              }
            />
          </StatGrid>
        </CardContent>
      </Card>
      {notices.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-10 text-center text-sm text-gray-500">
            <Inbox className="size-8" />
            {t("nhcx_no_payment_notice")}
          </CardContent>
        </Card>
      ) : (
        notices.map((p) => (
          <PaymentCard
            key={p.id}
            facilityId={facilityId}
            claimId={claimId}
            payment={p}
          />
        ))
      )}
    </div>
  );
}
