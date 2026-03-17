import { motion } from "framer-motion";
import { Check, Loader2 } from "lucide-react";
import { useEffect, useState } from "react";

const steps = [
  { label: "Extracting text...", duration: 5 },
  { label: "Analyzing content...", duration: 10 },
  { label: "Creating summary...", duration: 15 },
];

interface LoadingStepsProps {
  onComplete: () => void;
}

const LoadingSteps = ({ onComplete }: LoadingStepsProps) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [elapsed, setElapsed] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setElapsed((prev) => {
        const next = prev + 1;
        if (next >= 5 && currentStep === 0) setCurrentStep(1);
        if (next >= 10 && currentStep <= 1) setCurrentStep(2);
        if (next >= 15) {
          clearInterval(interval);
          onComplete();
        }
        return next;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [currentStep, onComplete]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="result-card flex flex-col gap-4"
    >
      {steps.map((step, i) => (
        <div key={i} className="flex items-center gap-3">
          {i < currentStep ? (
            <Check className="w-5 h-5 text-primary" />
          ) : i === currentStep ? (
            <Loader2 className="w-5 h-5 text-primary animate-spin" />
          ) : (
            <div className="w-5 h-5 rounded-full border-2 border-border" />
          )}
          <span
            className={`text-sm ${
              i <= currentStep ? "text-foreground" : "text-muted-foreground"
            }`}
          >
            {step.label} ({step.duration}s)
          </span>
        </div>
      ))}
      <div className="w-full bg-secondary rounded-full h-1.5 mt-2">
        <motion.div
          className="bg-primary h-1.5 rounded-full"
          initial={{ width: "0%" }}
          animate={{ width: `${Math.min((elapsed / 15) * 100, 100)}%` }}
          transition={{ duration: 0.5 }}
        />
      </div>
    </motion.div>
  );
};

export default LoadingSteps;
