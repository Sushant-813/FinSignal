import { useEffect, useState } from "react";
import { CategoryDistributionPanel } from "../components/CategoryDistributionPanel.tsx";
import { MerchantAnalyticsPanel } from "../components/MerchantAnalyticsPanel.tsx";
import { ReportingScopeBar } from "../components/ReportingScopeBar.tsx";
import { TrendsChartPanel } from "../components/TrendsChartPanel.tsx";
import { useReportingScopeParams } from "../hooks/useReportingScopeParams.ts";

function usePrefersReducedMotion(): boolean {
  const [reduced, setReduced] = useState(() =>
    typeof window !== "undefined" && typeof window.matchMedia === "function"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false
  );

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    const onChange = (event: MediaQueryListEvent) => setReduced(event.matches);
    mq.addEventListener("change", onChange);
    return () => mq.removeEventListener("change", onChange);
  }, []);

  return reduced;
}

export function AnalyticsPage() {
  const reducedMotion = usePrefersReducedMotion();
  const {
    scope,
    controls,
    hadInvalidUrlParams,
    setScope,
    resetScope,
    setInterval,
    setDirection,
    setMerchantSortBy,
    setMerchantLimit,
    setMerchantOffset,
  } = useReportingScopeParams();

  return (
    <div className="mx-auto max-w-6xl space-y-6">
      <div>
        <h1 className="text-[24px] leading-8 font-semibold tracking-tight text-text-primary">
          Analytics
        </h1>
        <p className="text-sm text-text-secondary">
          Backend-computed time-series trends, category breakdowns, and debit merchant rankings.
        </p>
      </div>

      <ReportingScopeBar
        scope={scope}
        hadInvalidUrlParams={hadInvalidUrlParams}
        timezoneNote="Calendar bucketing uses the selected IANA timezone on Trends; Categories and Merchants aggregate over [from_time, to_time)."
        onApply={setScope}
        onReset={resetScope}
      />

      <TrendsChartPanel
        scope={scope}
        interval={controls.interval}
        onIntervalChange={setInterval}
        reducedMotion={reducedMotion}
      />

      <div className="space-y-6">
        <CategoryDistributionPanel
          scope={scope}
          direction={controls.direction}
          onDirectionChange={setDirection}
          reducedMotion={reducedMotion}
        />

        <MerchantAnalyticsPanel
          scope={scope}
          sortBy={controls.merchantSortBy}
          limit={controls.merchantLimit}
          offset={controls.merchantOffset}
          onSortByChange={setMerchantSortBy}
          onLimitChange={setMerchantLimit}
          onOffsetChange={setMerchantOffset}
          reducedMotion={reducedMotion}
        />
      </div>
    </div>
  );
}
