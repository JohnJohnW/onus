import { Card, CardContent } from "@/components/ui/card";

// Data residency is controlled by whoever operates this deployment, not the firm - so
// this is a read-only statement of where the firm's data is hosted, driven by the
// operator's env config (NEXT_PUBLIC_DATA_REGION), defaulting by demo vs real deployment.
const isDemo = process.env.NEXT_PUBLIC_DEMO === "true";
const region =
  process.env.NEXT_PUBLIC_DATA_REGION || (isDemo ? "United States (demonstration)" : "Australia");

export function DataResidencyPanel() {
  return (
    <Card className="border-neutral-800 bg-neutral-900/50">
      <CardContent className="space-y-3 p-5 text-sm">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <span className="text-neutral-400">Where your data is hosted</span>
          <span className={isDemo ? "font-medium text-amber-300" : "font-medium text-emerald-300"}>
            {region}
          </span>
        </div>
        {isDemo ? (
          <p className="leading-relaxed text-neutral-400">
            This is a demonstration of Onus, hosted in the United States for evaluation only.
            Please do not enter real client information. A production deployment runs on
            Australian-hosted infrastructure so client and AML/CTF records stay onshore.
          </p>
        ) : (
          <p className="leading-relaxed text-neutral-400">
            Your data is hosted in {region}, kept onshore in line with the Privacy Act 1988
            (Australian Privacy Principles), AUSTRAC record-keeping, and your confidentiality
            obligations.
          </p>
        )}
      </CardContent>
    </Card>
  );
}
