"""Deterministic mock AI provider for testing and offline generation (Phase 10)."""

import asyncio
import json
import uuid

from finsignal.ai.providers.base import (
    BaseLLMProvider,
    ProviderRequest,
    ProviderResponse,
)


class MockProviderError(Exception):
    """Exception raised when Mock provider simulates an upstream failure."""


class MockLLMProvider(BaseLLMProvider):
    """Deterministic, context-aware Mock AI provider for Phase 10.

    Inspects structured InvestigationEvidenceContext directly to generate realistic,
    grounded summaries without natural language parsing or external network calls.
    """

    def __init__(
        self,
        simulate_delay: float = 0.0,
        simulate_timeout: bool = False,
        simulate_provider_error: bool = False,
        simulate_invalid_json: bool = False,
    ) -> None:
        self.simulate_delay = simulate_delay
        self.simulate_timeout = simulate_timeout
        self.simulate_provider_error = simulate_provider_error
        self.simulate_invalid_json = simulate_invalid_json

    async def generate(self, request: ProviderRequest) -> ProviderResponse:
        """Generate deterministic output conforming to AISummaryOutput based on typed context."""
        # Simulated fault injection
        if self.simulate_delay > 0:
            await asyncio.sleep(self.simulate_delay)

        if self.simulate_timeout:
            raise TimeoutError("Mock provider simulated request timeout.")

        if self.simulate_provider_error:
            raise MockProviderError(
                "Mock provider simulated upstream server failure (HTTP 500)."
            )

        if self.simulate_invalid_json:
            return ProviderResponse(
                raw_content="MALFORMED_NON_JSON_RESPONSE: {executive_summary: incomplete...",
                provider="mock",
                model=request.model,
            )

        # Context-grounded deterministic synthesis
        ctx = request.context
        ptx = ctx.primary_transaction
        risk = ctx.latest_risk_analysis
        factors = ctx.risk_factors
        meta = ctx.context_metadata

        ptx_id = ptx.get("id")
        ptx_uuid = uuid.UUID(str(ptx_id)) if ptx_id else uuid.uuid4()
        ptx_amount = ptx.get("amount", "0.00")
        ptx_curr = ptx.get("currency", "USD")
        ptx_cat = ptx.get("category", "GENERAL")
        ptx_pm = ptx.get("payment_method", "UNKNOWN")

        # Gather real evidence UUIDs from context for grounding
        available_citations: list[str] = [str(ptx_uuid)]
        for ev in ctx.evidence_items:
            if "id" in ev:
                available_citations.append(str(ev["id"]))

        # 1. Executive Summary
        risk_tier = risk.get("risk_level", "LOW") if risk else "UNASSESSED"
        score_val = risk.get("score", "0.0") if risk else "0.0"
        exec_summary = (
            f"Case analysis for primary transaction {ptx.get('external_transaction_id', ptx_uuid)} "
            f"evaluated at {risk_tier} risk tier (score: {score_val}). Transaction involves {ptx_amount} {ptx_curr} "
            f"via {ptx_pm} ({ptx_cat}). "
            f"Corroborated by {len(ctx.evidence_items)} attached evidence record(s) and {len(factors)} active risk factor(s)."
        )

        # 2. Observed Facts (Grounded in primary tx and attached evidence)
        observed_facts: list[dict[str, object]] = [
            {
                "claim": f"Primary transaction of {ptx_amount} {ptx_curr} executed with direction {ptx.get('direction', 'DEBIT')}.",
                "evidence_ids": [str(ptx_uuid)],
            }
        ]
        for ev in ctx.evidence_items:
            observed_facts.append(
                {
                    "claim": f"Documented finding: {ev.get('title', 'Evidence record')} ({ev.get('evidence_type', 'GENERAL')}).",
                    "evidence_ids": [str(ev["id"])],
                }
            )

        # 3. Derived Signals (Grounded in risk factors)
        derived_signals: list[dict[str, object]] = []
        if risk and factors:
            for f in factors:
                factor_citation = str(f.get("id", ptx_uuid))
                derived_signals.append(
                    {
                        "claim": f"Risk factor {f.get('factor_code')}: {f.get('description', 'Rule triggered')} [Severity: {f.get('severity')}].",
                        "evidence_ids": [factor_citation],
                    }
                )
        else:
            derived_signals.append(
                {
                    "claim": f"Composite automated score computed at {score_val} ({risk_tier}).",
                    "evidence_ids": [str(ptx_uuid)],
                }
            )

        # 4. Potential Interpretations
        interpretations: list[str] = []
        if risk_tier in ("HIGH", "CRITICAL"):
            interpretations.append(
                "Behavioral anomalies and elevated risk factors indicate potential account takeover or unauthorized spending."
            )
        else:
            interpretations.append(
                "Observed transaction patterns remain within baseline operational thresholds with low immediate indicators of fraud."
            )

        # 5. Uncertainties & Limitations
        limitations: list[str] = []
        if meta.omitted_evidence_count > 0:
            limitations.append(
                f"Context budget constraint: {meta.omitted_evidence_count} evidence items of types {meta.omitted_evidence_types} were omitted from model prompt."
            )
        if not ctx.related_transactions:
            limitations.append(
                "No related transactions have been linked to this investigation; cross-account velocity could not be corroborated."
            )
        if not ctx.evidence_items:
            limitations.append(
                "No independent evidence records have been attached to this investigation case."
            )

        output_dict = {
            "executive_summary": exec_summary,
            "observed_facts": observed_facts,
            "derived_signals": derived_signals,
            "potential_interpretations": interpretations,
            "uncertainties_and_limitations": limitations,
        }

        return ProviderResponse(
            raw_content=json.dumps(output_dict),
            provider="mock",
            model=request.model,
        )
