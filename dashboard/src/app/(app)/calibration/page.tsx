import { PageHeader } from "@/components/page-header";
import { CalibrationTraining } from "./_client";

export const metadata = {
  title: "Calibration training · INFORMATIV",
};

export const dynamic = "force-dynamic";

export default function CalibrationPage() {
  return (
    <div className="flex flex-col gap-6 p-6">
      <PageHeader
        title="Calibration training"
        description="Ten advertising-domain binary forecasts with immediate feedback and live Brier scoring. Based on the Tetlock/Mellers protocol from the Good Judgment Project — trains you to produce calibrated probability estimates, not round numbers that mean nothing."
      />
      <CalibrationTraining />
    </div>
  );
}
