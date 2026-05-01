import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Copy, Download, FileText } from "lucide-react";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { toast } from "sonner";
import { ChartRenderer } from "./ChartRenderer";

interface SummaryResultsProps {
  summaryText: string;
  onDownloadPDF?: () => void;
}

const SummaryResults = ({ summaryText, onDownloadPDF }: SummaryResultsProps) => {

  const handleCopy = () => {
    navigator.clipboard.writeText(summaryText);
    toast.success("Copied to clipboard!");
  };

  const handleDownloadTxt = () => {
    const raw = summaryText || "";
    // TXT export can't render charts; strip `recharts` code blocks to keep it readable.
    const text = raw
      .replace(/```recharts[\s\S]*?```/g, "[Chart omitted in TXT export]")
      .replace(/```[\s\S]*?```/g, (block) => {
        // Keep non-recharts code blocks as plain text (remove fences).
        return block.replace(/^```[^\n]*\n?/, "").replace(/\n?```$/, "");
      })
      .trim();
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "summary.txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
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
      <motion.div variants={item} className="result-card p-6 border rounded-xl bg-card text-card-foreground shadow-sm min-h-[200px]">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-display prose-headings:font-semibold prose-h3:text-primary prose-h3:mt-6 prose-h3:mb-3 prose-a:text-primary prose-table:border-collapse prose-th:bg-secondary prose-th:p-2 prose-td:p-2 prose-td:border-b">
          <ReactMarkdown 
            remarkPlugins={[remarkGfm]}
            components={{
              code({ node, className, children, ...props }: any) {
                const match = /language-(\w+)/.exec(className || "");
                if (match && match[1] === "recharts") {
                   return <ChartRenderer dataStr={String(children).replace(/\n$/, '')} />;
                }
                return <code className={className} {...props}>{children}</code>;
              }
            }}
          >
            {summaryText || "No summary was generated."}
          </ReactMarkdown>
        </div>
      </motion.div>

      {/* Action buttons */}
      <motion.div variants={item} className="flex gap-3">
        <Button variant="download" size="sm" className="flex-1" onClick={handleDownloadTxt}>
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
