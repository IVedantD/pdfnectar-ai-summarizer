import { motion, AnimatePresence } from "framer-motion";
import { Clock, FileText, Trash2, ChevronDown, ChevronUp } from "lucide-react";
import { Button } from "@/components/ui/button";
import { useState } from "react";

interface HistoryItem {
  id: string;
  file_name: string;
  summary_length: string;
  language: string;
  word_count: number | null;
  created_at: string;
}

interface HistoryPanelProps {
  items: HistoryItem[];
  onSelect: (id: string) => void;
  onDelete: (id: string) => void;
}

const HistoryPanel = ({ items, onSelect, onDelete }: HistoryPanelProps) => {
  const [expanded, setExpanded] = useState(false);

  if (items.length === 0) return null;

  const displayItems = expanded ? items : items.slice(0, 3);

  return (
    <motion.div
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      className="result-card"
    >
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold font-display text-foreground flex items-center gap-2">
          <Clock className="w-4 h-4 text-muted-foreground" />
          Recent Summaries
        </h3>
        {items.length > 3 && (
          <Button
            variant="ghost"
            size="sm"
            className="text-xs text-muted-foreground h-7 px-2"
            onClick={() => setExpanded(!expanded)}
          >
            {expanded ? (
              <>Show less <ChevronUp className="w-3 h-3 ml-1" /></>
            ) : (
              <>Show all ({items.length}) <ChevronDown className="w-3 h-3 ml-1" /></>
            )}
          </Button>
        )}
      </div>

      <AnimatePresence mode="popLayout">
        <div className="space-y-2">
          {displayItems.map((item) => (
            <motion.div
              key={item.id}
              layout
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              className="flex items-center gap-3 p-2.5 rounded-lg bg-secondary/50 hover:bg-secondary transition-colors cursor-pointer group"
              onClick={() => onSelect(item.id)}
            >
              <FileText className="w-4 h-4 text-primary shrink-0" />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-foreground truncate">
                  {item.file_name}
                </p>
                <p className="text-xs text-muted-foreground">
                  {item.summary_length} • {item.language === "hi" ? "हिन्दी" : "English"} • {new Date(item.created_at).toLocaleDateString()}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-destructive"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(item.id);
                }}
              >
                <Trash2 className="w-3.5 h-3.5" />
              </Button>
            </motion.div>
          ))}
        </div>
      </AnimatePresence>
    </motion.div>
  );
};

export default HistoryPanel;
