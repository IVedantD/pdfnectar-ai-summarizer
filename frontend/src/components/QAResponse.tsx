import { motion } from "framer-motion";

interface QAResponseProps {
  question: string;
  answer: string;
}

const QAResponse = ({ question, answer }: QAResponseProps) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className="result-card"
    >
      <p className="text-sm font-medium text-foreground mb-2 flex items-start gap-2">
        <span className="text-primary shrink-0">Q:</span>
        {question}
      </p>
      <p className="text-sm text-foreground/80 leading-relaxed pl-6 border-l-2 border-primary/30">
        {answer}
      </p>
    </motion.div>
  );
};

export default QAResponse;
