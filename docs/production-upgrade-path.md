# Production Upgrade Path

## Realtime Media

Use LiveKit when browser demo transport needs to become real-time production media with rooms, agent workers, and scalable audio routing.

## Telephony

Use SIP trunking for real inbound and outbound calls. Keep the demo's campaign and agent logic, then replace simulated dialing with SIP call initiation and call status events.

## Answer Machine Detection

Add AMD before routing audio to the AI agent in outbound flows. If voicemail is detected, skip LLM/STT/TTS and play the configured voicemail drop.

## Voicemail Drop

Store campaign voicemail audio in object storage, then play it when AMD returns voicemail. Log the result as `voicemail_simulated` or `voicemail_delivered` depending on environment.

## Deployment

Use Docker Compose on a VPS for the first production deployment. Split services later only when traffic or reliability requirements demand it.

## Cost Notes

The local platform cost is `$0`. Production costs come from SIP minutes, model calls, STT/TTS, storage, VPS, and monitoring. The cheapest reliable production design routes only live answers to the full AI pipeline.
