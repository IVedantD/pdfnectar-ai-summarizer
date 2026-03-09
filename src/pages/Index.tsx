import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import DropZone from "@/components/DropZone";
import LoadingSteps from "@/components/LoadingSteps";
import SummaryResults from "@/components/SummaryResults";
import beeLogo from "@/assets/bee-logo.png";

type SummaryLength = "short" | "medium" | "detailed";
type Language = "en" | "hi";
type AppState = "idle" | "loading" | "results";

const Index = () => {
  const [file, setFile] = useState<File | null>(null);
  const [length, setLength] = useState<SummaryLength>("medium");
  const [language, setLanguage] = useState<Language>("en");
  const [state, setState] = useState<AppState>("idle");

  const handleGenerate = () => {
    if (!file) return;
    setState("loading");
  };

  const handleComplete = useCallback(() => setState("results"), []);

  const handleReset = () => {
    setFile(null);
    setState("idle");
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[600px] mx-auto px-4 py-8 sm:py-12">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-center mb-8"
        >
          <div className="flex items-center justify-center gap-3 mb-2">
            <img src={beeLogo} alt="PDFNectar bee logo" className="w-10 h-10" />
            <h1 className="text-3xl sm:text-4xl font-display font-bold text-foreground tracking-tight">
              PDFNectar.ai
            </h1>
          </div>
          <p className="text-muted-foreground text-sm sm:text-base">
            Extract notes from any PDF in 30 seconds
          </p>
        </motion.header>

        {/* Main Content */}
        <motion.main
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="flex flex-col gap-5"
        >
          {state === "idle" && (
            <>
              <DropZone onFileSelect={setFile} selectedFile={file} />

              {/* Length Options */}
              <div className="flex gap-2">
                {([
                  { key: "short", label: "Short (100 words)" },
                  { key: "medium", label: "Medium (300 words)" },
                  { key: "detailed", label: "Detailed (800 words)" },
                ] as const).map((opt) => (
                  <Button
                    key={opt.key}
                    variant={length === opt.key ? "gold-active" : "gold-outline"}
                    size="sm"
                    className="flex-1 text-xs sm:text-sm"
                    onClick={() => setLength(opt.key)}
                  >
                    {opt.label}
                  </Button>
                ))}
              </div>

              {/* Language Toggle */}
              <div className="flex items-center justify-center gap-1 bg-secondary rounded-lg p-1">
                <button
                  onClick={() => setLanguage("en")}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                    language === "en"
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  English
                </button>
                <button
                  onClick={() => setLanguage("hi")}
                  className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-all ${
                    language === "hi"
                      ? "bg-card text-foreground shadow-sm"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  हिन्दी
                </button>
              </div>

              {/* Generate Button */}
              <Button
                variant="gold"
                size="lg"
                className="w-full text-base h-12"
                disabled={!file}
                onClick={handleGenerate}
              >
                Generate Summary ✨
              </Button>
            </>
          )}

          {state === "loading" && <LoadingSteps onComplete={handleComplete} />}

          {state === "results" && (
            <>
              <SummaryResults language={language} />
              <Button
                variant="gold-outline"
                className="w-full"
                onClick={handleReset}
              >
                Summarize another PDF
              </Button>
            </>
          )}
        </motion.main>

        {/* Footer */}
        <motion.footer
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
          className="text-center mt-12 text-xs text-muted-foreground"
        >
          Free • No signup needed • Powered by GPT-4o
        </motion.footer>
      </div>
    </div>
  );
};

export default Index;
