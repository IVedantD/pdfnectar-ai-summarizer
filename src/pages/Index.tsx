import { useState, useCallback, useEffect } from "react";
import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import DropZone from "@/components/DropZone";
import LoadingSteps from "@/components/LoadingSteps";
import SummaryResults from "@/components/SummaryResults";
import SearchBar from "@/components/SearchBar";
import QAResponse from "@/components/QAResponse";
import HistoryPanel from "@/components/HistoryPanel";
import beeLogo from "@/assets/bee-logo.png";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "sonner";

type SummaryLength = "short" | "medium" | "detailed";
type Language = "en" | "hi";
type AppState = "idle" | "loading" | "results";

interface QA {
  question: string;
  answer: string;
}

interface HistoryItem {
  id: string;
  file_name: string;
  summary_length: string;
  language: string;
  word_count: number | null;
  created_at: string;
}

const MOCK_ANSWERS: Record<string, string> = {
  default:
    "Based on the document analysis, the proposed neural architecture achieves a 34% improvement in processing efficiency. The cross-validation results are consistent across all benchmark datasets, with the novel attention mechanism reducing computational overhead by 2.3x compared to the baseline model.",
};

const Index = () => {
  const [file, setFile] = useState<File | null>(null);
  const [length, setLength] = useState<SummaryLength>("medium");
  const [language, setLanguage] = useState<Language>("en");
  const [state, setState] = useState<AppState>("idle");
  const [qaList, setQaList] = useState<QA[]>([]);
  const [qaLoading, setQaLoading] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);

  // Fetch history on mount
  useEffect(() => {
    fetchHistory();
  }, []);

  const fetchHistory = async () => {
    const { data, error } = await supabase
      .from("pdf_summaries")
      .select("id, file_name, summary_length, language, word_count, created_at")
      .order("created_at", { ascending: false })
      .limit(20);

    if (!error && data) {
      setHistory(data);
    }
  };

  const saveToHistory = async (fileName: string) => {
    const { error } = await supabase.from("pdf_summaries").insert({
      file_name: fileName,
      summary_length: length,
      language,
      key_points: [
        "34% improvement in processing efficiency",
        "Consistent cross-validation results",
        "Novel attention mechanism reduces overhead by 2.3x",
      ],
      action_items: [
        "Review supplementary materials",
        "Compare with Smith et al. methodology",
        "Validate on custom dataset",
      ],
      word_count: 245,
      reading_time: "2 min",
    });

    if (error) {
      console.error("Failed to save history:", error);
    } else {
      fetchHistory();
    }
  };

  const handleGenerate = () => {
    if (!file) return;
    setState("loading");
  };

  const handleComplete = useCallback(() => {
    setState("results");
    if (file) {
      saveToHistory(file.name);
    }
  }, [file, length, language]);

  const handleReset = () => {
    setFile(null);
    setState("idle");
    setQaList([]);
  };

  const handleAsk = (question: string) => {
    setQaLoading(true);
    // Simulate AI response
    setTimeout(() => {
      setQaList((prev) => [
        ...prev,
        { question, answer: MOCK_ANSWERS.default },
      ]);
      setQaLoading(false);
    }, 1500);
  };

  const handleHistorySelect = (id: string) => {
    // For now, just show a toast - in the future this would load the saved summary
    toast.info("Loading saved summary...");
    setState("results");
    setQaList([]);
  };

  const handleHistoryDelete = async (id: string) => {
    const { error } = await supabase
      .from("pdf_summaries")
      .delete()
      .eq("id", id);

    if (!error) {
      setHistory((prev) => prev.filter((item) => item.id !== id));
      toast.success("Summary removed from history");
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[600px] mx-auto px-4 py-8 sm:py-12 pb-24">
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
              {/* History */}
              <HistoryPanel
                items={history}
                onSelect={handleHistorySelect}
                onDelete={handleHistoryDelete}
              />

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

              {/* Q&A Responses */}
              {qaList.map((qa, i) => (
                <QAResponse key={i} question={qa.question} answer={qa.answer} />
              ))}

              {qaLoading && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="result-card flex items-center gap-3"
                >
                  <div className="w-4 h-4 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  <span className="text-sm text-muted-foreground">Thinking...</span>
                </motion.div>
              )}

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

      {/* Sticky Search Bar - only visible in results state */}
      {state === "results" && (
        <div className="fixed bottom-0 left-0 right-0 bg-background/80 backdrop-blur-md border-t border-border/50 px-4 py-3">
          <div className="max-w-[600px] mx-auto">
            <SearchBar onAsk={handleAsk} isLoading={qaLoading} />
          </div>
        </div>
      )}
    </div>
  );
};

export default Index;
