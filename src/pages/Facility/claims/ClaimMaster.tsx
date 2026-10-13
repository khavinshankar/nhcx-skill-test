import { useQuery } from "@tanstack/react-query";
import { PlusIcon } from "lucide-react";
import { Link } from "raviger";
import { useTranslation } from "react-i18next";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

import Page from "@/components/Common/Page";
import { TableSkeleton } from "@/components/Common/SkeletonLoading";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";
import PatientIdentifierFilter from "@/components/Patient/PatientIdentifierFilter";

import useFilters from "@/hooks/useFilters";

import { ClaimStatus } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";
import query from "@/Utils/request/query";

import { Chip, Muted } from "./components/ClaimWidgets";
import {
  CLAIM_STATUS,
  STAGE_LABEL,
  SUB_STAGE,
  claimBalance,
  formatDate,
  formatMoney,
} from "./utils";

const ALL = "all";

export default function ClaimMaster({ facilityId }: { facilityId: string }) {
  const { t } = useTranslation();
  const { qParams, updateQuery, Pagination, resultsPerPage } = useFilters({
    limit: 20,
    disableCache: true,
  });

  const status =
    qParams.status && qParams.status in CLAIM_STATUS
      ? (qParams.status as ClaimStatus)
      : undefined;

  const { data, isLoading } = useQuery({
    queryKey: ["nhcx-claims", facilityId, qParams],
    queryFn: query(nhcxApi.listClaims, {
      pathParams: { facilityId },
      queryParams: {
        status,
        patient: qParams.patient,
        search: qParams.search,
        limit: resultsPerPage,
        offset: ((qParams.page || 1) - 1) * resultsPerPage,
      },
    }),
  });

  const count = data?.count ?? 0;
  const title = qParams.patient_name
    ? t("nhcx_n_claims_for", { count, name: qParams.patient_name })
    : t("nhcx_n_claims", { count });

  return (
    <Page
      title={t("nhcx_claims")}
      options={
        <Button variant="primary" asChild>
          <Link
            href={`/facility/${facilityId}/claims/search${
              qParams.patient ? `?patient=${qParams.patient}` : ""
            }`}
          >
            <PlusIcon className="size-4" />
            {t("nhcx_new_claim")}
          </Link>
        </Button>
      }
    >
      <div className="mt-4 flex flex-col gap-4">
        <Card>
          <CardContent className="pt-6 text-sm text-gray-700 space-y-1">
            <p>{t("nhcx_master_intro")}</p>
            <p className="text-gray-500">{t("nhcx_master_intro_gateway")}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <CardTitle>{title}</CardTitle>
            <div className="flex flex-wrap items-center gap-2">
              <PatientIdentifierFilter
                patientId={qParams.patient}
                patientName={qParams.patient_name}
                onSelect={(patientId, patientName) =>
                  updateQuery({
                    patient: patientId,
                    patient_name: patientName,
                  })
                }
                placeholder={t("filter_by_patient")}
                className="w-full sm:w-auto"
              />
              <Select
                value={status ?? ALL}
                onValueChange={(value) =>
                  updateQuery({ status: value === ALL ? undefined : value })
                }
              >
                <SelectTrigger className="w-48">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value={ALL}>{t("nhcx_all_claims")}</SelectItem>
                  {(Object.keys(CLAIM_STATUS) as ClaimStatus[]).map((s) => (
                    <SelectItem key={s} value={s}>
                      {t(CLAIM_STATUS[s].label)}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {isLoading ? (
              <TableSkeleton count={5} />
            ) : !data?.results.length ? (
              <Muted>{t("nhcx_no_claims_yet")}</Muted>
            ) : (
              <div className="overflow-x-auto">
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>{t("nhcx_col_claim")}</TableHead>
                      <TableHead>{t("nhcx_beneficiary")}</TableHead>
                      <TableHead>{t("nhcx_policy")}</TableHead>
                      <TableHead>{t("nhcx_payer")}</TableHead>
                      <TableHead className="text-right">
                        {t("nhcx_balance")}
                      </TableHead>
                      <TableHead>{t("nhcx_stage")}</TableHead>
                      <TableHead>{t("status")}</TableHead>
                      <TableHead>{t("nhcx_opened")}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {data.results.map((claim) => {
                      const sub = SUB_STAGE[claim.sub_stage];
                      const st = CLAIM_STATUS[claim.status];
                      return (
                        <TableRow key={claim.id}>
                          <TableCell>
                            <Link
                              href={`/facility/${facilityId}/claims/${claim.id}`}
                              className="font-medium text-primary-700 hover:underline"
                            >
                              {claim.claim_no}
                            </Link>
                          </TableCell>
                          <TableCell>
                            <div>
                              {claim.beneficiary_name || t("nhcx_unknown")}
                            </div>
                            <div className="text-xs text-gray-500">
                              {claim.member_id || "-"}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>
                              {claim.product_name || claim.plan_name || "-"}
                            </div>
                            <div className="text-xs text-gray-500">
                              {claim.policy_code || "-"}
                            </div>
                          </TableCell>
                          <TableCell>
                            {claim.payer_name || claim.payer_id || "-"}
                          </TableCell>
                          <TableCell className="text-right">
                            {formatMoney(claimBalance(claim))}
                          </TableCell>
                          <TableCell>
                            {claim.stage && sub && (
                              <Chip tone={sub.tone}>
                                {t(STAGE_LABEL[claim.stage] ?? claim.stage)}:{" "}
                                {t(sub.label)}
                              </Chip>
                            )}
                          </TableCell>
                          <TableCell>
                            {st && <Chip tone={st.tone}>{t(st.label)}</Chip>}
                          </TableCell>
                          <TableCell>
                            {formatDate(claim.created_date)}
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </div>
            )}
            {count > resultsPerPage && (
              <div className="mt-4">
                <Pagination totalCount={count} />
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </Page>
  );
}
