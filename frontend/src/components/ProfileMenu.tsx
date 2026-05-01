import { useEffect, useState } from "react";
import { History, LogOut, Mail, Trash2, User as UserIcon, FileText } from "lucide-react";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { useAuth } from "@/contexts/AuthContext";
import { supabase } from "@/integrations/supabase/client";
import { toast } from "@/hooks/use-toast";
import { ScrollArea } from "@/components/ui/scroll-area";

interface HistoryItem {
  id: string;
  file_name: string;
  summary_length: string;
  language: string;
  word_count: number | null;
  reading_time: string | null;
  created_at: string;
}

const ProfileMenu = () => {
  const { user, signOut } = useAuth();
  const [historyOpen, setHistoryOpen] = useState(false);
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [loading, setLoading] = useState(false);

  const initials = (user?.email || "?")
    .split("@")[0]
    .slice(0, 2)
    .toUpperCase();

  const fetchHistory = async () => {
    if (!user) return;
    setLoading(true);
    const { data, error } = await supabase
      .from("pdf_summaries")
      .select("id, file_name, summary_length, language, word_count, reading_time, created_at")
      .eq("user_id", user.id)
      .order("created_at", { ascending: false });
    if (error) {
      toast({ title: "Failed to load history", description: error.message, variant: "destructive" });
    } else {
      setHistory(data || []);
    }
    setLoading(false);
  };

  useEffect(() => {
    if (historyOpen) fetchHistory();
  }, [historyOpen]);

  const handleDelete = async (id: string) => {
    const { error } = await supabase.from("pdf_summaries").delete().eq("id", id);
    if (error) {
      toast({ title: "Delete failed", description: error.message, variant: "destructive" });
      return;
    }
    setHistory((prev) => prev.filter((h) => h.id !== id));
    toast({ title: "Deleted", description: "Summary removed from history." });
  };

  return (
    <>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            className="h-9 w-9 rounded-full ring-2 ring-primary/20 hover:ring-primary/50 transition-all overflow-hidden focus:outline-none focus:ring-primary"
            aria-label="Open profile menu"
          >
            <Avatar className="h-9 w-9">
              <AvatarFallback className="bg-primary text-primary-foreground text-xs font-semibold">
                {initials}
              </AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-64">
          <DropdownMenuLabel className="font-normal">
            <div className="flex items-center gap-3">
              <Avatar className="h-10 w-10">
                <AvatarFallback className="bg-primary text-primary-foreground text-sm font-semibold">
                  {initials}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col min-w-0">
                <span className="text-xs text-muted-foreground uppercase tracking-wider font-medium">
                  Signed in
                </span>
                <span className="text-sm font-semibold truncate">{user?.email}</span>
              </div>
            </div>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem disabled className="text-xs text-muted-foreground gap-2">
            <UserIcon className="w-3.5 h-3.5" />
            <span className="truncate">ID: {user?.id?.slice(0, 8)}…</span>
          </DropdownMenuItem>
          <DropdownMenuItem disabled className="text-xs text-muted-foreground gap-2">
            <Mail className="w-3.5 h-3.5" />
            <span className="truncate">{user?.email}</span>
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => setHistoryOpen(true)} className="cursor-pointer gap-2">
            <History className="w-4 h-4" />
            View history
          </DropdownMenuItem>
          <DropdownMenuItem
            onClick={() => signOut()}
            className="cursor-pointer gap-2 text-destructive focus:text-destructive"
          >
            <LogOut className="w-4 h-4" />
            Sign out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <Sheet open={historyOpen} onOpenChange={setHistoryOpen}>
        <SheetContent className="w-full sm:max-w-md flex flex-col">
          <SheetHeader>
            <SheetTitle className="flex items-center gap-2">
              <History className="w-5 h-5 text-primary" />
              Your History
            </SheetTitle>
            <SheetDescription>
              All PDFs you've summarized, most recent first.
            </SheetDescription>
          </SheetHeader>

          <ScrollArea className="flex-1 mt-4 -mx-6 px-6">
            {loading ? (
              <div className="text-sm text-muted-foreground py-8 text-center">Loading…</div>
            ) : history.length === 0 ? (
              <div className="text-sm text-muted-foreground py-12 text-center">
                <FileText className="w-10 h-10 mx-auto mb-3 opacity-40" />
                No summaries yet. Upload a PDF to get started.
              </div>
            ) : (
              <ul className="space-y-2 pb-4">
                {history.map((item) => (
                  <li
                    key={item.id}
                    className="group flex items-start gap-3 p-3 rounded-lg border bg-card hover:bg-accent/30 transition-colors"
                  >
                    <FileText className="w-4 h-4 text-primary shrink-0 mt-0.5" />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{item.file_name}</p>
                      <p className="text-xs text-muted-foreground mt-0.5">
                        {item.summary_length} •{" "}
                        {item.language === "hi" ? "हिन्दी" : "English"}
                        {item.word_count ? ` • ${item.word_count} words` : ""}
                      </p>
                      <p className="text-[10px] text-muted-foreground mt-1">
                        {new Date(item.created_at).toLocaleString()}
                      </p>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-7 w-7 opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive transition"
                      onClick={() => handleDelete(item.id)}
                      aria-label="Delete summary"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </li>
                ))}
              </ul>
            )}
          </ScrollArea>
        </SheetContent>
      </Sheet>
    </>
  );
};

export default ProfileMenu;
