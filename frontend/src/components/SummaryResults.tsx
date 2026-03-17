import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Copy, Download, FileText } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from "sonner";

interface SummaryResultsProps {
  summaryText: string;
  onDownloadPDF?: () => void;
}

const SummaryResults = ({ summaryText, onDownloadPDF }: SummaryResultsProps) => {

  const handleCopy = () => {
    navigator.clipboard.writeText(summaryText);
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
      {/* Generated Summary wrapped in Markdown */}
      <motion.div variants={item} className="result-card p-6 border rounded-xl bg-card text-card-foreground shadow-sm">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-display prose-headings:font-semibold prose-a:text-primary prose-table:border-collapse prose-th:bg-secondary prose-th:p-2 prose-td:p-2 prose-td:border-b">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {summaryText || "No summary was generated."}
          </ReactMarkdown>
        </div>
      </motion.div>

      {/* Action buttons */}
      <motion.div variants={item} className="flex gap-3">
        <Button variant="download" size="sm" className="flex-1">
          <FileText className="w-4 h-4" /> TXT
        </Button>
        <Button variant="download" size="sm" className="flex-1" onClick={onDownloadPDF}>
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
