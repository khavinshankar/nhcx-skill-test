import { ClaimState } from "@/types/nhcx/nhcx";

export type ClaimTabKey =
  | "eligibility"
  | "plan"
  | "lines"
  | "validate"
  | "verification"
  | "preauth"
  | "communication"
  | "claim"
  | "payments";

export const CLAIM_TABS: { key: ClaimTabKey; label: string }[] = [
  { key: "eligibility", label: "nhcx_tab_eligibility" },
  { key: "plan", label: "nhcx_tab_plan" },
  { key: "lines", label: "nhcx_tab_lines" },
  { key: "validate", label: "nhcx_tab_validate" },
  { key: "verification", label: "nhcx_tab_verification" },
  { key: "preauth", label: "nhcx_tab_preauth" },
  { key: "communication", label: "nhcx_tab_communication" },
  { key: "claim", label: "nhcx_tab_claim" },
  { key: "payments", label: "nhcx_tab_payments" },
];

export interface ClaimTabProps {
  facilityId: string;
  claimId: string;
  state: ClaimState;
  goTo: (tab: ClaimTabKey) => void;
}
