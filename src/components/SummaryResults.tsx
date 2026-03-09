import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import { Copy, Download, FileText } from "lucide-react";
import { toast } from "sonner";

interface SummaryResultsProps {
  language: "en" | "hi";
}

const enResults = {
  keyPoints: [
    "The study demonstrates a 34% improvement in processing efficiency using the proposed neural architecture.",
    "Cross-validation results show consistent performance across all five benchmark datasets.",
    "The framework introduces a novel attention mechanism that reduces computational overhead by 2.3x.",
  ],
  tables: "**Table 3.2** — Performance Comparison\n\n| Model | Accuracy | F1 Score | Latency |\n|-------|----------|----------|---------|\n| Baseline | 87.2% | 0.85 | 42ms |\n| Proposed | 91.8% | 0.91 | 18ms |\n\n**Formula:** `L = -Σ yᵢ log(ŷᵢ) + λ‖θ‖²`",
  actionItems: [
    "Review supplementary materials in Appendix B for implementation details",
    "Compare results with Smith et al. (2024) methodology",
    "Validate findings on custom dataset before deployment",
  ],
  stats: { words: 245, readingTime: "2 min" },
};

const hiResults = {
  keyPoints: [
    "अध्ययन प्रस्तावित न्यूरल आर्किटेक्चर का उपयोग करके प्रसंस्करण दक्षता में 34% सुधार प्रदर्शित करता है।",
    "क्रॉस-वैलिडेशन परिणाम सभी पांच बेंचमार्क डेटासेट में लगातार प्रदर्शन दिखाते हैं।",
    "फ्रेमवर्क एक नवीन ध्यान तंत्र पेश करता है जो कम्प्यूटेशनल ओवरहेड को 2.3 गुना कम करता है।",
  ],
  tables: enResults.tables,
  actionItems: [
    "कार्यान्वयन विवरण के लिए परिशिष्ट B में पूरक सामग्री की समीक्षा करें",
    "Smith et al. (2024) कार्यप्रणाली से परिणामों की तुलना करें",
    "तैनाती से पहले कस्टम डेटासेट पर निष्कर्षों को मान्य करें",
  ],
  stats: { words: 245, readingTime: "2 मिनट" },
};

const SummaryResults = ({ language }: SummaryResultsProps) => {
  const data = language === "hi" ? hiResults : enResults;

  const handleCopy = () => {
    const text = `Key Points:\n${data.keyPoints.join("\n")}\n\nAction Items:\n${data.actionItems.join("\n")}`;
    navigator.clipboard.writeText(text);
    toast.success("Copied to clipboard!");
  };

  const container = {
    hidden: { opacity: 0 },
    show: { opacity: 1, transition: { staggerChildren: 0.15 } },
  };
  const item = {
    hidden: { opacity: 0, y: 20 },
    show: { opacity: 1, y: 0 },
  };

  return (
    <motion.div
      variants={container}
      initial="hidden"
      animate="show"
      className="flex flex-col gap-4"
    >
      {/* Key Points */}
      <motion.div variants={item} className="result-card">
        <h3 className="text-lg font-semibold font-display text-foreground mb-3">
          📋 3 Key Points
        </h3>
        <ul className="space-y-2">
          {data.keyPoints.map((point, i) => (
            <li key={i} className="text-sm text-foreground/80 leading-relaxed pl-4 border-l-2 border-primary/40">
              {point}
            </li>
          ))}
        </ul>
      </motion.div>

      {/* Tables/Formulas */}
      <motion.div variants={item} className="result-card">
        <h3 className="text-lg font-semibold font-display text-foreground mb-3">
          📊 Important Tables/Formulas
        </h3>
        <div className="text-sm text-foreground/80 leading-relaxed overflow-x-auto">
          <table className="w-full text-sm border-collapse">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left py-2 px-3 font-medium">Model</th>
                <th className="text-left py-2 px-3 font-medium">Accuracy</th>
                <th className="text-left py-2 px-3 font-medium">F1 Score</th>
                <th className="text-left py-2 px-3 font-medium">Latency</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-border/50">
                <td className="py-2 px-3">Baseline</td>
                <td className="py-2 px-3">87.2%</td>
                <td className="py-2 px-3">0.85</td>
                <td className="py-2 px-3">42ms</td>
              </tr>
              <tr>
                <td className="py-2 px-3 font-medium">Proposed</td>
                <td className="py-2 px-3 font-medium">91.8%</td>
                <td className="py-2 px-3 font-medium">0.91</td>
                <td className="py-2 px-3 font-medium">18ms</td>
              </tr>
            </tbody>
          </table>
          <p className="mt-3 font-mono text-xs bg-secondary px-3 py-2 rounded-lg">
            L = -Σ yᵢ log(ŷᵢ) + λ‖θ‖²
          </p>
        </div>
      </motion.div>

      {/* Action Items */}
      <motion.div variants={item} className="result-card">
        <h3 className="text-lg font-semibold font-display text-foreground mb-3">
          ✅ Action Items
        </h3>
        <ul className="space-y-2">
          {data.actionItems.map((a, i) => (
            <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
              <span className="text-primary mt-0.5">•</span>
              {a}
            </li>
          ))}
        </ul>
      </motion.div>

      {/* Stats */}
      <motion.div variants={item} className="result-card">
        <h3 className="text-lg font-semibold font-display text-foreground mb-3">
          📈 Summary Stats
        </h3>
        <div className="flex gap-6 text-sm text-muted-foreground">
          <span>Words: <strong className="text-foreground">{data.stats.words}</strong></span>
          <span>Reading time: <strong className="text-foreground">{data.stats.readingTime}</strong></span>
        </div>
      </motion.div>

      {/* Download buttons */}
      <motion.div variants={item} className="flex gap-3">
        <Button variant="download" size="sm" className="flex-1">
          <FileText className="w-4 h-4" /> TXT
        </Button>
        <Button variant="download" size="sm" className="flex-1">
          <Download className="w-4 h-4" /> PDF
        </Button>
        <Button variant="download" size="sm" className="flex-1" onClick={handleCopy}>
          <Copy className="w-4 h-4" /> Copy
        </Button>
      </motion.div>
    </motion.div>
  );
};

export default SummaryResults;
