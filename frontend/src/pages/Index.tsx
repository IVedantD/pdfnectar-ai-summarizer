import beeLogo from "@/assets/bee-logo.png";
import DropZone from "@/components/DropZone";
import LoadingSteps from "@/components/LoadingSteps";
import SummaryResults from "@/components/SummaryResults";
import { Button } from "@/components/ui/button";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react"; // Import for loading spinner
import { useState } from "react";

type SummaryLength = "short" | "medium" | "detailed";
type Language = "en" | "hi";
type AppState = "idle" | "loading" | "results";

type ChatMessage = {
  role: "user" | "ai";
  content: string;
  pages?: number[];
  pdfUrl?: string;
};

const formatMessageContent = (content: string) => {
  return content;
};

const Index = () => {
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
    if (!file) return;
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
      setDocumentId(newDocId); // Save to state for later reuse
      setFilename(uploadData.filename); // Save the safe filename on backend for downloading
      
      // 2. Query Chat API for Summary
      const languageStr = language === "en" ? "English" : "Hindi";
      const lengthPrompt = length === "short" ? "around 100 words" : length === "medium" ? "around 300 words" : "around 800 words";
      const query = `You are an intelligent document analysis assistant.

IMPORTANT CONTEXT RULES
• Answer ONLY using the provided document context.
• Do NOT generate information that does not exist in the document.
• If the information is missing, respond with:
"The document does not provide this information."

Before generating the final response, carefully analyze the entire document context and identify the most relevant information.

Your task is to analyze the provided PDF content and generate a structured response in ${languageStr}.
The summary should be ${lengthPrompt} long.

Use clear Markdown formatting and follow the structure below.

--------------------------------------------------

1️⃣ 📋 DOCUMENT OVERVIEW
Provide a short explanation describing the overall purpose of the document.

--------------------------------------------------

2️⃣ 🔑 KEY INSIGHTS
Extract the most important ideas from the document.

• Use bullet points
• Highlight key technologies, systems, or entities in **bold**

${length === "short" ? "" : `--------------------------------------------------

3️⃣ 🧩 IMPORTANT ENTITIES
Identify key elements mentioned in the document such as Technologies, Modules, Tables, Workflows, or Roles. List them clearly using bullet points.

--------------------------------------------------

4️⃣ 📐 DIAGRAM / PROCESS EXPLANATION
If the document contains diagrams, workflows, or system architecture descriptions, explain them briefly. If none exist, skip this section.

--------------------------------------------------

5️⃣ 📊 DATA INSIGHTS (ONLY IF NUMERIC DATA EXISTS)
If the document contains numbers, percentages, or statistics, extract the relevant values and present them in a structured table. If no meaningful numeric data exists, skip this section.
`}
--------------------------------------------------

6️⃣ 💡 KEY TAKEAWAYS

Provide 2–3 important conclusions derived from the document.

--------------------------------------------------

7️⃣ 📈 SUMMARY STATISTICS

Provide:

• Estimated word count of the response  
• Estimated reading time

--------------------------------------------------

8️⃣ 📚 SOURCES

Mention the page numbers used.

Example:
Source: Page 1, Page 3

--------------------------------------------------

📊 OPTIONAL CHART DATA OUTPUT

If numeric data suitable for visualization exists, return raw JSON called chart_data at the end of the response.

Return RAW JSON only.
Do NOT wrap JSON inside markdown code blocks.

Example:

chart_data:
{
 "labels": ["Category A","Category B"],
 "values": [45,30],
 "chart_type": "bar"
}

If no numeric data exists, DO NOT include chart_data.

--------------------------------------------------

FINAL RULES

• Do NOT hallucinate information.
• Use only the document context.
• Skip sections if the document does not contain relevant information.
• Prefer bullet points and short paragraphs.
• Highlight key technologies or entities in **bold**.`;

      const chatRes = await fetch(`/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ 
          query, 
          user_query: "Summarize this document",
          session_id: newSessionId,
          document_id: newDocId 
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
      const formattedQuery = `You are an intelligent document question-answering assistant.

IMPORTANT CONTEXT RULES
• Answer ONLY using the provided document context and conversation history.
• Do NOT generate information that does not exist in the document.
• If the document does not contain the answer, respond with:
"The document does not provide this information."

CONVERSATION MEMORY

You may receive previous conversation messages along with the current user question.

• Use conversation history to interpret follow-up references such as:
  "it", "this", "that system", "the project", etc.
• If the user asks a follow-up question, interpret it using the previous discussion.

FOLLOW-UP QUESTION HANDLING

• If the user question is ambiguous, attempt to resolve it using conversation history.
• If the reference is still unclear, ask the user for clarification before answering.

OUT-OF-SCOPE QUESTION HANDLING

Before answering the question:

• Determine whether the user's question is related to the uploaded document.
• If the question is unrelated to the document content, respond with:

"This question is outside the scope of the uploaded document. Please ask a question related to the document."

• Do not attempt to answer questions that cannot be supported by the document context.

QUESTION REFORMULATION

Before answering the user's question:

• If the question is short, vague, or relies on conversation context,
  rewrite it internally into a clear standalone question.

• Use the conversation history and document context to clarify the meaning.

Examples:

User question: "What about the database?"
Rewritten internally: "What database is used in the project described in the document?"

User question: "How does it work?"
Rewritten internally: "How does the system described in the document work?"

• Use the rewritten question for reasoning and document analysis,
  but DO NOT display the rewritten question to the user.

Continue answering using the normal analysis process.

RELEVANCE FILTERING

Before using retrieved document context:

• Evaluate whether each piece of retrieved context is relevant to the rewritten question.
• Prioritize the most relevant sections of the document.
• Ignore context that is weakly related or unrelated to the question.
• If multiple relevant sections exist, combine them to form a more complete answer.

Only use information that clearly supports the answer.

CONTEXT PRIORITIZATION

When multiple pieces of retrieved document context are available:

• Rank the context sections based on their relevance to the question.
• Prioritize sections that directly answer the question.
• Use secondary sections only to support or expand the explanation.
• Avoid relying on less relevant context when stronger evidence exists.

Always base the final answer on the most relevant document sections first.

CONTRADICTION CHECK

Before constructing the final answer:

• Check whether different parts of the retrieved document context contain conflicting or inconsistent information.
• If contradictions exist, acknowledge them clearly instead of choosing one interpretation without explanation.
• Present both viewpoints briefly and explain that the document contains differing information.
• Prefer the most clearly supported or most recent information if the document indicates it.

Do not merge conflicting statements into a single claim.

INFORMATION PRIORITY RULE

When multiple pieces of document information exist about the same topic:

• Prefer the most authoritative or clearly supported information.
• If the document indicates chronological updates, prefer the most recent or final version.
• Give priority to sections that explicitly define or summarize concepts.
• Use supporting sections only to expand the explanation.

Do not prioritize weaker or indirect statements when stronger evidence exists.

DOCUMENT ANALYSIS STRATEGY

Step 1 — Extract Relevant Facts
• Carefully review the provided document context.
• Identify the sections most relevant to the question.
• Extract key facts, entities, and statements from the document.

Step 2 — Verify Context Coverage
• Check whether the retrieved document context contains enough information to answer the question.
• If the context is insufficient, respond with:
  "The document does not provide enough information to answer this question."

Step 3 — Build the Answer
• Combine extracted facts into a clear explanation.
• Use multiple sections of the document if necessary.
• Ignore unrelated or redundant information.

USER INTENT DETECTION

Before answering the question:

• Determine the user's intent based on the wording of the question.

Possible intents include:
• Explanation → provide a clear explanation.
• Summary → provide a concise summary.
• List → provide bullet points.
• Comparison → clearly compare items.
• Definition → provide a short definition.

Adapt the depth and structure of the response accordingly while still following the required output format.

Always prioritize answering the user's intent clearly and concisely.

ANSWER STYLE ADAPTATION

Adjust the structure of the answer depending on the question type:

• If the question asks for a definition → provide a short explanation.
• If the question asks for a list → provide bullet points.
• If the question asks for a process or workflow → explain step-by-step.
• If the question asks for comparison → clearly compare items.

RESPONSE LENGTH CONTROL

Before generating the answer:

• Adjust the length of the response based on the user's intent and question complexity.

Guidelines:
• Definition questions → short explanation (1–2 sentences).
• List questions → concise bullet points.
• Explanation questions → short paragraph + key points.
• Process or workflow questions → clear step-by-step explanation.
• Comparison questions → structured comparison with bullet points.

Avoid overly long explanations when a concise answer is sufficient.
Avoid overly short answers when additional clarification improves understanding.

ANSWER VERIFICATION

Before finalizing the response:

• Review the constructed answer and compare it with the extracted document facts.
• Ensure that every key claim in the answer is supported by the document context.
• Confirm that the Evidence quotes directly support the explanation.
• If any claim cannot be supported by the document, remove or revise it.

Only return the final answer once all statements are verified against the document context.

EXPLANATION CLARITY CHECK

Before finalizing the response:

• Review the explanation for clarity and readability.
• Simplify complex or overly technical wording when possible.
• Ensure the answer is understandable to a general reader while preserving accuracy.
• Prefer clear, direct language instead of unnecessary technical jargon.

The goal is to make the explanation both accurate and easy to understand.

TONE CONSISTENCY CHECK

Before finalizing the response:

• Ensure the tone of the answer is clear, professional, and consistent.
• Avoid informal language, unnecessary filler, or conversational phrases.
• Maintain a neutral, informative style suitable for technical documentation.
• Keep sentences concise and structured.

The goal is to provide responses that feel professional, precise, and consistent across all answers.

REDUNDANCY REMOVAL CHECK

Before finalizing the response:

• Review the answer to ensure information is not repeated across sections.
• Avoid restating the same idea in multiple sentences unless necessary for clarity.
• Ensure Key Points summarize the answer instead of duplicating it word-for-word.
• Keep the response concise while preserving all important information.

The goal is to maintain clarity without unnecessary repetition.

ANSWER COMPLETENESS CHECK

Before finalizing the response:

• Ensure the answer fully addresses the user's question.
• Confirm that all relevant facts from the document context have been considered.
• If additional relevant information exists in the retrieved context, include it in the explanation.
• Avoid returning partial answers when more supporting details are available.

Only return the response once the answer is complete and supported by document evidence.

SOURCE TRACEABILITY

When constructing the answer:

• Ensure each key claim or statement can be traced back to a specific part of the document.
• When possible, associate key points with the page where the information appears.
• Do not include claims that cannot be traced to document evidence.
• If different claims come from different pages, clearly reflect that in the inline citations.

The goal is that every important statement in the answer is grounded in identifiable document evidence.

TASK

The user will ask a question about the uploaded PDF.

Generate a clear answer using ONLY the document context.

RESPONSE GUIDELINES

• Start with a direct answer.
• Use bullet points when listing information.
• Highlight key technologies, systems, or entities in **bold**.
• Avoid repeating the same information.
• Keep explanations concise and clear.

CITATION RULES

• Do NOT insert any page citations inside the answer text.
• Do NOT write (Source: Page X), [Source: Page X], or any similar inline reference.
• Do NOT add a Sources, References, Evidence, or Confidence section.
• The system will automatically add page sources — you must NOT add them yourself.
• Write clean, natural text like ChatGPT or Perplexity would.

OUTPUT FORMAT

Provide a clear, well-structured answer without any page references in the text.
Use Key Points as bullet points when relevant.

Example:
The system uses **React** for the frontend and **Node.js** for the backend.

Key Points:
• Data is stored in **MongoDB**.
• The application follows a client-server architecture.

FINAL RULES

• Do not hallucinate facts or numbers.
• Use only the document context.
• Skip information that is not supported by the document.
• Keep the response structured and readable.
• Never insert page numbers or citations in the answer text.

---
User Question:
${questionText}`;

      const chatRes = await fetch(`/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          query: formattedQuery,
          user_query: questionText,
          session_id: sessionId,
          document_id: documentId,
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
                  onDownloadPDF={filename ? () => {
                    window.open(`/api/download/${filename}`, "_blank");
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
                        className={`flex gap-3 w-full ${
                          msg.role === "user" ? "justify-end" : "justify-start"
                        }`}
                      >
                        {msg.role === "ai" && (
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center text-lg shadow-sm border border-border/50">
                            🤖
                          </div>
                        )}
                        <div
                          className={`max-w-[80%] rounded-2xl px-4 py-3 text-sm shadow-sm ${
                            msg.role === "user"
                              ? "bg-yellow-500 text-white rounded-tr-sm"
                              : "bg-muted text-foreground rounded-tl-sm whitespace-pre-wrap leading-relaxed"
                          }`}
                        >
                          {msg.role === "ai" ? formatMessageContent(msg.content) : msg.content}
                          
                          {/* Sources Section */}
                          {msg.role === "ai" && msg.pages && msg.pages.length > 0 && (
                            <div className="mt-3 pt-3 border-t border-border/50">
                              <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider mb-2">Sources:</p>
                              <div className="flex flex-wrap gap-2">
                                {msg.pages.map((p) => (
                                  <span
                                    key={`source-${p}`}
                                    className="source-chip"
                                    onClick={() => {
                                      if (msg.pdfUrl) {
                                        window.open(`${msg.pdfUrl}#page=${p}`, "_blank");
                                      }
                                    }}
                                  >
                                    p{p}
                                  </span>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                        {msg.role === "user" && (
                          <div className="flex-shrink-0 w-8 h-8 rounded-full bg-yellow-100 dark:bg-yellow-900 border border-yellow-200 dark:border-yellow-800 flex items-center justify-center text-lg shadow-sm">
                            👤
                          </div>
                        )}
                      </div>
                    ))}
                    {isChatLoading && (
                      <div className="flex gap-3 w-full justify-start">
                        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-muted flex items-center justify-center text-lg shadow-sm border border-border/50">
                          🤖
                        </div>
                        <div className="bg-muted text-muted-foreground rounded-2xl rounded-tl-sm px-4 py-3 flex items-center gap-2 shadow-sm">
                          <Loader2 className="w-4 h-4 animate-spin" />
                          <span className="text-sm">Thinking...</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}
                
                <form onSubmit={handleAskQuestion} className="flex gap-2 items-center">
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
                    placeholder="Ask a question about your PDF..."
                    className="flex-1 rounded-full border border-input bg-background px-4 py-3 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={isChatLoading}
                  />
                  <Button 
                    type="submit" 
                    variant="gold" 
                    className="rounded-full px-6 h-11"
                    disabled={isChatLoading || !currentQuestion.trim()}
                  >
                    Ask
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
