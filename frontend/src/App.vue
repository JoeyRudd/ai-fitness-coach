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

        <div class="container mx-auto px-4 py-8 max-w-4xl">
            <h1 class="text-4xl font-bold text-center text-gray-800 dark:text-gray-100 mb-8">
                AI Fitness Coach
            </h1>

            <!-- Main Chat Interface -->
            <ChatInterface
                api-endpoint="http://localhost:8000/api/v1/chat2"
                input-label="Ask your fitness question:"
                placeholder="e.g., Create a workout plan for beginners, help me plan my meals, or ask about exercises..."
                send-button-text="Get Fitness Advice"
                :textarea-rows="4"
                :max-length="1000"
                @message-sent="onMessageSent"
                @response-received="onResponseReceived"
            />

            <!-- Connection Status -->
            <div
                v-if="connectionStatus"
                class="mt-4 p-3 rounded-lg text-sm border"
                :class="connectionStatusClass"
            >
                {{ connectionStatus }}
            </div>

            <!-- Backend Test Component -->
            <details class="mt-8 pt-8 border-t border-gray-200 dark:border-neutral-800">
                <summary
                    class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-4 cursor-pointer hover:text-gray-900 dark:hover:text-white"
                >
                    Backend Connection Test (Click to expand)
                </summary>
                <div class="mt-4">
                    <BackendTest />
                </div>
            </details>

            <!-- Interaction History -->
            <div v-if="interactionHistory.length > 0" class="mt-6">
                <h3 class="text-lg font-semibold text-gray-700 dark:text-gray-200 mb-3">
                    Recent Interactions
                </h3>
                <div class="space-y-2 max-h-40 overflow-y-auto">
                    <div
                        v-for="(interaction, index) in interactionHistory.slice(
                            -3,
                        )"
                        :key="index"
                        class="p-3 rounded-lg text-sm bg-gray-50 text-gray-700 border border-gray-200 dark:bg-neutral-900 dark:text-gray-200 dark:border-neutral-800"
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
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import ChatInterface from "./components/ChatInterface.vue";
import BackendTest from "./components/BackendTest.vue";

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
