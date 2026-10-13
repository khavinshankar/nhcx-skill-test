import { useMutation, useQuery } from "@tanstack/react-query";
import { CirclePlus, SearchIcon } from "lucide-react";
import { Link, navigate, useQueryParams } from "raviger";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
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

import { PolicyResult, SearchIdType } from "@/types/nhcx/nhcx";
import nhcxApi from "@/types/nhcx/nhcxApi";

import { ErrorText, Muted } from "./components/ClaimWidgets";
import { nhcxCall, refusalText } from "./useClaimAction";
import { ID_TYPES } from "./utils";

const isIdType = (v?: string): v is SearchIdType =>
  !!v && ID_TYPES.some((o) => o.value === v);

// S1 Search Policy + S2 Select Policy. The search runs from the query string
// (`id_type`, `id_value`), so a result can be bookmarked and refreshed.
export default function SearchPolicy({ facilityId }: { facilityId: string }) {
  const { t } = useTranslation();
  const [qParams, setQParams] = useQueryParams<{
    id_type?: string;
    id_value?: string;
    patient?: string;
    searched?: string;
  }>();
  const [idType, setIdType] = useState<string>(qParams.id_type || "MemberId");
  const [idValue, setIdValue] = useState(qParams.id_value || "");
  const [formError, setFormError] = useState<string>();

  useEffect(() => {
    if (qParams.id_type) setIdType(qParams.id_type);
    if (qParams.id_value !== undefined) setIdValue(qParams.id_value);
  }, [qParams.id_type, qParams.id_value]);

  const searched = qParams.searched === "1";
  const activeType = isIdType(qParams.id_type) ? qParams.id_type : undefined;
  const activeValue = (qParams.id_value || "").trim();

  const search = useQuery({
    queryKey: ["nhcx-policy-search", facilityId, activeType, activeValue],
    enabled: searched && !!activeType && !!activeValue,
    retry: false,
    queryFn: async ({ signal }) => {
      const res = await nhcxCall(nhcxApi.policySearch, {
        pathParams: { facilityId },
        body: { identifiertype: activeType, identifiervalue: activeValue },
        signal,
      });
      if (res.ok === false) throw new Error(res.error || res.message || "");
      return res;
    },
  });

  const openClaim = useMutation({
    mutationFn: (policy: PolicyResult) =>
      nhcxCall(nhcxApi.openClaim, {
        pathParams: { facilityId },
        body: {
          policy,
          id_type: activeType,
          id_value: activeValue,
          patient: qParams.patient || undefined,
        },
      }),
    onSuccess: (res) => {
      if (res.ok === false || !res.claim_id) {
        toast.error(res.error || t("something_went_wrong"));
        return;
      }
      toast.success(res.message || t("nhcx_claim_opened"));
      navigate(`/facility/${facilityId}/claims/${res.claim_id}`);
    },
    onError: (error) =>
      toast.error(refusalText(error, t("something_went_wrong"))),
  });

  const submit = (e: React.SyntheticEvent) => {
    e.preventDefault();
    if (!isIdType(idType)) {
      setFormError(t("nhcx_choose_identifier_type"));
      return;
    }
    if (!idValue.trim()) {
      setFormError(t("nhcx_enter_identifier_value"));
      return;
    }
    setFormError(undefined);
    setQParams({
      id_type: idType,
      id_value: idValue.trim(),
      patient: qParams.patient,
      searched: "1",
    });
    if (activeType === idType && activeValue === idValue.trim()) {
      search.refetch();
    }
  };

  const policies = search.data?.policies ?? [];
  const failed = search.isError
    ? refusalText(search.error, t("something_went_wrong"))
    : undefined;
  const discoverHref = `/facility/${facilityId}/claims/discovery?${new URLSearchParams(
    {
      id_type: activeType || idType,
      id_value: activeValue || idValue,
      ...(qParams.patient ? { patient: qParams.patient } : {}),
    },
  ).toString()}`;

  return (
    <Page
      title={t("nhcx_policy_search")}
      options={
        <Button variant="outline" asChild>
          <Link href={`/facility/${facilityId}/claims`}>
            {t("nhcx_claims")}
          </Link>
        </Button>
      }
    >
      <div className="mt-4 flex flex-col gap-4">
        <Card>
          <CardHeader>
            <CardTitle>{t("nhcx_search_policy_title")}</CardTitle>
          </CardHeader>
          <CardContent>
            <form
              onSubmit={submit}
              className="flex flex-wrap items-end gap-3"
              noValidate
            >
              <div className="flex flex-col gap-1">
                <Label>{t("nhcx_identifier_type")}</Label>
                <Select value={idType} onValueChange={setIdType}>
                  <SelectTrigger className="w-48">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ID_TYPES.map((o) => (
                      <SelectItem key={o.value} value={o.value}>
                        {t(o.label)}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1">
                <Label htmlFor="nhcx-id-value">
                  {t("nhcx_identifier_value")}
                </Label>
                <Input
                  id="nhcx-id-value"
                  className="min-w-64"
                  value={idValue}
                  onChange={(e) => setIdValue(e.target.value)}
                />
              </div>
              <Button type="submit" variant="primary">
                <SearchIcon className="size-4" />
                {t("nhcx_search_policies")}
              </Button>
            </form>
            {formError && (
              <div className="mt-3">
                <ErrorText>{formError}</ErrorText>
              </div>
            )}
          </CardContent>
        </Card>

        {searched && search.isFetching && (
          <Card>
            <CardContent className="pt-6">
              <TableSkeleton count={3} />
            </CardContent>
          </Card>
        )}

        {searched && !search.isFetching && failed && (
          <Card>
            <CardContent className="pt-6 space-y-3">
              <ErrorText>{failed}</ErrorText>
              <Button variant="outline" size="sm" asChild>
                <Link href={discoverHref}>{t("nhcx_discover_with_payer")}</Link>
              </Button>
            </CardContent>
          </Card>
        )}

        {searched && !search.isFetching && search.isSuccess && (
          <Card>
            <CardHeader>
              <CardTitle>
                {policies.length === 1
                  ? t("nhcx_one_policy_found")
                  : t("nhcx_n_policies_found", { n: policies.length })}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {policies.length === 0 ? (
                <div className="space-y-3">
                  <Muted>{t("nhcx_no_policy_matches")}</Muted>
                  <Button variant="outline" size="sm" asChild>
                    <Link href={discoverHref}>
                      {t("nhcx_discover_with_payer")}
                    </Link>
                  </Button>
                </div>
              ) : (
                <div className="overflow-x-auto">
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>{t("nhcx_beneficiary")}</TableHead>
                        <TableHead>{t("nhcx_product_policy")}</TableHead>
                        <TableHead>{t("nhcx_payer")}</TableHead>
                        <TableHead>{t("nhcx_abha")}</TableHead>
                        <TableHead>{t("nhcx_mobile")}</TableHead>
                        <TableHead />
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {policies.map((p, i) => (
                        <TableRow key={`${p.payer_id}-${p.member_id}-${i}`}>
                          <TableCell>
                            <div>
                              {p.name ||
                                p.beneficiary_name ||
                                t("nhcx_unknown")}
                            </div>
                            <div className="text-xs text-gray-500">
                              {p.member_id || "-"}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>{p.product_name || "-"}</div>
                            <div className="text-xs text-gray-500">
                              {p.policy_code ||
                                p.policy_number ||
                                p.product_id ||
                                "-"}
                            </div>
                          </TableCell>
                          <TableCell>
                            <div>{p.payer_name || p.payer_id || "-"}</div>
                            <div className="text-xs text-gray-500">
                              {p.payer_id || "-"}
                            </div>
                          </TableCell>
                          <TableCell>{p.abha_number || "-"}</TableCell>
                          <TableCell>{p.mobile_number || "-"}</TableCell>
                          <TableCell className="text-right">
                            <Button
                              size="xs"
                              variant="primary"
                              disabled={openClaim.isPending}
                              onClick={() => openClaim.mutate(p)}
                            >
                              <CirclePlus className="size-3" />
                              {t("nhcx_select")}
                            </Button>
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </div>
              )}
            </CardContent>
          </Card>
        )}
      </div>
    </Page>
  );
}
