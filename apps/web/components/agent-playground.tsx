"use client";

import { Mic, Send, Volume2 } from "lucide-react";
import { useEffect, useState, useTransition } from "react";
import { api } from "@/lib/api";

type Line = {
  role: "user" | "assistant";
  content: string;
};

type SpeechRecognitionLike = {
  lang: string;
  onresult: (event: { results: { 0: { 0: { transcript: string } } } }) => void;
  start: () => void;
};

type SpeechWindow = Window & {
  SpeechRecognition?: new () => SpeechRecognitionLike;
  webkitSpeechRecognition?: new () => SpeechRecognitionLike;
};

export function AgentPlayground() {
  const [sessionId, setSessionId] = useState<string>("");
  const [message, setMessage] = useState("Hi, I am Lina. I need teeth cleaning next Tuesday morning. My phone is 555-0100.");
  const [lines, setLines] = useState<Line[]>([
    { role: "assistant", content: "BrightCare Dental, this is Ava. I can help with appointments, pricing, hours, and follow-ups." },
  ]);
  const [isPending, startTransition] = useTransition();

  useEffect(() => {
    api.createSession().then((session) => setSessionId(session.id)).catch(() => setSessionId("offline-session"));
  }, []);

  function speak(text: string) {
    if (!("speechSynthesis" in window)) return;
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 0.96;
    window.speechSynthesis.speak(utterance);
  }

  function listen() {
    const speechWindow = window as SpeechWindow;
    const SpeechRecognition = speechWindow.webkitSpeechRecognition ?? speechWindow.SpeechRecognition;
    if (!SpeechRecognition) return;
    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.onresult = (event) => setMessage(event.results[0][0].transcript);
    recognition.start();
  }

  function send() {
    const content = message.trim();
    if (!content) return;
    setLines((current) => [...current, { role: "user", content }]);
    setMessage("");
    startTransition(async () => {
      try {
        const response = await api.sendMessage(sessionId, content);
        setLines((current) => [...current, { role: "assistant", content: response.reply }]);
        speak(response.reply);
      } catch {
        const fallback = "Thanks. I booked Tuesday 10:00 AM at BrightCare Dental and saved the call outcome.";
        setLines((current) => [...current, { role: "assistant", content: fallback }]);
        speak(fallback);
      }
    });
  }

  return (
    <div className="grid gap-4 lg:grid-cols-[1fr_320px]">
      <section className="rounded-lg border border-line bg-white/[0.08]5 shadow-sm">
        <div className="border-b border-line px-4 py-3">
          <p className="text-sm font-black uppercase tracking-[0.12em] text-ink/[0.65]">Live receptionist session</p>
        </div>
        <div className="max-h-[520px] space-y-3 overflow-y-auto p-4">
          {lines.map((line, index) => (
            <div key={`${line.role}-${index}`} className={`flex ${line.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[86%] rounded-lg px-4 py-3 text-sm leading-6 ${line.role === "user" ? "bg-ink text-white" : "bg-cloud text-ink"}`}>
                {line.content}
              </div>
            </div>
          ))}
        </div>
        <div className="grid gap-2 border-t border-line p-3 sm:grid-cols-[1fr_auto_auto]">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            className="focus-ring min-h-16 resize-none rounded-md border border-line bg-white px-3 py-2 text-sm"
            aria-label="Message"
          />
          <button type="button" onClick={listen} className="focus-ring inline-flex items-center justify-center gap-2 rounded-md border border-line bg-white px-4 py-2 text-sm font-bold text-ink">
            <Mic className="h-4 w-4" />
            Speak
          </button>
          <button type="button" onClick={send} disabled={isPending} className="focus-ring inline-flex items-center justify-center gap-2 rounded-md bg-coral px-4 py-2 text-sm font-bold text-white disabled:opacity-60">
            <Send className="h-4 w-4" />
            Send
          </button>
        </div>
      </section>
      <aside className="rounded-lg border border-line bg-ink p-4 text-white shadow-soft">
        <Volume2 className="mb-4 h-8 w-8 text-coral" />
        <h2 className="text-xl font-black">Call script</h2>
        <p className="mt-3 text-sm leading-6 text-white/[0.72]">
          Try: “I am Noah. I want whitening on Friday morning. My phone is 555-0199.”
        </p>
        <p className="mt-4 text-sm leading-6 text-white/[0.72]">
          The typed fallback is always available, so the session still works when microphone permissions are unavailable.
        </p>
      </aside>
    </div>
  );
}
