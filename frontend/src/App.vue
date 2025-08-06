<template>
    <div class="min-h-screen bg-gray-50">
        <div class="container mx-auto px-4 py-8 max-w-4xl">
            <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">
                AI Fitness Coach
            </h1>

            <!-- Main Chat Interface -->
            <ChatInterface
                api-endpoint="http://localhost:8000/chat"
                input-label="Ask your fitness question:"
                placeholder="e.g., Create a workout plan for beginners, help me plan my meals, or ask about exercises..."
                send-button-text="Get Fitness Advice"
                loading-text="Thinking..."
                loading-message="Getting your personalized fitness advice..."
                response-title="AI Fitness Coach Response:"
                :textarea-rows="4"
                :max-length="1000"
                :show-clear-button="true"
                :enable-mock-response="true"
                @message-sent="onMessageSent"
                @response-received="onResponseReceived"
                @error="onError"
            />

            <!-- Connection Status -->
            <div
                v-if="connectionStatus"
                class="mt-4 p-3 rounded-lg text-sm"
                :class="connectionStatusClass"
            >
                {{ connectionStatus }}
            </div>

            <!-- Backend Test Component -->
            <details class="mt-8 pt-8 border-t border-gray-200">
                <summary
                    class="text-lg font-semibold text-gray-700 mb-4 cursor-pointer hover:text-gray-900"
                >
                    Backend Connection Test (Click to expand)
                </summary>
                <div class="mt-4">
                    <BackendTest />
                </div>
            </details>

            <!-- Interaction History -->
            <div v-if="interactionHistory.length > 0" class="mt-6">
                <h3 class="text-lg font-semibold text-gray-700 mb-3">
                    Recent Interactions
                </h3>
                <div class="space-y-2 max-h-40 overflow-y-auto">
                    <div
                        v-for="(interaction, index) in interactionHistory.slice(
                            -3,
                        )"
                        :key="index"
                        class="p-3 bg-gray-50 rounded-lg text-sm"
                    >
                        <div class="font-medium text-gray-700">
                            {{ interaction.type }}:
                        </div>
                        <div class="text-gray-600 truncate">
                            {{ interaction.message }}
                        </div>
                        <div class="text-xs text-gray-500">
                            {{ interaction.timestamp }}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import ChatInterface from "./components/ChatInterface.vue";
import BackendTest from "./components/BackendTest.vue";

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
        return "bg-red-50 border border-red-200 text-red-700";
    } else if (connectionStatus.value.includes("Success")) {
        return "bg-green-50 border border-green-200 text-green-700";
    } else {
        return "bg-blue-50 border border-blue-200 text-blue-700";
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

const onError = (error: string): void => {
    console.error("Chat error:", error);
    addInteraction("Error", error);
    connectionStatus.value = `Error: ${error}`;
};
</script>

<style>
/* Using TailwindCSS utilities instead of custom CSS as per guidelines */
</style>
