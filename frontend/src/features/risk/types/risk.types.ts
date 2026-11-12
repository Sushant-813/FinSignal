import type { components } from "../../../api/generated/schema.ts";

export type RiskAnalysisResponse = components["schemas"]["RiskAnalysisResponse"];
export type RiskFactorDTO = components["schemas"]["RiskFactorDTO"];
export type RiskLevel = components["schemas"]["RiskLevel"];
export type RiskSeverity = components["schemas"]["RiskSeverity"];
export type RiskFactorCode = components["schemas"]["RiskFactorCode"];
export type RiskAnalyzeRequest = components["schemas"]["RiskAnalyzeRequest"];

export type RiskQueryResult =
  | { readonly kind: "analyzed"; readonly analysis: RiskAnalysisResponse }
  | { readonly kind: "not_analyzed" };
