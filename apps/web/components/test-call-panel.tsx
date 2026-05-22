"use client";

import { useEffect, useState } from "react";
import { Mic, MicOff, PhoneCall, PhoneOff } from "lucide-react";
import {
  BarVisualizer,
  LiveKitRoom,
  RoomAudioRenderer,
  useLocalParticipant,
  useVoiceAssistant,
} from "@livekit/components-react";
import "@livekit/components-styles";
import { api } from "@/lib/api";
import type { LiveKitTokenResponse } from "@/lib/types";

type Props = {
  workspaceId: number;
  agentId: number;
  agentName: string;
};

export function TestCallPanel({ workspaceId, agentId, agentName }: Props) {
  const [conn, setConn] = useState<LiveKitTokenResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function startCall() {
    setLoading(true);
    setError(null);
    try {
      const res = await api.livekitToken({
        workspace_id: workspaceId,
        agent_id: agentId,
      });
      setConn(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  function endCall() {
    setConn(null);
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-zinc-800 bg-zinc-900/30">
      <div className="flex items-start justify-between gap-4 p-5">
        <div>
          <div className="mb-1 flex items-center gap-1.5">
            <span className="text-[11px] font-medium uppercase tracking-wider text-accent-400">
              Test call
            </span>
            {conn && (
              <span className="h-1.5 w-1.5 rounded-full bg-accent-400 animate-pulse-glow" />
            )}
          </div>
          <h3 className="text-sm text-zinc-100">
            Talk to <span className="font-medium">{agentName}</span> in the browser
          </h3>
          <p className="mt-1 max-w-md text-xs text-zinc-500">
            Verifies persona, voice, and KB grounding end to end. The transcript
            is saved when you hang up.
          </p>
        </div>
        {!conn ? (
          <button
            type="button"
            onClick={startCall}
            disabled={loading}
            className="flex shrink-0 items-center gap-1.5 rounded-lg bg-accent-400 px-3.5 py-2 text-sm font-medium text-zinc-950 transition hover:bg-accent-300 disabled:opacity-60"
          >
            <PhoneCall className="h-4 w-4" />
            {loading ? "Connecting..." : "Start call"}
          </button>
        ) : (
          <button
            type="button"
            onClick={endCall}
            className="flex shrink-0 items-center gap-1.5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3.5 py-2 text-sm font-medium text-rose-300 transition hover:bg-rose-500/20"
          >
            <PhoneOff className="h-4 w-4" />
            End call
          </button>
        )}
      </div>

      {error && (
        <p className="mx-5 mb-5 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-xs text-rose-300">
          {error}
        </p>
      )}

      {conn && (
        <LiveKitRoom
          key={conn.room}
          token={conn.token}
          serverUrl={conn.url}
          connect
          audio={{
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true,
          }}
          video={false}
          onDisconnected={endCall}
        >
          <CallStage room={conn.room} />
        </LiveKitRoom>
      )}
    </div>
  );
}

function CallStage({ room }: { room: string }) {
  const { state, audioTrack } = useVoiceAssistant();
  const { localParticipant, microphoneTrack, isMicrophoneEnabled } =
    useLocalParticipant();
  const [micError, setMicError] = useState<string | null>(null);

  useEffect(() => {
    if (!localParticipant) return;
    let cancelled = false;
    (async () => {
      try {
        await localParticipant.setMicrophoneEnabled(true);
      } catch (err) {
        if (!cancelled) {
          setMicError(err instanceof Error ? err.message : String(err));
        }
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [localParticipant]);

  const micOn = isMicrophoneEnabled && microphoneTrack;

  return (
    <div className="border-t border-zinc-800/80 bg-zinc-950/40 px-5 py-5">
      <div className="mb-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px]">
        <span className="flex items-center gap-1.5 text-zinc-400">
          <span className="font-mono text-zinc-600">agent</span>
          <span className="rounded-md bg-zinc-900 px-1.5 py-0.5 font-mono text-zinc-200">
            {state}
          </span>
        </span>
        <span className="flex items-center gap-1.5">
          {micOn ? (
            <>
              <Mic className="h-3.5 w-3.5 text-emerald-400" />
              <span className="text-emerald-300">mic on</span>
            </>
          ) : (
            <>
              <MicOff className="h-3.5 w-3.5 text-rose-400" />
              <span className="text-rose-300">mic off</span>
            </>
          )}
        </span>
        <span className="ml-auto font-mono text-zinc-600">{room}</span>
      </div>
      <div className="h-24 rounded-xl border border-zinc-800 bg-zinc-950 p-3">
        <BarVisualizer state={state} barCount={11} trackRef={audioTrack} />
      </div>
      <RoomAudioRenderer />
      {micError ? (
        <p className="mt-3 rounded-lg border border-rose-500/30 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-300">
          Mic error: {micError}. Check the site permissions in your browser URL bar.
        </p>
      ) : (
        <p className="mt-3 text-[11px] text-zinc-500">
          Allow microphone access if prompted. Speak normally — the agent uses
          Deepgram for STT, Groq for reasoning, and Cartesia for TTS.
        </p>
      )}
    </div>
  );
}
