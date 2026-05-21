"use client";

import { useState } from "react";
import {
  BarVisualizer,
  LiveKitRoom,
  RoomAudioRenderer,
  useVoiceAssistant,
} from "@livekit/components-react";
import "@livekit/components-styles";

type Connection = {
  token: string;
  url: string;
  room: string;
  identity: string;
};

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000";

function AgentView({ onEnd }: { onEnd: () => void }) {
  const { state, audioTrack } = useVoiceAssistant();

  return (
    <div className="flex flex-col items-center gap-6">
      <p className="text-sm uppercase tracking-wide text-gray-500">
        Status: {state}
      </p>
      <div className="h-32 w-full max-w-md">
        <BarVisualizer state={state} barCount={7} trackRef={audioTrack} />
      </div>
      <RoomAudioRenderer />
      <button
        onClick={onEnd}
        className="rounded-md bg-red-600 px-4 py-2 text-white hover:bg-red-700"
      >
        End call
      </button>
    </div>
  );
}

export default function VoicePage() {
  const [conn, setConn] = useState<Connection | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const startCall = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/livekit/token`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({}),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Token request failed (${res.status}): ${body}`);
      }
      const data: Connection = await res.json();
      setConn(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <main className="mx-auto max-w-2xl px-6 py-12">
      <h1 className="text-2xl font-semibold">BrightCare Dental</h1>
      <p className="mt-1 text-gray-600">
        Call the AI receptionist from your browser.
      </p>

      <div className="mt-8 rounded-lg border border-gray-200 bg-white p-8">
        {!conn ? (
          <div className="flex flex-col items-center gap-4">
            <button
              onClick={startCall}
              disabled={loading}
              className="rounded-md bg-blue-600 px-6 py-3 text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? "Connecting..." : "Start call"}
            </button>
            <p className="text-xs text-gray-500">
              Your browser will ask for microphone permission.
            </p>
            {error && (
              <p className="text-sm text-red-600">{error}</p>
            )}
          </div>
        ) : (
          <LiveKitRoom
            token={conn.token}
            serverUrl={conn.url}
            connect
            audio
            video={false}
            onDisconnected={() => setConn(null)}
          >
            <AgentView onEnd={() => setConn(null)} />
          </LiveKitRoom>
        )}
      </div>
    </main>
  );
}
