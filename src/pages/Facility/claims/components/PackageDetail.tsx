import { useTranslation } from "react-i18next";

import {
  Accordion,
  AccordionContent,
  AccordionItem,
  AccordionTrigger,
} from "@/components/ui/accordion";
import { Button } from "@/components/ui/button";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";

import { Benefit, ClaimForm } from "@/types/nhcx/nhcx";

import {
  Chip,
  DetailList,
  Muted,
} from "@/pages/Facility/claims/components/ClaimWidgets";
import FormDetail from "@/pages/Facility/claims/components/FormDetail";
import { formatMoney } from "@/pages/Facility/claims/utils";

const IMPLANT_FLAGS = [
  "ImplantApplicable",
  "MultipleImplantsAllowed",
  "MaximumImplantsAllowed",
];

function Section({
  value,
  title,
  children,
}: {
  value: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <AccordionItem value={value}>
      <AccordionTrigger>{title}</AccordionTrigger>
      <AccordionContent>{children}</AccordionContent>
    </AccordionItem>
  );
}

// S7.1 Package Detail: everything the payer published about one package.
export default function PackageDetail({
  benefit,
  benefits,
  forms,
  planTitle,
  onOpen,
}: {
  benefit: Benefit;
  benefits: Benefit[];
  forms: ClaimForm[];
  planTitle?: string | null;
  onOpen: (benefit: Benefit) => void;
}) {
  const { t } = useTranslation();
  const extras = benefit.extras ?? [];
  const conditions = Object.entries(benefit.conditions ?? {});
  const docs = benefit.supporting_info ?? [];
  const formsByUrl = new Map(forms.map((f) => [f.url, f]));
  const linkedForms = docs
    .map((d) => (d.form ? formsByUrl.get(d.form) : undefined))
    .filter((f, i, all): f is ClaimForm => !!f && all.indexOf(f) === i);
  const isImplant = benefit.kind === "Implant";
  const implants = extras.filter((e) => e.type === "Implant");
  const tiers = extras.filter((e) => e.type !== "Implant");
  const allowedWith = isImplant
    ? benefits.filter(
        (b) =>
          b.kind !== "Implant" &&
          (b.extras ?? []).some(
            (e) => e.type === "Implant" && e.code === benefit.code,
          ),
      )
    : [];
  const implantEntry = (code: string) =>
    benefits.find((b) => b.kind === "Implant" && b.code === code);

  return (
    <div className="space-y-4">
      <DetailList
        items={[
          { label: t("nhcx_code"), value: benefit.code },
          { label: t("nhcx_type"), value: benefit.kind },
          {
            label: t("nhcx_speciality"),
            value: benefit.category_display || benefit.category_code,
          },
          { label: t("nhcx_package_rate"), value: formatMoney(benefit.rate) },
          { label: t("nhcx_currency"), value: benefit.currency },
          { label: t("nhcx_requirement"), value: benefit.requirement },
          { label: t("nhcx_plan"), value: planTitle },
        ]}
      />
      <Accordion type="multiple">
        {!isImplant && (
          <Section
            value="implants"
            title={t("nhcx_implants_allowed", { n: implants.length })}
          >
            {implants.length ? (
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
                  {implants.map((e) => {
                    const entry = implantEntry(e.code);
                    return (
                      <TableRow key={e.code}>
                        <TableCell>{e.code}</TableCell>
                        <TableCell>{e.label || e.code}</TableCell>
                        <TableCell>{formatMoney(e.rate)}</TableCell>
                        <TableCell>
                          {entry ? (
                            <Button
                              size="xs"
                              variant="secondary"
                              onClick={() => onOpen(entry)}
                            >
                              {t("view")}
                            </Button>
                          ) : (
                            <span className="text-xs text-gray-500">
                              {t("nhcx_not_in_plan")}
                            </span>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            ) : (
              <Muted>{t("nhcx_no_implant")}</Muted>
            )}
            <div className="mt-2 flex flex-wrap gap-1">
              {IMPLANT_FLAGS.filter(
                (f) => benefit.conditions?.[f] !== undefined,
              ).map((f) => (
                <Chip key={f} tone="neutral">
                  {f}: {String(benefit.conditions?.[f])}
                </Chip>
              ))}
            </div>
          </Section>
        )}
        {!isImplant && (
          <Section
            value="tiers"
            title={t("nhcx_ward_icu_tiers", { n: tiers.length })}
          >
            {tiers.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("nhcx_tier")}</TableHead>
                    <TableHead>{t("nhcx_kind")}</TableHead>
                    <TableHead>{t("nhcx_rate")}</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {tiers.map((e) => (
                    <TableRow key={`${e.type}-${e.code}`}>
                      <TableCell>
                        <div>{e.label || e.code}</div>
                        <div className="text-xs text-gray-500">{e.code}</div>
                      </TableCell>
                      <TableCell>{e.type}</TableCell>
                      <TableCell>{formatMoney(e.rate)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Muted>{t("nhcx_no_tier")}</Muted>
            )}
          </Section>
        )}
        {isImplant && (
          <Section
            value="allowed"
            title={t("nhcx_allowed_with", { n: allowedWith.length })}
          >
            {allowedWith.length ? (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>{t("nhcx_code")}</TableHead>
                    <TableHead>{t("nhcx_package")}</TableHead>
                    <TableHead>{t("nhcx_speciality")}</TableHead>
                    <TableHead />
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {allowedWith.map((b) => (
                    <TableRow key={b.id}>
                      <TableCell>{b.code}</TableCell>
                      <TableCell>{b.display || b.code}</TableCell>
                      <TableCell>
                        {b.category_display || b.category_code || "-"}
                      </TableCell>
                      <TableCell>
                        <Button
                          size="xs"
                          variant="secondary"
                          onClick={() => onOpen(b)}
                        >
                          {t("view")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            ) : (
              <Muted>{t("nhcx_no_package_lists_implant")}</Muted>
            )}
          </Section>
        )}
        <Section
          value="conditions"
          title={t("nhcx_claim_conditions", { n: conditions.length })}
        >
          {conditions.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("nhcx_condition")}</TableHead>
                  <TableHead>{t("nhcx_value")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {conditions.map(([k, v]) => (
                  <TableRow key={k}>
                    <TableCell>{k}</TableCell>
                    <TableCell>
                      {v === true || v === "Y" ? t("yes") : String(v ?? "-")}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Muted>{t("nhcx_no_conditions")}</Muted>
          )}
        </Section>
        <Section
          value="docs"
          title={t("nhcx_documents_required", { n: docs.length })}
        >
          {docs.length ? (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>{t("nhcx_code")}</TableHead>
                  <TableHead>{t("nhcx_document")}</TableHead>
                  <TableHead>{t("nhcx_category")}</TableHead>
                  <TableHead>{t("nhcx_form")}</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {docs.map((d, i) => (
                  <TableRow key={`${d.code}-${i}`}>
                    <TableCell>{d.code}</TableCell>
                    <TableCell>{d.display || d.code}</TableCell>
                    <TableCell>
                      {d.category_display || d.category || "-"}
                    </TableCell>
                    <TableCell>
                      {d.form
                        ? formsByUrl.get(d.form)?.title ||
                          t("nhcx_form_not_sent")
                        : "-"}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          ) : (
            <Muted>{t("nhcx_no_documents_mandatory")}</Muted>
          )}
        </Section>
        {linkedForms.length > 0 && (
          <Section
            value="forms"
            title={t("nhcx_forms_to_complete", { n: linkedForms.length })}
          >
            <Accordion type="multiple">
              {linkedForms.map((f) => (
                <AccordionItem key={f.url} value={f.url}>
                  <AccordionTrigger>
                    {f.title} ({f.questions.length})
                  </AccordionTrigger>
                  <AccordionContent>
                    <FormDetail form={f} />
                  </AccordionContent>
                </AccordionItem>
              ))}
            </Accordion>
          </Section>
        )}
      </Accordion>
    </div>
  );
}
