<template>
  <div class="flex flex-col h-full w-full min-h-0">
    <!-- Chat History - Takes up most of the screen -->
    <div class="flex-1 overflow-y-auto px-3 sm:px-6 py-4 sm:py-6 min-h-0">
      <!-- Welcome Message -->
      <div v-if="history.length === 1" class="text-center py-8 sm:py-12">
        <div class="text-2xl sm:text-4xl font-bold text-gray-800 dark:text-gray-100 mb-3 sm:mb-4">
          Hypertrofit
        </div>
        <div class="text-base sm:text-lg text-gray-600 dark:text-gray-400 w-full max-w-4xl mx-auto px-2">
          {{ history[0].content }}
        </div>
      </div>

      <!-- Chat Messages -->
      <div v-else class="space-y-4 sm:space-y-6">
        <div v-for="(turn, idx) in history.slice(1)" :key="idx" class="flex w-full">
          <!-- User message -->
          <div
            v-if="turn.role === 'user'"
            class="ml-auto flex justify-end"
          >
            <div class="flex flex-col items-end">
              <div 
                :class="getMessageBubbleClasses(turn.content)"
                class="bg-blue-600 text-white rounded-3xl px-3 py-2.5 sm:px-4 sm:py-3 whitespace-pre-wrap text-sm sm:text-base transition-all duration-200 ease-out"
              >
                {{ turn.content }}
              </div>
              <div class="flex items-center space-x-2 mt-1 mr-2">
                <div v-if="turn.timestamp" class="text-xs text-gray-400 dark:text-gray-500">
                  {{ formatTime(turn.timestamp) }}
                </div>
                <div v-if="turn.status" class="flex items-center">
                  <span v-if="turn.status === 'sending'" class="text-xs text-gray-400 dark:text-gray-500">
                    <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  </span>
                  <span v-else-if="turn.status === 'sent'" class="text-xs text-gray-400 dark:text-gray-500">✓</span>
                  <span v-else-if="turn.status === 'delivered'" class="text-xs text-blue-500 dark:text-blue-400">✓</span>
                  <span v-else-if="turn.status === 'error'" class="text-xs text-red-500 dark:text-red-400">⚠</span>
                </div>
              </div>
            </div>
          </div>
          <!-- Assistant message -->
          <div
            v-else-if="turn.role === 'assistant'"
            class="mr-auto flex justify-start"
          >
            <div class="flex flex-col items-start">
              <div 
                :class="getMessageBubbleClasses(turn.content)"
                class="bg-gray-100 dark:bg-neutral-800 text-gray-900 dark:text-gray-100 px-3 py-2.5 sm:px-4 sm:py-3 rounded-3xl whitespace-pre-wrap text-sm sm:text-base transition-all duration-200 ease-out"
              >
                {{ turn.content }}
              </div>
              <div v-if="turn.timestamp" class="text-xs text-gray-400 dark:text-gray-500 mt-1 ml-2">
                {{ formatTime(turn.timestamp) }}
              </div>
            </div>
          </div>
          <!-- System message -->
          <div
            v-else
            class="w-full text-center text-xs sm:text-sm italic text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-neutral-900/50 rounded-lg px-3 py-2 mx-2"
          >
            {{ turn.content }}
          </div>
        </div>

        <!-- Loading indicator -->
        <div v-if="loading" class="flex w-full">
          <div class="mr-auto flex justify-start">
            <div class="bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-gray-300 px-3 py-2.5 sm:px-4 sm:py-3 rounded-3xl flex items-center space-x-2 text-sm sm:text-base max-w-[280px] sm:max-w-[320px]">
              <div class="flex items-center space-x-1">
                <span class="text-gray-500 dark:text-gray-400 mr-2">AI is typing</span>
                <div class="flex space-x-1">
                  <span class="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce"></span>
                  <span class="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay:0.1s"></span>
                  <span class="w-2 h-2 bg-gray-400 dark:bg-gray-500 rounded-full animate-bounce" style="animation-delay:0.2s"></span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- TDEE Panel -->
      <div v-if="tdeeData" class="mt-4 sm:mt-6 w-full px-2">
        <div class="p-3 sm:p-4 rounded-xl bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-950/40 dark:to-blue-900/20 border border-blue-200/60 dark:border-blue-800/40 text-xs sm:text-sm text-blue-900 dark:text-blue-200 max-w-4xl mx-auto">
          <div class="font-semibold mb-2">Caloric Estimates</div>
          <div class="flex flex-col sm:flex-row sm:flex-wrap gap-2 sm:gap-4">
            <div>BMR: <span class="font-medium">{{ tdeeData.bmr.toFixed(0) }}</span></div>
            <div>TDEE: <span class="font-medium">{{ tdeeData.tdee.toFixed(0) }}</span></div>
            <div>Range: <span class="font-medium">{{ tdeeData.range[0].toFixed(0) }} - {{ tdeeData.range[1].toFixed(0) }}</span></div>
          </div>
        </div>
      </div>

      <!-- Profile Chips & Missing Info Notices -->
      <div v-if="showProfileBar" class="mt-4 sm:mt-6 w-full px-2">
        <div class="max-w-4xl mx-auto">
          <div class="flex flex-wrap gap-1.5 sm:gap-2 mb-2">
            <span v-if="profile.sex" class="chip text-xs">Sex: {{ profile.sex }}</span>
            <span v-if="profile.age !== null" class="chip text-xs">Age: {{ profile.age }}</span>
            <span v-if="profile.weight_kg !== null" :class="weightChipClass + ' text-xs'">Weight: {{ formattedWeight }}</span>
            <span v-if="profile.height_cm !== null" :class="heightChipClass + ' text-xs'">Height: {{ formattedHeight }}</span>
            <span v-if="profile.activity_factor !== null" :class="activityChipClass + ' text-xs'">Activity: {{ activityName }}</span>
          </div>
          <div v-if="tdeeIntentNeedsFields" class="text-xs text-amber-700 dark:text-amber-300 bg-amber-50 dark:bg-amber-950/30 px-3 py-2 rounded-lg">
            Need: {{ missing.join(', ') }}
          </div>
          <div v-else-if="gentleReminder" class="text-xs text-gray-500 dark:text-gray-400 bg-gray-50 dark:bg-neutral-900/50 px-3 py-2 rounded-lg">
            Provide remaining info anytime for numbers.
          </div>
        </div>
      </div>
    </div>

    <!-- Input Section - Fixed at bottom -->
    <div class="bg-gray-100 dark:bg-[#080e12]">
      <div class="w-full px-3 sm:px-6 py-3 sm:py-4">
        <div class="relative max-w-4xl mx-auto">
          <textarea
            id="user-input"
            v-model="userInput"
            :placeholder="placeholder"
            :rows="textareaRows"
            :maxlength="maxLength"
            class="w-full px-3 py-2.5 sm:px-4 sm:py-3 pr-14 border border-gray-300 dark:border-neutral-600 rounded-xl shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/60 resize-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-neutral-800 text-gray-900 dark:text-gray-100 text-sm sm:text-base"
            :disabled="loading"
            @keydown.enter.prevent="handleEnter"
            @keydown.ctrl.enter.prevent="sendMessage"
            @keydown.meta.enter.prevent="sendMessage"
          ></textarea>

          <!-- Circular send button inside input -->
          <button
            @click="sendMessage"
            :disabled="loading || !userInput.trim() || (!!maxLength && userInput.length > maxLength)"
            class="absolute bottom-3 sm:bottom-3.5 right-1.5 sm:right-2 w-9 h-9 sm:w-10 sm:h-10 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 dark:disabled:bg-gray-600 text-white rounded-full flex items-center justify-center focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-neutral-800 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-sm hover:shadow-md z-10"
          >
            <span v-if="!loading">
              <svg class="w-4 h-4 sm:w-5 sm:h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8"></path>
              </svg>
            </span>
            <span v-else class="flex items-center">
              <svg class="animate-spin w-3.5 h-3.5 sm:w-4 sm:h-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            </span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import axios from 'axios';

// Types
export interface HistoryTurn { 
  role: 'user' | 'assistant' | 'system'; 
  content: string;
  timestamp?: Date;
  status?: 'sending' | 'sent' | 'delivered' | 'error';
}
export type BackendResponse = {
  response: string
  profile: { sex: string | null; age: number | null; weight_kg: number | null; height_cm: number | null; activity_factor: number | null }
  tdee: { bmr: number; tdee: number; range: [number, number] } | null
  missing: string[]
  asked_this_intent: string[]
  intent: string
}

interface Props {
  apiEndpoint?: string
  inputLabel?: string
  placeholder?: string
  textareaRows?: number
  maxLength?: number
}

// Replace with simple defineProps (no local var refs in defaults)
const props = defineProps<Props>();

// Local fallbacks (non-reactive to external prop changes, sufficient here)
const placeholder = props.placeholder ?? 'e.g., Create a workout plan for beginners, or suggest a healthy meal...';
const textareaRows = props.textareaRows ?? 3;
const maxLength = props.maxLength ?? 1000;

function resolveEndpoint(): string {
  const envBase = import.meta.env.VITE_API_BASE as string | undefined;

  console.log('[ChatInterface] Environment check:', {
    VITE_API_BASE: envBase,
    PROD: import.meta.env.PROD,
    MODE: import.meta.env.MODE
  });

  if (!envBase) {
    // This will now be very obvious in the console if the variable is missing
    console.error("FATAL: VITE_API_BASE environment variable is not set!");
    
    // For production, try to use the Railway URL as fallback
    if (import.meta.env.PROD) {
      console.warn("Attempting to use Railway fallback URL");
      return 'https://outstanding-caring-production.up.railway.app/api/v1/chat';
    }
    
    // Return a non-functional path to ensure it fails in development
    return '/error-vite-api-base-not-set';
  }
  
  // The env var should contain the full path including /api/v1
  let endpoint = `${envBase.replace(/\/$/, '')}/chat`;
  
  // Ensure we have the correct API path structure
  if (!endpoint.includes('/api/v1')) {
    console.warn('[ChatInterface] Environment variable missing /api/v1, fixing...');
    if (endpoint.includes('railway.app')) {
      endpoint = 'https://outstanding-caring-production.up.railway.app/api/v1/chat';
    } else {
      endpoint = `${envBase.replace(/\/$/, '')}/api/v1/chat`;
    }
  }
  
  console.log('[ChatInterface] Built endpoint from env:', endpoint);
  return endpoint;
}

console.debug('[ChatInterface] Using API endpoint:', resolveEndpoint());

// Emits
const emit = defineEmits<{ messageSent: [message: string]; responseReceived: [response: string] }>();

// Reactive State
const userInput = ref('');
const loading = ref(false);
const history = ref<HistoryTurn[]>([
  { role: 'assistant', content: 'Hey! How can I help you with your fitness today?' }
]);
const profile = ref<BackendResponse['profile']>({ sex: null, age: null, weight_kg: null, height_cm: null, activity_factor: null });
const tdeeData = ref<BackendResponse['tdee'] | null>(null);
const intent = ref<string>('');
const missing = ref<string[]>([]);
const askedThisIntent = ref<string[]>([]);

// Derived
const hasAnyProfile = computed(() => Object.values(profile.value).some(v => v !== null));
const showProfileBar = computed(() => hasAnyProfile.value || (intent.value === 'tdee' && missing.value.length > 0));
const activityName = computed(() => {
  if (profile.value.activity_factor == null) return '';
  const af = profile.value.activity_factor;
  if (af < 1.3) return 'Sedentary';
  if (af < 1.5) return 'Light';
  if (af < 1.7) return 'Moderate';
  if (af < 1.9) return 'Active';
  return 'Very Active';
});
const formattedWeight = computed(() => {
  if (profile.value.weight_kg == null) return '';
  const lbs = profile.value.weight_kg * 2.20462;
  return `${profile.value.weight_kg.toFixed(1)} kg (${lbs.toFixed(1)} lb)`;
});
const formattedHeight = computed(() => {
  if (profile.value.height_cm == null) return '';
  const totalInches = profile.value.height_cm / 2.54;
  const feet = Math.floor(totalInches / 12);
  const inches = Math.round(totalInches - feet * 12);
  return `${profile.value.height_cm.toFixed(0)} cm (${feet}'${inches}\")`;
});
const tdeeIntentNeedsFields = computed(() => intent.value === 'tdee' && missing.value.length > 0 && askedThisIntent.value.length > 0);
const gentleReminder = computed(() => intent.value === 'tdee' && missing.value.length > 0 && askedThisIntent.value.length === 0);

// Highlight chip classes when requested & missing
function chipBase(extra='') { return `chip ${extra}`; }
const requestedMissingSet = computed(() => new Set(missing.value));
const highlightIfMissing = (field: string) => tdeeIntentNeedsFields.value && requestedMissingSet.value.has(field) ? 'ring-2 ring-amber-500/70' : '';
const weightChipClass = computed(() => chipBase(highlightIfMissing('weight')));
const heightChipClass = computed(() => chipBase(highlightIfMissing('height')));
const activityChipClass = computed(() => chipBase(highlightIfMissing('activity')));

// Auto-scroll when history changes
async function scrollToBottom() {
  await nextTick();
  // Scroll the chat history container to bottom
  const chatHistoryEl = document.querySelector('.overflow-y-auto');
  if (chatHistoryEl) {
    chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
  }
}

// History summarization
function maybeSummarizeHistory() {
  if (history.value.length <= 60) return;
  const nonSystem: number[] = [];
  for (let i = 0; i < history.value.length; i++) {
    if (history.value[i].role !== 'system') nonSystem.push(i);
    if (nonSystem.length >= 40) break;
  }
  if (nonSystem.length < 40) return;
  const summaryProfileBits: string[] = [];
  if (profile.value.sex) summaryProfileBits.push(`sex:${profile.value.sex}`);
  if (profile.value.age != null) summaryProfileBits.push(`age:${profile.value.age}`);
  if (profile.value.weight_kg != null) summaryProfileBits.push(`weight:${profile.value.weight_kg}kg`);
  if (profile.value.height_cm != null) summaryProfileBits.push(`height:${profile.value.height_cm}cm`);
  if (profile.value.activity_factor != null) summaryProfileBits.push(`activity:${activityName.value}`);
  const summary = `${summaryProfileBits.join(', ')}${summaryProfileBits.length ? '; ' : ''}conversation continued (summarized)`;
  const keep: HistoryTurn[] = [];
  let inserted = false;
  for (let i = 0; i < history.value.length; i++) {
    if (nonSystem.includes(i)) {
      if (!inserted) { keep.push({ role: 'system', content: summary }); inserted = true; }
      continue;
    }
    keep.push(history.value[i]);
  }
  history.value = keep;
}

// Send logic
async function sendMessage() {
  const content = userInput.value.trim();
  if (!content) return;
  if (maxLength && content.length > maxLength) return;

  // Add user message with 'sending' status
  let userMessage: HistoryTurn = { role: 'user', content, timestamp: new Date(), status: 'sending' };
  history.value.push(userMessage);
  emit('messageSent', content);
  userInput.value = '';
  await scrollToBottom();
  
  // Update status to 'sent' immediately
  userMessage.status = 'sent';
  
  loading.value = true;
  maybeSummarizeHistory();

  const endpoint = resolveEndpoint();
  console.log(`[ChatInterface] Attempting to POST to: ${endpoint}`); // New log

  try {
    const isNewChatEndpoint = /\/chat\/?$/.test(endpoint);
    const payload = isNewChatEndpoint
      ? {
          history: history.value
            .filter(t => t.role !== 'system')
            .slice(0, -1)
            .map(t => ({ role: t.role, content: t.content })),
          message: content
        }
      : { history: history.value };

    const res = await axios({
      url: endpoint,
      method: 'POST',
      data: payload,
      headers: { 'Content-Type': 'application/json' }
    });
    const data = res.data;
    if (!data || typeof data !== 'object' || (data as any).response === undefined) {
      throw new Error('Unexpected response shape');
    }
    
    // Update user message status to 'delivered'
    userMessage.status = 'delivered';
    
    history.value.push({ role: 'assistant', content: data.response, timestamp: new Date() });
    profile.value = data.profile || profile.value;
    tdeeData.value = data.tdee;
    missing.value = data.missing || [];
    askedThisIntent.value = data.asked_this_intent || [];
    intent.value = data.intent || '';
    emit('responseReceived', data.response);
  } catch (e: any) {
    if (e?.response) {
      console.error('[ChatInterface] Chat request failed', {
        status: e.response.status,
        statusText: e.response.statusText,
        data: e.response.data,
        endpoint
      });
    } else {
      console.error('[ChatInterface] Chat request error', e, { endpoint });
    }
    
    // Update user message status to 'error'
    userMessage.status = 'error';
    
    history.value.push({ role: 'assistant', content: 'Sorry, there was an error processing that. Please try again.', timestamp: new Date() });
  } finally {
    loading.value = false;
    scrollToBottom();
  }
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey || e.metaKey || e.ctrlKey) { return; }
  sendMessage();
}

function getMessageBubbleClasses(content: string) {
  const length = content.length;
  
  // Very short messages (1-20 chars) - keep them compact
  if (length <= 20) {
    return 'max-w-[200px] sm:max-w-[240px]';
  }
  
  // Short messages (21-50 chars) - moderate width
  if (length <= 50) {
    return 'max-w-[280px] sm:max-w-[320px]';
  }
  
  // Medium messages (51-100 chars) - wider but not full width
  if (length <= 100) {
    return 'max-w-[400px] sm:max-w-[450px]';
  }
  
  // Long messages (101-200 chars) - use most of available width
  if (length <= 200) {
    return 'max-w-[500px] sm:max-w-[550px]';
  }
  
  // Very long messages (200+ chars) - use full available width
  return 'max-w-[600px] sm:max-w-[650px]';
}

function formatTime(timestamp: Date | undefined): string {
  if (!timestamp) return '';
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - timestamp.getTime()) / 1000);

  if (diffInSeconds < 60) {
    return `${diffInSeconds}s ago`;
  } else if (diffInSeconds < 3600) {
    const minutes = Math.floor(diffInSeconds / 60);
    return `${minutes}m ago`;
  } else if (diffInSeconds < 86400) {
    const hours = Math.floor(diffInSeconds / 3600);
    return `${hours}h ago`;
  } else {
    const days = Math.floor(diffInSeconds / 86400);
    return `${days}d ago`;
  }
}
</script>

<style scoped>
.chip {
  border-radius: 9999px; /* rounded-full */
  background-color: rgba(219,234,254,1); /* blue-100 */
  color: #1e3a8a; /* blue-800 */
  font-size: 0.75rem; /* text-xs */
  line-height: 1rem;
  padding: 0.25rem 0.5rem; /* px-2 py-1 */
}
:deep(.dark) .chip {
  background-color: rgba(30,58,138,0.3); /* dark:bg-blue-900/30 */
  color: #bfdbfe; /* dark:text-blue-200 */
}
</style>
