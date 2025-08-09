<template>
  <div class="rounded-xl p-8 bg-white/80 backdrop-blur-sm border border-gray-200 shadow-xl dark:bg-neutral-900/80 dark:border-neutral-800 dark:shadow-black/30 flex flex-col">
    <!-- Chat Log -->
    <div ref="chatContainer" class="flex flex-col space-y-4 overflow-y-auto max-h-[60vh] mb-6 pr-2">
      <div v-for="(turn, idx) in history" :key="idx" class="flex w-full">
        <!-- System / summary -->
        <div v-if="turn.role === 'system'" class="w-full text-center text-xs italic opacity-70 whitespace-pre-wrap">
          {{ turn.content }}
        </div>
        <!-- User bubble -->
        <div
          v-else-if="turn.role === 'user'"
          class="ml-auto max-w-[85%] bg-blue-600 text-white rounded-lg px-4 py-3 whitespace-pre-wrap shadow"
        >
          {{ turn.content }}
        </div>
        <!-- Assistant bubble -->
        <div
          v-else
          class="mr-auto max-w-[85%] bg-gray-100 dark:bg-neutral-800 text-gray-900 dark:text-gray-100 px-4 py-3 rounded-lg whitespace-pre-wrap shadow"
        >
          {{ turn.content }}
        </div>
      </div>
      <!-- Loading indicator bubble -->
      <div v-if="loading" class="flex w-full">
        <div class="mr-auto max-w-[70%] bg-gray-100 dark:bg-neutral-800 text-gray-600 dark:text-gray-300 px-4 py-3 rounded-lg shadow flex items-center space-x-2">
          <div class="flex space-x-1">
            <span class="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></span>
            <span class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay:0.1s"></span>
            <span class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay:0.2s"></span>
          </div>
          <span>Thinking...</span>
        </div>
      </div>
    </div>

    <!-- TDEE Panel -->
    <div v-if="tdeeData" class="mb-4 p-4 rounded-lg bg-gradient-to-r from-blue-50 to-blue-100 dark:from-blue-950/40 dark:to-blue-900/20 border border-blue-200/60 dark:border-blue-800/40 text-sm text-blue-900 dark:text-blue-200">
      <div class="font-semibold mb-1">Caloric Estimates</div>
      <div class="flex flex-wrap gap-4">
        <div>BMR: <span class="font-medium">{{ tdeeData.bmr.toFixed(0) }}</span></div>
        <div>TDEE: <span class="font-medium">{{ tdeeData.tdee.toFixed(0) }}</span></div>
        <div>Range: <span class="font-medium">{{ tdeeData.range[0].toFixed(0) }} - {{ tdeeData.range[1].toFixed(0) }}</span></div>
      </div>
    </div>

    <!-- Profile Chips & Missing Info Notices -->
    <div v-if="showProfileBar" class="mb-6">
      <div class="flex flex-wrap gap-2 mb-2">
        <span v-if="profile.sex" class="chip">Sex: {{ profile.sex }}</span>
        <span v-if="profile.age !== null" class="chip">Age: {{ profile.age }}</span>
        <span v-if="profile.weight_kg !== null" :class="weightChipClass">Weight: {{ formattedWeight }}</span>
        <span v-if="profile.height_cm !== null" :class="heightChipClass">Height: {{ formattedHeight }}</span>
        <span v-if="profile.activity_factor !== null" :class="activityChipClass">Activity: {{ activityName }}</span>
      </div>
      <div v-if="tdeeIntentNeedsFields" class="text-xs text-amber-700 dark:text-amber-300">Need: {{ missing.join(', ') }}</div>
      <div v-else-if="gentleReminder" class="text-xs text-gray-500 dark:text-gray-400">Provide remaining info anytime for numbers.</div>
    </div>

    <!-- Input Section -->
    <div class="mb-4">
      <label for="user-input" class="block text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
        {{ inputLabel }}
      </label>
      <div class="relative">
        <textarea
          id="user-input"
          v-model="userInput"
          :placeholder="placeholder"
          :rows="textareaRows"
          :maxlength="maxLength"
          class="w-full px-4 py-3 border-2 border-gray-200 dark:border-neutral-800 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500/60 focus:border-blue-500/60 resize-none transition-all duration-200 placeholder-gray-400 dark:placeholder-gray-500 bg-white/70 dark:bg-neutral-900/70 text-gray-900 dark:text-gray-100"
          :disabled="loading"
          @keydown.enter.prevent="handleEnter"
          @keydown.ctrl.enter.prevent="sendMessage"
          @keydown.meta.enter.prevent="sendMessage"
        ></textarea>
        <div class="absolute bottom-2 right-2 text-xs text-gray-400 dark:text-gray-500" v-if="maxLength">
          {{ userInput.length }}/{{ maxLength }}
        </div>
      </div>
      <div class="flex justify-between items-center mt-2">
        <p class="text-xs text-gray-500 dark:text-gray-400 flex items-center">
          <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg dark:text-gray-200 dark:bg-neutral-800 dark:border-neutral-700">Enter</kbd>
          <span class="ml-2">to send</span>
          <span class="mx-2">|</span>
          <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg dark:text-gray-200 dark:bg-neutral-800 dark:border-neutral-700">⌘</kbd>
          <span class="mx-1">+</span>
          <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg dark:text-gray-200 dark:bg-neutral-800 dark:border-neutral-700">Enter</kbd>
          <span class="ml-2">(or Ctrl) for newline</span>
        </p>
      </div>
    </div>

    <!-- Send Button -->
    <div>
      <button
        @click="sendMessage"
        :disabled="loading || !userInput.trim() || (!!maxLength && userInput.length > maxLength)"
        class="w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-white dark:focus:ring-offset-neutral-900 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 disabled:transform-none"
      >
        <span v-if="!loading">{{ sendButtonText }}</span>
        <span v-else class="flex items-center">
          <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          Thinking...
        </span>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue';
import axios from 'axios';

// Types
export interface HistoryTurn { role: 'user' | 'assistant' | 'system'; content: string }
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
  sendButtonText?: string
  textareaRows?: number
  maxLength?: number
}

const props = withDefaults(defineProps<Props>(), {
  apiEndpoint: 'http://localhost:8000/api/v1/chat2',
  inputLabel: 'Ask your fitness question:',
  placeholder: 'e.g., Create a workout plan for beginners, or suggest a healthy meal...',
  sendButtonText: 'Send',
  textareaRows: 3,
  maxLength: 1000
});

// Emits
const emit = defineEmits<{ messageSent: [message: string]; responseReceived: [response: string] }>();

// Reactive State
const userInput = ref('');
const loading = ref(false);
const history = ref<HistoryTurn[]>([
  { role: 'assistant', content: 'Hi. Ask me anything about simple fitness.' }
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
const chatContainer = ref<HTMLDivElement | null>(null);
async function scrollToBottom() {
  await nextTick();
  const el = chatContainer.value; if (!el) return;
  el.scrollTop = el.scrollHeight;
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
  if (props.maxLength && content.length > props.maxLength) return;

  history.value.push({ role: 'user', content });
  emit('messageSent', content);
  userInput.value = '';
  await scrollToBottom();
  loading.value = true;
  maybeSummarizeHistory();

  try {
    const res = await axios.post<BackendResponse>(props.apiEndpoint, { history: history.value }, { headers: { 'Content-Type': 'application/json' } });
    const data = res.data;
    history.value.push({ role: 'assistant', content: data.response });
    profile.value = data.profile || profile.value;
    tdeeData.value = data.tdee;
    missing.value = data.missing || [];
    askedThisIntent.value = data.asked_this_intent || [];
    intent.value = data.intent || '';
    emit('responseReceived', data.response);
  } catch (e) {
    history.value.push({ role: 'assistant', content: 'Sorry, there was an error processing that. Please try again.' });
  } finally {
    loading.value = false;
    scrollToBottom();
  }
}

function handleEnter(e: KeyboardEvent) {
  if (e.shiftKey || e.metaKey || e.ctrlKey) { return; }
  sendMessage();
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
