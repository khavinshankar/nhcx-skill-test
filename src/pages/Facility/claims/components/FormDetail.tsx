import { useTranslation } from "react-i18next";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/Common/Table";

import { ClaimForm } from "@/types/nhcx/nhcx";

import { Chip, Muted } from "@/pages/Facility/claims/components/ClaimWidgets";
import { answerTypeKey } from "@/pages/Facility/claims/utils";

// S7.3 Form Detail: one questionnaire, read-only.
export default function FormDetail({ form }: { form: ClaimForm }) {
  const { t } = useTranslation();
  if (!form.questions.length) {
    return <Muted>{t("nhcx_form_no_questions")}</Muted>;
  }
  return (
    <div className="overflow-x-auto">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>{t("nhcx_question")}</TableHead>
            <TableHead>{t("nhcx_answer_type")}</TableHead>
            <TableHead>{t("nhcx_options")}</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {form.questions.map((q) => {
            const typeKey = answerTypeKey(q.type);
            return (
              <TableRow key={q.linkId}>
                <TableCell>
                  <span style={{ paddingLeft: `${(q.depth ?? 0) * 1}rem` }}>
                    {q.text || q.linkId}
                    {q.required && <span className="text-red-600"> *</span>}
                  </span>
                </TableCell>
                <TableCell>{typeKey ? t(typeKey) : q.type}</TableCell>
                <TableCell>
                  {q.options?.length ? (
                    <div className="flex flex-wrap gap-1">
                      {q.options.map((o) => (
                        <Chip key={o} tone="info">
                          {o}
                        </Chip>
                      ))}
                    </div>
                  ) : (
                    "-"
                  )}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}
