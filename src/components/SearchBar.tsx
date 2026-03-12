import { useState } from "react";
import { motion } from "framer-motion";
import { Send } from "lucide-react";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  onAsk: (question: string) => void;
  isLoading?: boolean;
}

const SearchBar = ({ onAsk, isLoading }: SearchBarProps) => {
  const [question, setQuestion] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!question.trim() || isLoading) return;
    onAsk(question.trim());
    setQuestion("");
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="sticky bottom-4 z-10"
    >
      <form
        onSubmit={handleSubmit}
        className="flex items-center gap-2 bg-card border border-border rounded-xl p-2 shadow-lg"
      >
        <input
          type="text"
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about a specific part of the PDF..."
          className="flex-1 bg-transparent text-sm text-foreground placeholder:text-muted-foreground outline-none px-3 py-2 font-body"
          disabled={isLoading}
        />
        <Button
          type="submit"
          variant="gold"
          size="icon"
          disabled={!question.trim() || isLoading}
          className="shrink-0 h-9 w-9"
        >
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </motion.div>
  );
};

export default SearchBar;
