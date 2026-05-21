#!/usr/bin/env bash
set -u

BASE="${BASE:-http://127.0.0.1:8000}"
TS="$(date +%s)"
PASS=0
FAIL=0
TOKEN=""

json_get() {
  python3 - "$1" "$2" <<'PY'
import json
import sys

path, key = sys.argv[1], sys.argv[2]
with open(path) as handle:
    data = json.load(handle)
print(data.get(key, ""))
PY
}

run_json() {
  local name="$1"
  local method="$2"
  local path="$3"
  local body="$4"
  local auth="$5"
  local expect="$6"
  local outfile="/tmp/voice_api_${TS}_${name//[^A-Za-z0-9_]/_}.json"
  local code

  if [[ -n "$body" && "$auth" == "yes" ]]; then
    code="$(curl -s -o "$outfile" -w '%{http_code}' -X "$method" "${BASE}${path}" -H 'Content-Type: application/json' -H "Authorization: Bearer ${TOKEN}" -d "$body")"
  elif [[ -n "$body" ]]; then
    code="$(curl -s -o "$outfile" -w '%{http_code}' -X "$method" "${BASE}${path}" -H 'Content-Type: application/json' -d "$body")"
  elif [[ "$auth" == "yes" ]]; then
    code="$(curl -s -o "$outfile" -w '%{http_code}' -X "$method" "${BASE}${path}" -H "Authorization: Bearer ${TOKEN}")"
  else
    code="$(curl -s -o "$outfile" -w '%{http_code}' -X "$method" "${BASE}${path}")"
  fi

  if [[ "$code" == "$expect" ]]; then
    printf '%-42s PASS expected=%s got=%s\n' "$name" "$expect" "$code"
    PASS=$((PASS + 1))
  else
    printf '%-42s FAIL expected=%s got=%s\n' "$name" "$expect" "$code"
    if [[ -f "$outfile" ]]; then
      sed 's/^/  body: /' "$outfile"
      printf '\n'
    fi
    FAIL=$((FAIL + 1))
  fi
}

run_json health GET /health "" no 200
run_json docs GET /docs "" no 200
run_json openapi GET /openapi.json "" no 200
run_json login POST /auth/login '{"email":"admin@voiceagent.local","password":"admin123"}' no 200
TOKEN="$(json_get "/tmp/voice_api_${TS}_login.json" access_token)"

run_json auth_me GET /auth/me "" yes 200
run_json users_list GET /users "" yes 200
run_json users_create POST /users "{\"email\":\"curl-user-${TS}@voiceagent.local\",\"name\":\"Curl Analyst\",\"role\":\"analyst\",\"password\":\"curlpass123\"}" yes 201
USER_ID="$(json_get "/tmp/voice_api_${TS}_users_create.json" id)"
run_json users_get GET "/users/${USER_ID}" "" yes 200
run_json users_patch PATCH "/users/${USER_ID}" '{"role":"campaign_operator"}' yes 200

run_json contacts_list GET /contacts "" no 200
run_json contacts_create POST /contacts "{\"name\":\"Curl Patient ${TS}\",\"phone\":\"555-2200\",\"email\":\"curl${TS}@example.com\",\"company\":\"BrightCare Dental\",\"source\":\"curl\"}" yes 201
CONTACT_ID="$(json_get "/tmp/voice_api_${TS}_contacts_create.json" id)"
run_json contacts_get GET "/contacts/${CONTACT_ID}" "" no 200
run_json contacts_patch PATCH "/contacts/${CONTACT_ID}" '{"phone":"555-3300","source":"curl-updated"}' yes 200

run_json appointments_list GET /appointments "" no 200
run_json appointments_create POST /appointments "{\"contact_id\":\"${CONTACT_ID}\",\"contact_name\":\"Curl Patient ${TS}\",\"title\":\"Dental cleaning\",\"starts_at\":\"Tuesday 10:00 AM\",\"status\":\"booked\",\"notes\":\"Created by curl suite\"}" yes 201
APPOINTMENT_ID="$(json_get "/tmp/voice_api_${TS}_appointments_create.json" id)"
run_json appointments_get GET "/appointments/${APPOINTMENT_ID}" "" no 200
run_json appointments_patch PATCH "/appointments/${APPOINTMENT_ID}" '{"status":"confirmed"}' yes 200

run_json agent_session POST /agent/session "{\"direction\":\"inbound\",\"contact_id\":\"${CONTACT_ID}\"}" yes 200
SESSION_ID="$(json_get "/tmp/voice_api_${TS}_agent_session.json" id)"
run_json agent_message POST /agent/message "{\"session_id\":\"${SESSION_ID}\",\"message\":\"Hi, this is Nora. I need a cleaning next Tuesday morning. My phone is 555-0100.\"}" yes 200
CALL_ID="$SESSION_ID"
run_json calls_list GET /calls "" no 200
run_json calls_get GET "/calls/${CALL_ID}" "" no 200
run_json calls_patch PATCH "/calls/${CALL_ID}" '{"outcome":"callback_requested","summary":"Curl suite updated call summary."}' yes 200

run_json knowledge_list GET /knowledge/documents "" no 200
run_json knowledge_create POST /knowledge/documents "{\"title\":\"Curl Emergency FAQ ${TS}\",\"source_name\":\"curl\",\"content\":\"Emergency appointments are available for urgent pain, swelling, or broken teeth.\"}" yes 201
DOC_ID="$(json_get "/tmp/voice_api_${TS}_knowledge_create.json" id)"
run_json knowledge_get GET "/knowledge/documents/${DOC_ID}" "" no 200
run_json knowledge_search POST /knowledge/search '{"query":"emergency appointments"}' no 200
run_json knowledge_answer POST /knowledge/answer '{"query":"Do you offer emergency appointments?","max_context_items":2}' no 200

run_json llm_health GET /llm/health "" yes 200
run_json llm_models GET /llm/models "" yes 200
run_json llm_chat POST /llm/chat '{"message":"Say hello as a dental receptionist in one short sentence.","model":"llama-3.1-8b-instant"}' yes 200

run_json campaigns_list GET /campaigns "" no 200
run_json campaigns_create POST /campaigns "{\"name\":\"Curl Whitening Campaign ${TS}\",\"mode\":\"outbound\",\"prompt\":\"Qualify whitening interest and offer an appointment.\"}" yes 201
CAMPAIGN_ID="$(json_get "/tmp/voice_api_${TS}_campaigns_create.json" id)"
run_json campaigns_get GET "/campaigns/${CAMPAIGN_ID}" "" no 200
run_json campaigns_patch PATCH "/campaigns/${CAMPAIGN_ID}" '{"status":"active"}' yes 200
run_json campaigns_import POST "/campaigns/${CAMPAIGN_ID}/import-csv" '{"csv_content":"name,phone,email,company\nCurl Lead,555-7777,curl-lead@example.com,BrightCare Dental\n"}' yes 200
run_json campaigns_start POST "/campaigns/${CAMPAIGN_ID}/start-simulation" "" yes 200

run_json analytics GET /analytics/overview "" no 200
run_json sip_trunks_list GET /sip/trunks "" no 200
run_json sip_trunks_create POST /sip/trunks "{\"name\":\"Curl SIP Lab ${TS}\",\"provider\":\"local-asterisk\",\"host\":\"sip.local\",\"username\":\"voice-agent\",\"caller_id\":\"+15550000000\",\"max_concurrent_calls\":3,\"status\":\"draft\"}" yes 201
TRUNK_ID="$(json_get "/tmp/voice_api_${TS}_sip_trunks_create.json" id)"
run_json sip_trunks_get GET "/sip/trunks/${TRUNK_ID}" "" no 200
run_json sip_trunks_patch PATCH "/sip/trunks/${TRUNK_ID}" '{"status":"active","max_concurrent_calls":5}' yes 200
run_json sip_outbound POST /sip/outbound-call "{\"trunk_id\":\"${TRUNK_ID}\",\"contact_id\":\"${CONTACT_ID}\",\"campaign_id\":\"${CAMPAIGN_ID}\"}" yes 201

run_json amd_settings_get GET /amd/settings "" no 200
run_json amd_settings_put PUT /amd/settings '{"enabled":true,"detection_window_seconds":4,"sensitivity":0.72}' yes 200
run_json amd_analyze POST /amd/analyze '{"greeting_text":"Please leave a message after the tone.","audio_duration_seconds":8}' yes 200

run_json voicemail_list GET /voicemail/templates "" no 200
run_json voicemail_create POST /voicemail/templates "{\"name\":\"Curl Voicemail ${TS}\",\"message_text\":\"Hi, this is BrightCare Dental calling about your appointment.\",\"voice\":\"browser-default\",\"status\":\"draft\"}" yes 201
VOICEMAIL_ID="$(json_get "/tmp/voice_api_${TS}_voicemail_create.json" id)"
run_json voicemail_get GET "/voicemail/templates/${VOICEMAIL_ID}" "" no 200
run_json voicemail_patch PATCH "/voicemail/templates/${VOICEMAIL_ID}" '{"status":"active"}' yes 200
run_json voicemail_delete DELETE "/voicemail/templates/${VOICEMAIL_ID}" "" yes 204

run_json profiles_list GET /agent-profiles "" no 200
run_json profiles_create POST /agent-profiles "{\"name\":\"Curl Ava ${TS}\",\"persona\":\"Warm dental receptionist\",\"system_prompt\":\"Book appointments and answer BrightCare Dental questions.\",\"voice\":\"browser-default\",\"language\":\"en-US\",\"temperature\":0.3,\"status\":\"draft\"}" yes 201
PROFILE_ID="$(json_get "/tmp/voice_api_${TS}_profiles_create.json" id)"
run_json profiles_get GET "/agent-profiles/${PROFILE_ID}" "" no 200
run_json profiles_patch PATCH "/agent-profiles/${PROFILE_ID}" '{"status":"active","temperature":0.2}' yes 200

run_json orchestration_get GET /orchestration/config "" no 200
run_json orchestration_put PUT /orchestration/config '{"framework":"pipecat","transport":"browser","vad_enabled":true,"barge_in_enabled":true,"target_latency_ms":900}' yes 200
run_json recordings_list GET /recordings "" no 200
run_json recordings_create POST /recordings "{\"call_id\":\"${CALL_ID}\",\"storage_url\":\"minio://recordings/curl-call.wav\",\"duration_seconds\":42,\"transcript_status\":\"ready\"}" yes 201
RECORDING_ID="$(json_get "/tmp/voice_api_${TS}_recordings_create.json" id)"
run_json recordings_get GET "/recordings/${RECORDING_ID}" "" no 200
run_json runtime_get GET /settings/runtime "" no 200
run_json runtime_put PUT /settings/runtime '{"llm_provider":"groq","llm_model":"llama-3.1-8b-instant","groq_base_url":"https://api.groq.com/openai/v1","stt_provider":"faster-whisper","tts_provider":"piper","telephony_mode":"browser"}' yes 200
run_json costs_estimate POST /costs/estimate '{"daily_calls":2000,"average_call_minutes":2.5,"live_answer_rate":0.35,"sip_cost_per_minute":0.01,"ai_cost_per_live_minute":0.001,"voicemail_cost_per_minute":0}' yes 200

printf '\nSUMMARY pass=%s fail=%s\n' "$PASS" "$FAIL"
printf 'LLM health body: '
cat "/tmp/voice_api_${TS}_llm_health.json"
printf '\nLLM chat body: '
cat "/tmp/voice_api_${TS}_llm_chat.json"
printf '\nKnowledge answer body: '
cat "/tmp/voice_api_${TS}_knowledge_answer.json"
printf '\n'
