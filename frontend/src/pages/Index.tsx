import beeLogo from "@/assets/bee-logo.png";
import { ChartRenderer } from "@/components/ChartRenderer";
import DropZone from "@/components/DropZone";
import LoadingSteps from "@/components/LoadingSteps";
import SummaryResults from "@/components/SummaryResults";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/contexts/AuthContext";
import { motion } from "framer-motion";
import { Loader2, LogOut, Send } from "lucide-react";
import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

type SummaryLength = "short" | "medium" | "detailed";
type Language = "en" | "hi";
type AppState = "idle" | "loading" | "results";

type ChatMessage = {
  role: "user" | "ai";
  content: string;
  pages?: number[];
  pdfUrl?: string;
};
const Index = () => {
  const { session, signOut, user } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [length, setLength] = useState<SummaryLength>("medium");
  const [language, setLanguage] = useState<Language>("en");
  const [state, setState] = useState<AppState>("idle");
  const [summaryText, setSummaryText] = useState("");
  const [documentId, setDocumentId] = useState<string | null>(null);
  const [filename, setFilename] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string>("");

  // Chat State
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [isChatLoading, setIsChatLoading] = useState(false);

  const handleGenerate = async () => {
    if (!file || !session) return;
    setState("loading");
    setSummaryText("");
    
    const newSessionId = crypto.randomUUID();
    setSessionId(newSessionId);
    
    try {
      // 1. Upload File
      const formData = new FormData();
      formData.append("file", file);
      
      const uploadRes = await fetch(`/api/upload`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${session.access_token}`
        },
        body: formData,
      });
      
      if (!uploadRes.ok) {
        let errorMessage = "Document processing failed";
        try {
            const errorData = await uploadRes.json();
            if (errorData.detail) errorMessage = errorData.detail;
        } catch(e) {}
        throw new Error(errorMessage);
      }
      
      const uploadData = await uploadRes.json();
      const newDocId = uploadData.document_id;
      setDocumentId(newDocId);
      setFilename(uploadData.filename);
      
      // 2. Poll for Status (Adaptive Polling)
      let isCompleted = false;
      let attempts = 0;
      
      while (!isCompleted && attempts < 30) { // Max 2-3 mins 
        attempts++;
        const pollInterval = attempts < 10 ? 2000 : 5000; // Start at 2s, move to 5s
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
        const statusRes = await fetch(`/api/status/${newDocId}`, {
          headers: { "Authorization": `Bearer ${session.access_token}` }
        });
        
        if (statusRes.ok) {
          const statusData = await statusRes.json();
          if (statusData.status === "completed") {
            isCompleted = true;
          } else if (statusData.status === "failed") {
            throw new Error(statusData.error || "Processing failed at backend");
          }
        } else if (statusRes.status === 401) {
          window.location.reload(); // Session expired
          return;
        }
      }
      
      if (!isCompleted) throw new Error("Processing timed out. Please try refreshing.");

      // 3. Query Chat API for Summary
      const languageStr = language === "en" ? "English" : "Hindi";
      const chatRes = await fetch(`/api/chat`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session.access_token}`
        },
        body: JSON.stringify({ 
          user_query: "Summarize this document",
          session_id: newSessionId,
          document_id: newDocId,
          mode: "summary",
          language: languageStr,
          length: length
        })
      });
      
      if (!chatRes.ok) {
        let errorMessage = "Summarization failed";
        try {
            const errorData = await chatRes.json();
            if (errorData.detail) errorMessage = errorData.detail;
        } catch(e) {}
        throw new Error(errorMessage);
      }
      
      const chatData = await chatRes.json();
      setSummaryText(chatData.response);
      setState("results");
    } catch (err: any) {
      console.error(err);
      alert(err.message || "An error occurred");
      setState("idle");
    }
  };

  const handleAskQuestion = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!currentQuestion.trim() || !documentId || !sessionId) return;

    let questionText = currentQuestion.trim();
    if (questionText.length > 0) {
      questionText = questionText.charAt(0).toUpperCase() + questionText.slice(1);
    }
    
    setCurrentQuestion("");
    setIsChatLoading(true);

    // Add user message to UI immediately
    setChatMessages((prev) => [...prev, { role: "user", content: questionText }]);

    try {
      const chatRes = await fetch(`/api/chat`, {
        method: "POST",
        headers: { 
          "Content-Type": "application/json",
          "Authorization": `Bearer ${session?.access_token}`
        },
        body: JSON.stringify({
          user_query: questionText,
          session_id: sessionId,
          document_id: documentId,
          mode: "chat",
          language: language === "en" ? "English" : "Hindi"
        }),
      });

      if (!chatRes.ok) {
        let errorMessage = "Failed to get answer";
        try {
            const errorData = await chatRes.json();
            if (errorData.detail) errorMessage = errorData.detail;
        } catch(e) {}
        throw new Error(errorMessage);
      }

      const chatData = await chatRes.json();
      
      // Add AI response to UI with pages and pdfUrl
      setChatMessages((prev) => [
        ...prev, 
        { 
          role: "ai", 
          content: chatData.response,
          pages: chatData.pages,
          pdfUrl: chatData.pdf_url
        }
      ]);
    } catch (err: any) {
      console.error(err);
      setChatMessages((prev) => [...prev, { role: "ai", content: "Sorry, I encountered an error while answering that question." }]);
    } finally {
      setIsChatLoading(false);
    }
  };

  const handleReset = () => {
    setFile(null);
    setSummaryText("");
    setDocumentId(null);
    setFilename(null);
    setSessionId("");
    setChatMessages([]);
    setState("idle");
  };

  const handleComplete = () => {
    // Optional callback when LoadingSteps finishes its animation loop.
  };

  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-[600px] mx-auto px-4 py-8 sm:py-12">
        {/* Header */}
        <motion.header
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="relative text-center mb-8"
        >
          {/* Profile Menu */}
          <div className="absolute -top-4 right-0 flex items-center gap-2">
            <ProfileMenu />
          </div>

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
              <div id="summary-section">
                <SummaryResults 
                  summaryText={summaryText} 
                  onDownloadPDF={documentId ? async () => {
                    try {
                      const res = await fetch(`/api/download/${documentId}`, {
                        headers: { "Authorization": `Bearer ${session?.access_token}` }
                      });
                      if (res.ok) {
                        const data = await res.json();
                        window.open(data.url, "_blank");
                      }
                    } catch (e) {
                      console.error("Download failed", e);
                    }
                  } : undefined}
                />
              </div>
              
              {/* Chat Interface */}
              <div className="mt-6 flex flex-col gap-4">
                {chatMessages.length > 0 && (
                  <div className="flex flex-col gap-5 p-4 rounded-xl border bg-card/50">
                    {chatMessages.map((msg, idx) => (
                      <div
                        key={idx}
                        className={`flex gap-4 w-full ${
                          msg.role === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        <div
                          className={`max-w-[85%] rounded-2xl px-5 py-3.5 text-sm shadow-sm ${
                            msg.role === "user"
                              ? "bg-primary text-primary-foreground"
                              : "bg-card text-card-foreground border border-border/50"
                          }`}
                        >
                          {msg.role === "ai" ? (
                            <div className="prose prose-sm dark:prose-invert max-w-none prose-p:leading-relaxed prose-p:my-2 prose-ul:my-2 prose-li:my-0.5">
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
                                {msg.content}
                              </ReactMarkdown>
                            </div>
                          ) : (
                            <div className="whitespace-pre-wrap leading-relaxed">{msg.content}</div>
                          )}
                          
                          {/* Sources Section */}
                          {msg.role === "ai" && msg.pages && msg.pages.length > 0 && (
                            <div className="mt-4 pt-3 border-t border-border/50 flex flex-wrap items-center gap-2">
                              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">Sources:</span>
                              <div className="flex flex-wrap gap-1.5">
                                {msg.pages.map((p) => (
                                  <button
                                    key={`source-${p}`}
                                    className="px-2.5 py-0.5 rounded-full bg-secondary text-secondary-foreground text-[10px] font-medium hover:bg-secondary/80 transition-colors border border-border/50"
                                    onClick={() => {
                                      if (msg.pdfUrl) {
                                        window.open(`${msg.pdfUrl}#page=${p}`, "_blank");
                                      }
                                    }}
                                  >
                                    Page {p}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                      </div>
                    ))}
                    {isChatLoading && (
                      <div className="flex gap-4 w-full justify-start">
                        <div className="bg-card text-muted-foreground rounded-2xl px-5 py-4 flex items-center gap-3 shadow-sm border border-border/50">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className="text-sm font-medium">Analyzing document...</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                <form onSubmit={handleAskQuestion} className="flex gap-2 items-center mt-2 relative">
                  <input
                    type="text"
                    value={currentQuestion}
                    onChange={(e) => setCurrentQuestion(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        handleAskQuestion();
                      }
                    }}
                    placeholder="Ask a question about your document..."
                    className="w-full rounded-full border border-input bg-card px-5 py-4 pr-14 text-sm shadow-sm transition-all focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={isChatLoading}
                  />
                  <Button 
                    type="submit" 
                    size="icon"
                    variant="gold" 
                    className="absolute right-2 top-2 bottom-2 my-auto h-10 w-10 p-0 rounded-full flex items-center justify-center"
                    disabled={isChatLoading || !currentQuestion.trim()}
                  >
                    <Send className="h-4 w-4" />
                  </Button>
                </form>
              </div>

              <div className="mt-4 pt-4 border-t flex gap-2">
                <Button
                  variant="gold-outline"
                  className="w-full"
                  onClick={handleReset}
                >
                  Summarize another PDF
                </Button>
              </div>
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
          Free • No signup needed • Powered by AI
        </motion.footer>
      </div>
    </div>
  );
};

export default Index;
