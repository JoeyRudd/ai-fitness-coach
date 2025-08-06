<template>
    <div class="min-h-screen bg-gray-50">
        <div class="container mx-auto px-4 py-8 max-w-4xl">
            <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">
                AI Fitness Coach
            </h1>

            <!-- Main Chat Interface with Props -->
            <ChatInterface
                api-endpoint="http://localhost:8000/chat"
                input-label="Ask your fitness question:"
                placeholder="e.g., Create a workout plan for beginners, or suggest a healthy meal..."
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

            <!-- Backend Test Component (can be removed later) -->
            <div class="mt-8 pt-8 border-t border-gray-200">
                <h2 class="text-lg font-semibold text-gray-700 mb-4">
                    Backend Connection Test
                </h2>
                <BackendTest />
            </div>

            <!-- Optional: Display last interaction info -->
            <div v-if="lastMessage" class="mt-6 p-4 bg-blue-50 rounded-lg">
                <h3 class="text-sm font-medium text-blue-700 mb-2">
                    Last Interaction:
                </h3>
                <p class="text-blue-600 text-sm">{{ lastMessage }}</p>
            </div>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import ChatInterface from "./components/ChatInterface.vue";
import BackendTest from "./components/BackendTest.vue";

// State to track interactions (optional)
const lastMessage = ref<string>("");

// Event handlers for ChatInterface events
const onMessageSent = (message: string): void => {
    console.log("Message sent:", message);
    lastMessage.value = `Sent: ${message}`;
};

const onResponseReceived = (response: string): void => {
    console.log("Response received:", response);
    lastMessage.value = `Received response (${response.length} characters)`;
};

const onError = (error: string): void => {
    console.error("Chat error:", error);
    lastMessage.value = `Error: ${error}`;
};
</script>

<style>
/* Using TailwindCSS utilities instead of custom CSS as per guidelines */
</style>
