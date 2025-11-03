<template>
    <div class="h-screen bg-gray-50 transition-colors duration-300 flex flex-col" :style="isDark ? 'background-color: #0c151b;' : 'background-color: rgb(249 250 251);'">
        <!-- Header -->
        <div class="w-full bg-gray-100 dark:bg-[#080e12] flex-shrink-0">
            <div class="w-full px-4 sm:px-6 py-3 sm:py-4 flex items-center justify-between">
                <HypertrofitLogo />
                
                <!-- Theme Toggle (inline with header) -->
                <button
                    class="inline-flex items-center gap-1.5 sm:gap-2 rounded-full border border-gray-200/70 bg-gray-100 px-3 sm:px-4 py-2 shadow-lg hover:bg-gray-200 dark:border-neutral-800 dark:bg-[#080e12] dark:hover:bg-neutral-700 text-gray-700 dark:text-gray-200 transition-colors min-h-[40px] sm:min-h-[44px]"
                    @click="toggleTheme"
                    aria-label="Toggle color scheme"
                >
                    <span class="sr-only">Toggle Theme</span>
                    <svg v-if="!isDark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-4 w-4 sm:h-5 sm:w-5">
                        <path d="M12 2.25a.75.75 0 01.75.75v2.25a.75.75 0 01-1.5 0V3a.75.75 0 01.75-.75zM7.5 12a4.5 4.5 0 119 0 4.5 4.5 0 01-9 0zM18.894 6.166a.75.75 0 00-1.06-1.06l-1.591 1.59a.75.75 0 101.06 1.061l1.591-1.59zM21.75 12a.75.75 0 01-.75.75h-2.25a.75.75 0 010-1.5H21a.75.75 0 01.75.75zM17.834 18.894a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 10-1.061 1.06l1.59 1.591zM12 18a.75.75 0 01.75.75V21a.75.75 0 01-1.5 0v-2.25A.75.75 0 0112 18zM7.758 17.303a.75.75 0 00-1.061-1.06l-1.591 1.59a.75.75 0 001.06 1.061l1.591-1.59zM6 12a.75.75 0 01-.75.75H3a.75.75 0 010-1.5h2.25A.75.75 0 016 12zM6.697 7.757a.75.75 0 001.06-1.06l-1.59-1.591a.75.75 0 00-1.061 1.06l1.59 1.591z"/>
                    </svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-4 w-4 sm:h-5 sm:w-5">
                        <path fill-rule="evenodd" d="M9.528 1.718a.75.75 0 01.162.819A8.97 8.97 0 009 6a9 9 0 009 9 8.97 8.97 0 003.463-.69a.75.75 0 01.981.98 10.503 10.503 0 01-9.694 6.46c-5.799 0-10.5-4.701-10.5-10.5 0-4.368 2.667-8.112 6.46-9.694a.75.75 0 01.818.162z" clip-rule="evenodd" />
                    </svg>
                    <span class="text-xs sm:text-sm font-medium">{{ isDark ? 'Dark' : 'Light' }}</span>
                </button>
            </div>
        </div>

        <!-- Hero -->
        <div v-if="showHero" class="w-full bg-white dark:bg-[#0c151b]">
            <div class="max-w-3xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
                <div class="rounded-2xl bg-gray-50/60 dark:bg-[#0e1820] p-6 sm:p-8 shadow-sm">
                    <h1 class="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-50">Your simple fitness and nutrition coach</h1>
                    <p class="mt-2 text-gray-700 dark:text-gray-300 text-sm sm:text-base">Friendly, beginner-focused guidance. Small steps. Clear habits.</p>
                    <div class="mt-4 grid grid-cols-1 sm:grid-cols-3 gap-2 sm:gap-3">
                        <button @click="applyQuickPrompt('What\'s a good workout split for beginners?')" class="text-left text-sm px-3 py-2 rounded-lg bg-white/80 hover:bg-white text-gray-800 dark:bg-[#0b141a] dark:hover:bg-[#0c151b] dark:text-gray-100 transition-colors shadow-sm">What's a good workout split for beginners?</button>
                        <button @click="applyQuickPrompt('How much protein should I eat?')" class="text-left text-sm px-3 py-2 rounded-lg bg-white/80 hover:bg-white text-gray-800 dark:bg-[#0b141a] dark:hover:bg-[#0c151b] dark:text-gray-100 transition-colors shadow-sm">How much protein should I eat?</button>
                        <button @click="applyQuickPrompt('What is RIR?')" class="text-left text-sm px-3 py-2 rounded-lg bg-white/80 hover:bg-white text-gray-800 dark:bg-[#0b141a] dark:hover:bg-[#0c151b] dark:text-gray-100 transition-colors shadow-sm">What is RIR?</button>
                    </div>
                    <p class="mt-4 text-xs text-gray-500 dark:text-gray-400">For education only. Not medical advice. Consult a healthcare professional for personal guidance.</p>
                </div>
            </div>
        </div>

        <!-- Compact disclaimer banner (shown after first message) -->
        <div v-if="!showHero && showDisclaimer" @click="showDisclaimer = false" class="w-full bg-red-50/80 dark:bg-red-950/30 border-b border-red-200/50 dark:border-red-900/40 cursor-pointer hover:bg-red-100/80 dark:hover:bg-red-950/40 transition-colors">
            <div class="max-w-3xl mx-auto px-4 sm:px-6 py-3 sm:py-3.5">
                <p class="text-xs sm:text-sm font-medium text-red-800 dark:text-red-300 leading-relaxed text-center">
                    <span class="font-semibold">For education only.</span> Not medical advice. Consult a healthcare professional for personal guidance.
                </p>
            </div>
        </div>

        <!-- Main Chat Interface - Full Height -->
        <div class="flex-1 min-h-0 flex flex-col relative overflow-hidden bg-gray-50 dark:bg-[#0c151b]">
            <ChatInterface
                input-label="Ask your fitness question:"
                placeholder="e.g., Create a workout plan for beginners, help me plan my meals, or ask about exercises..."
                send-button-text="Get Fitness Advice"
                :textarea-rows="3"
                :max-length="1000"
                @message-sent="onMessageSent"
                @response-received="onResponseReceived"
            />
        </div>

        <!-- Interaction History - Collapsible sidebar or modal -->
        <div v-if="interactionHistory.length > 0" class="fixed bottom-3 sm:bottom-4 right-3 sm:right-4 z-30">
            <details class="text-xs sm:text-sm">
                <summary
                    class="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 bg-gray-50 dark:bg-[#080e12] px-2.5 sm:px-3 py-1.5 sm:py-2 rounded-lg border border-gray-200 dark:border-neutral-800 min-h-[32px] sm:min-h-[36px] flex items-center"
                >
                    Recent ({{ interactionHistory.length }})
                </summary>
                <div class="absolute bottom-full right-0 mb-2 p-3 sm:p-4 bg-gray-50 dark:bg-[#080e12] border border-gray-200 dark:border-neutral-800 rounded-lg shadow-lg w-[280px] sm:min-w-[300px] max-h-60 overflow-y-auto">
                    <h3 class="text-xs sm:text-sm font-semibold text-gray-700 dark:text-gray-200 mb-2 sm:mb-3">
                        Recent Interactions
                    </h3>
                    <div class="space-y-1.5 sm:space-y-2">
                        <div
                            v-for="(interaction, index) in interactionHistory.slice(-5)"
                            :key="index"
                            class="p-1.5 sm:p-2 rounded text-xs bg-gray-50 text-gray-700 border border-gray-200 dark:bg-neutral-800 dark:text-gray-200 dark:border-neutral-700"
                        >
                            <div class="font-medium text-gray-700 dark:text-gray-100">
                                {{ interaction.type }}:
                            </div>
                            <div class="text-gray-600 dark:text-gray-300 truncate">
                                {{ interaction.message }}
                            </div>
                            <div class="text-xs text-gray-500 dark:text-gray-400">
                                {{ interaction.timestamp }}
                            </div>
                        </div>
                    </div>
                </div>
            </details>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import ChatInterface from "./components/ChatInterface.vue";
import HypertrofitLogo from "./components/HypertrofitLogo.vue";

// Theme state and logic
const isDark = ref(false);
const applyTheme = (dark: boolean) => {
    const root = document.documentElement;
    if (dark) {
        root.classList.add("dark");
        localStorage.setItem("theme", "dark");
    } else {
        root.classList.remove("dark");
        localStorage.setItem("theme", "light");
    }
    isDark.value = dark;
};
const toggleTheme = () => applyTheme(!isDark.value);

onMounted(() => {
    // Initialize from localStorage or system preference (index.html pre-applies to avoid FOUC)
    const hasDarkClass = document.documentElement.classList.contains("dark");
    isDark.value = hasDarkClass;
});

// State to track interactions
interface Interaction {
    type: string;
    message: string;
    timestamp: string;
}

const interactionHistory = ref<Interaction[]>([]);

// Landing hero state
const showHero = ref(true);
// Disclaimer banner state
const showDisclaimer = ref(true);

// Helper function to add interaction
const addInteraction = (type: string, message: string): void => {
    const timestamp = new Date().toLocaleTimeString();
    interactionHistory.value.push({ type, message, timestamp });
};

// Quick prompt applier: prefill the textarea and focus it; hide hero
const applyQuickPrompt = (text: string): void => {
    const input = document.getElementById('user-input') as HTMLTextAreaElement | null;
    if (input) {
        input.value = text;
        input.dispatchEvent(new Event('input', { bubbles: true }));
        input.focus();
    }
    if (showHero.value) showHero.value = false;
};

// Event handlers for ChatInterface events
const onMessageSent = (message: string): void => {
    addInteraction("Message Sent", message);
    // Hide hero after first message
    if (showHero.value) showHero.value = false;
    // Show disclaimer when hero is hidden
    if (!showHero.value && showDisclaimer.value) showDisclaimer.value = true;
};

const onResponseReceived = (response: string): void => {
    addInteraction("Response Received", response);
};
</script>
