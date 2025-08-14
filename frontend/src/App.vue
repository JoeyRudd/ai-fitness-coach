<template>
    <div class="min-h-screen bg-gray-50 dark:bg-neutral-950 transition-colors duration-300">
        <!-- Theme Toggle (top-right) -->
        <button
            class="fixed top-4 right-4 z-50 inline-flex items-center gap-2 rounded-full border border-gray-200/70 bg-white/80 px-4 py-2 shadow-lg backdrop-blur-sm hover:bg-white dark:border-neutral-800 dark:bg-neutral-900/80 dark:hover:bg-neutral-900 text-gray-700 dark:text-gray-200 transition-colors"
            @click="toggleTheme"
            aria-label="Toggle color scheme"
        >
            <span class="sr-only">Toggle Theme</span>
            <svg v-if="!isDark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
                <path d="M12 18a6 6 0 1 0 0-12 6 6 0 0 0 0 12Zm0 4a1 1 0 0 1-1-1v-1.2a1 1 0 1 1 2 0V21a1 1 0 0 1-1 1Zm0-19a1 1 0 0 1 1-1h.2a1 1 0 1 1 0 2H13a1 1 0 0 1-1-1ZM4.222 5.636a1 1 0 0 1 1.414-1.414l.848.848a1 1 0 1 1-1.414 1.414l-.848-.848Zm12.254 12.254a1 1 0 0 1 1.414 0l.848.848a1 1 0 0 1-1.414 1.414l-.848-.848a1 1 0 0 1 0-1.414ZM1 13a1 1 0 1 1 0-2h1.2a1 1 0 1 1 0 2H1Zm19.8 0a1 1 0 1 1 0-2H22a1 1 0 1 1 0 2h-1.2ZM4.222 18.364l.848-.848a1 1 0 1 1 1.414 1.414l-.848.848a1 1 0 1 1-1.414-1.414ZM17.486 5.636a1 1 0 1 1 1.414-1.414l.848.848a1 1 0 0 1-1.414 1.414l-.848-.848Z"/>
            </svg>
            <svg v-else xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" class="h-5 w-5">
                <path d="M21.752 15.002A9.718 9.718 0 0 1 12.002 22C6.476 22 2 17.523 2 11.998 2 7.748 4.468 4.06 8.12 2.377a1 1 0 0 1 1.33 1.33A8.002 8.002 0 0 0 20 12.002a7.96 7.96 0 0 1-1.54 4.608 1 1 0 0 1-1.708-.608Z"/>
            </svg>
            <span class="text-sm font-medium">{{ isDark ? 'Dark' : 'Light' }}</span>
        </button>

        <!-- Header -->
        <div class="w-full bg-white/80 dark:bg-neutral-900/80 backdrop-blur-sm border-b border-gray-200 dark:border-neutral-800">
            <div class="w-full px-6 py-4">
                <h1 class="text-2xl font-bold text-gray-800 dark:text-gray-100">
                    AI Fitness Coach
                </h1>
            </div>
        </div>

        <!-- Main Chat Interface - Full Width -->
        <div class="flex-1 flex flex-col h-[calc(100vh-120px)]">
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

        <!-- Connection Status - Fixed at bottom above input -->
        <div
            v-if="connectionStatus"
            class="fixed bottom-24 left-1/2 transform -translate-x-1/2 z-40 px-4 py-2 rounded-lg text-sm border shadow-lg"
            :class="connectionStatusClass"
        >
            {{ connectionStatus }}
        </div>

        <!-- Interaction History - Collapsible sidebar or modal -->
        <div v-if="interactionHistory.length > 0" class="fixed bottom-4 right-4 z-30">
            <details class="text-sm">
                <summary
                    class="cursor-pointer text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 bg-white/80 dark:bg-neutral-900/80 px-3 py-2 rounded-lg border border-gray-200 dark:border-neutral-800 backdrop-blur-sm"
                >
                    Recent ({{ interactionHistory.length }})
                </summary>
                <div class="absolute bottom-full right-0 mb-2 p-4 bg-white dark:bg-neutral-900 border border-gray-200 dark:border-neutral-800 rounded-lg shadow-lg backdrop-blur-sm min-w-[300px] max-h-60 overflow-y-auto">
                    <h3 class="text-sm font-semibold text-gray-700 dark:text-gray-200 mb-3">
                        Recent Interactions
                    </h3>
                    <div class="space-y-2">
                        <div
                            v-for="(interaction, index) in interactionHistory.slice(-5)"
                            :key="index"
                            class="p-2 rounded text-xs bg-gray-50 text-gray-700 border border-gray-200 dark:bg-neutral-800 dark:text-gray-200 dark:border-neutral-700"
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
import { ref, computed, onMounted } from "vue";
import ChatInterface from "./components/ChatInterface.vue";

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
const connectionStatus = ref<string>("");

// Computed class for connection status styling
const connectionStatusClass = computed(() => {
    if (
        connectionStatus.value.includes("Error") ||
        connectionStatus.value.includes("Failed")
    ) {
        return "bg-red-50 border-red-200 text-red-700 dark:bg-red-950/60 dark:border-red-900 dark:text-red-300";
    } else if (connectionStatus.value.includes("Success")) {
        return "bg-green-50 border-green-200 text-green-700 dark:bg-emerald-950/60 dark:border-emerald-900 dark:text-emerald-300";
    } else {
        return "bg-blue-50 border-blue-200 text-blue-700 dark:bg-sky-950/60 dark:border-sky-900 dark:text-sky-300";
    }
});

// Helper function to add interaction
const addInteraction = (type: string, message: string): void => {
    const timestamp = new Date().toLocaleTimeString();
    interactionHistory.value.push({ type, message, timestamp });
};

// Event handlers for ChatInterface events
const onMessageSent = (message: string): void => {
    console.log("Message sent:", message);
    addInteraction("Message Sent", message);
    connectionStatus.value = "Sending message to backend...";
};

const onResponseReceived = (response: string): void => {
    console.log("Response received:", response);
    addInteraction("Response Received", response);
    connectionStatus.value = `Success! Received response (${response.length} characters)`;

    // Clear status after 3 seconds
    setTimeout(() => {
        connectionStatus.value = "";
    }, 3000);
};
</script>

<style>
/* Using TailwindCSS utilities instead of custom CSS as per guidelines */
</style>
