import { motion } from "framer-motion";
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { ChartRenderer } from "./ChartRenderer";

interface QAResponseProps {
  question: string;
  answer: string;
}

const QAResponse = ({ question, answer }: QAResponseProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="result-card min-h-[150px]"
    >
      <p className="text-sm font-medium text-foreground mb-4 flex items-start gap-2">
        <span className="text-primary shrink-0">Q:</span>
        {question}
      </p>
      
      <div className="text-sm text-foreground/80 leading-relaxed pl-6 border-l-2 border-primary/30">
        <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-a:text-primary prose-table:border-collapse prose-th:bg-secondary prose-th:p-2 prose-td:p-2 prose-td:border-b">
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
            {answer || "Thinking..."}
          </ReactMarkdown>
        </div>
      </div>
    </motion.div>
  );
};

export default QAResponse;
