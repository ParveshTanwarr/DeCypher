import express, { Request, Response } from "express";
import path from "path";
import { createServer as createViteServer } from "vite";
import { GoogleGenAI } from "@google/genai";
import dotenv from "dotenv";

dotenv.config();

const app = express();
const PORT = 3000;

app.use(express.json({ limit: "10mb" }));

// Lazy initialization of GoogleGenAI client with required User-Agent telemetry
let aiClient: GoogleGenAI | null = null;

function getAIClient(): GoogleGenAI {
  if (!aiClient) {
    const apiKey = process.env.GEMINI_API_KEY;
    if (!apiKey) {
      throw new Error("GEMINI_API_KEY environment variable is required.");
    }
    aiClient = new GoogleGenAI({
      apiKey,
      httpOptions: {
        headers: {
          "User-Agent": "aistudio-build",
        },
      },
    });
  }
  return aiClient;
}

// Allowed models mapped to requested capabilities
const VALID_MODELS = [
  "gemini-3.7-flash",
  "gemini-3.5-flash",
  "gemini-3.1-pro-preview",
  "gemini-3.1-flash-lite",
];

// Fallback cascade when a model is experiencing high demand (503) or rate limits (429)
const FALLBACK_CASCADES: Record<string, string[]> = {
  "gemini-3.7-flash": ["gemini-3.1-flash-lite", "gemini-3.5-flash", "gemini-3.1-pro-preview"],
  "gemini-3.5-flash": ["gemini-3.7-flash", "gemini-3.1-flash-lite", "gemini-3.1-pro-preview"],
  "gemini-3.1-pro-preview": ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-flash-lite"],
  "gemini-3.1-flash-lite": ["gemini-3.7-flash", "gemini-3.5-flash", "gemini-3.1-pro-preview"],
};

async function sleep(ms: number) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

// Generate content with automatic retry and model fallback cascade for 503/429/high-demand spikes
async function generateContentWithResilience(
  ai: GoogleGenAI,
  preferredModel: string,
  formattedContents: any[],
  fullSystemInstruction: string
): Promise<{ text: string; modelUsed: string; fallbackOccurred: boolean }> {
  const modelsToTry = [
    preferredModel,
    ...(FALLBACK_CASCADES[preferredModel] || ["gemini-3.7-flash", "gemini-3.1-flash-lite"]),
  ].filter((v, i, a) => a.indexOf(v) === i); // deduplicate

  let lastError: any = null;

  for (let mIndex = 0; mIndex < modelsToTry.length; mIndex++) {
    const currentModel = modelsToTry[mIndex];
    const maxRetries = 2;

    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await ai.models.generateContent({
          model: currentModel,
          contents: formattedContents,
          config: {
            systemInstruction: fullSystemInstruction,
            temperature: 0.7,
          },
        });

        const replyText = response.text || "No response generated.";
        return {
          text: replyText,
          modelUsed: currentModel,
          fallbackOccurred: currentModel !== preferredModel,
        };
      } catch (err: any) {
        lastError = err;
        const errStr = String(err?.message || err || "");
        const isHighDemand =
          errStr.includes("503") ||
          errStr.includes("high demand") ||
          errStr.includes("UNAVAILABLE") ||
          errStr.includes("ResourceExhausted") ||
          errStr.includes("429") ||
          errStr.includes("quota");

        if (isHighDemand) {
          console.warn(
            `Model ${currentModel} attempt ${attempt + 1}/${maxRetries + 1} failed with transient error: ${errStr}`
          );
          if (attempt < maxRetries) {
            // Exponential backoff
            await sleep((attempt + 1) * 700);
            continue;
          }
          // If max retries on this model exceeded, break inner loop to try next fallback model
          break;
        } else {
          // If it's another non-demand error, don't repeatedly retry the same error; attempt next fallback model
          break;
        }
      }
    }
  }

  throw lastError || new Error("All candidate AI models were unavailable due to high demand.");
}

const DEFAULT_SYSTEM_INSTRUCTION = `You are "DECyPHER Intelligence Copilot", an elite AI assistant and user-friendly guide embedded within DECyPHER—a cyber threat intelligence, relationship analysis, and threat actor de-anonymization platform.

DECyPHER Knowledge Base:
- Platform Overview: DECyPHER correlates threat actors, darknet marketplace handles, cryptocurrency wallets (Monero XMR, Ethereum ETH, Bitcoin BTC), and behavioral signals into an interactive graph.
- Key Threat Clusters in Database:
  1. Cluster A00001 (Critical Risk, 92% confidence): Initial Access Broker / Ransomware Affiliate. Controls handles "nyxinhex99" (darknet forum) and "vexatrace" (Telegram). Uses primary Monero wallet 4b5U...aoX and Ethereum deposit 0x7e...870. Rebranded after 78-day dormancy.
  2. Cluster A00042 (High Risk, 84% confidence): Exploit Broker / 0-day syndicate. Controls handle "circuitmoth". Financial overlap with A00001 via shared Ethereum contract 0x7e...870.
  3. Cluster A00118 (Medium Risk, 71% confidence): Low-Volume Tor directory vendor. Controls handle "quietledger", static Bitcoin reserve bc1q...9pz. High OPSEC hygiene.
- Key Methodologies: Stylometric NLP analysis (character slips, syntax, markdown habits), temporal activity windows (UTC), cryptographic wallet reuse analysis, PGP signature validation, and dormancy-rebrand lifecycles.
- Platform Navigation:
  * "/" - Threat Intelligence Dashboard & Executive Overview
  * "/graph" - Interactive Relationship Graph with force-directed simulation, category filters, confidence threshold slider, and real-time telemetry.
  * "/actors/:actorId" - Detailed Actor Dossier with mini-graph, evidence signals, timeline, and stylometrics.
  * "/reports/:actorId" - Formal Executive Intelligence & Sanctions Compliance Report.

Guidelines:
- Maintain a helpful, analytical, and user-friendly tone.
- Format responses cleanly with Markdown (bullet points, bold key terms, tables, and code formatting for addresses/hashes).
- Explain complex OSINT and cyber intelligence concepts simply if asked, and guide users on how to use DECyPHER's graph tools effectively.`;

// API Routes
app.get("/api/health", (_req: Request, res: Response) => {
  res.json({
    status: "ok",
    hasApiKey: Boolean(process.env.GEMINI_API_KEY),
    timestamp: new Date().toISOString(),
  });
});

// Chat endpoint
app.post("/api/chat", async (req: Request, res: Response): Promise<void> => {
  try {
    const {
      messages,
      model = "gemini-3.5-flash",
      systemInstruction,
      context,
    } = req.body;

    if (!messages || !Array.isArray(messages) || messages.length === 0) {
      res.status(400).json({ error: "Invalid or empty messages array." });
      return;
    }

    // Validate selected model or fallback to gemini-3.5-flash
    const selectedModel = VALID_MODELS.includes(model) ? model : "gemini-3.5-flash";

    // Build context-enriched system instruction
    let fullSystemInstruction = systemInstruction || DEFAULT_SYSTEM_INSTRUCTION;
    if (context) {
      fullSystemInstruction += `\n\nCURRENT USER CONTEXT:\n- Active Page: ${context.currentPage || "Unknown"}`;
      if (context.currentActorId) {
        fullSystemInstruction += `\n- Actively Viewed Actor: ${context.currentActorId}`;
      }
      if (context.currentActorData) {
        fullSystemInstruction += `\n- Actor Profile Details: ${JSON.stringify(context.currentActorData)}`;
      }
    }

    // Transform chat messages into @google/genai format
    const formattedContents = messages.map((m: { role: string; content: string }) => ({
      role: m.role === "user" ? "user" : "model",
      parts: [{ text: m.content }],
    }));

    const ai = getAIClient();

    const { text, modelUsed, fallbackOccurred } = await generateContentWithResilience(
      ai,
      selectedModel,
      formattedContents,
      fullSystemInstruction
    );

    res.json({
      role: "model",
      content: text,
      modelUsed,
      fallbackOccurred,
      timestamp: new Date().toISOString(),
    });
  } catch (error: any) {
    console.error("Gemini Chat API Error:", error);
    
    // Provide a helpful response if API key is missing or invalid
    if (!process.env.GEMINI_API_KEY) {
      res.status(503).json({
        error: "GEMINI_API_KEY is not configured.",
        message: "Please configure your GEMINI_API_KEY in the Settings > Secrets panel.",
      });
      return;
    }

    const errMessage = error?.message || "Failed to generate AI response.";
    const isDemandError = errMessage.includes("503") || errMessage.includes("high demand") || errMessage.includes("UNAVAILABLE");

    res.status(isDemandError ? 503 : 500).json({
      error: errMessage,
      message: isDemandError
        ? "The AI intelligence models are currently experiencing high demand. Automatic retry is available."
        : "Failed to generate AI response.",
      details: error.toString(),
    });
  }
});

// Vite middleware & Static serving
async function startServer() {
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (_req: Request, res: Response) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`DECyPHER Intelligence Server running on http://0.0.0.0:${PORT}`);
  });
}

startServer();
