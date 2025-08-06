<template>
    <div class="bg-white rounded-xl shadow-xl p-8 border border-gray-100">
        <!-- Input Section -->
        <div class="mb-8">
            <label
                for="user-input"
                class="block text-sm font-semibold text-gray-700 mb-3"
            >
                {{ inputLabel }}
            </label>
            <div class="relative">
                <textarea
                    id="user-input"
                    v-model="userInput"
                    :placeholder="placeholder"
                    :rows="textareaRows"
                    :maxlength="maxLength"
                    class="w-full px-4 py-3 border-2 border-gray-200 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none transition-all duration-200 placeholder-gray-400"
                    :disabled="loading"
                    @keydown.ctrl.enter="sendMessage"
                    @keydown.meta.enter="sendMessage"
                ></textarea>
                <div class="absolute bottom-2 right-2 text-xs text-gray-400">
                    <span v-if="maxLength">{{ userInput.length }}/{{ maxLength }}</span>
                </div>
            </div>
            <div class="flex justify-between items-center mt-2">
                <p class="text-xs text-gray-500 flex items-center">
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg">⌘</kbd>
                    <span class="mx-1">+</span>
                    <kbd class="px-2 py-1 text-xs font-semibold text-gray-800 bg-gray-100 border border-gray-200 rounded-lg">Enter</kbd>
                    <span class="ml-2">to send</span>
                </p>
            </div>
        </div>

        <!-- Send Button -->
        <div class="mb-8">
            <button
                @click="sendMessage"
                :disabled="
                    loading ||
                    !userInput.trim() ||
                    (!!maxLength && userInput.length > maxLength)
                "
                class="w-full sm:w-auto px-8 py-3 bg-gradient-to-r from-blue-500 to-blue-600 text-white font-semibold rounded-lg hover:from-blue-600 hover:to-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all duration-200 shadow-lg hover:shadow-xl transform hover:-translate-y-0.5 disabled:transform-none"
            >
                <span class="flex items-center justify-center">
                    <span v-if="!loading">{{ sendButtonText }}</span>
                    <span v-else class="flex items-center">
                        <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        {{ loadingText }}
                    </span>
                </span>
            </button>
        </div>

        <!-- AI Response Section -->
        <div v-if="aiResponse || loading" class="border-t border-gray-200 pt-8">
            <h2 class="text-xl font-bold text-gray-800 mb-4 flex items-center">
                <svg class="w-6 h-6 mr-2 text-blue-500" fill="none" stroke="currentColor" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"></path>
                </svg>
                {{ responseTitle }}
            </h2>

            <!-- Loading indicator -->
            <div
                v-if="loading"
                class="flex items-center space-x-3 text-gray-600 bg-gray-50 rounded-xl p-6"
            >
                <div class="flex space-x-1">
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                    <div class="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
                </div>
                <span class="font-medium">{{ loadingMessage }}</span>
            </div>

            <!-- AI Response -->
            <div
                v-else-if="aiResponse"
                class="bg-gradient-to-br from-gray-50 to-blue-50 rounded-xl p-6 whitespace-pre-wrap text-gray-800 leading-relaxed border border-gray-100 shadow-inner"
            >
                {{ aiResponse }}
            </div>
        </div>

        <!-- Error Display -->
        <div
            v-if="error"
            class="mt-6 p-5 bg-gradient-to-r from-red-50 to-red-100 border-l-4 border-red-400 rounded-lg shadow-sm"
        >
            <div class="flex items-start">
                <svg class="w-5 h-5 text-red-400 mt-0.5 mr-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                </svg>
                <div class="flex-1">
                    <h3 class="text-sm font-semibold text-red-800 mb-1">Error:</h3>
                    <p class="text-red-700 text-sm leading-relaxed">{{ error }}</p>
                    <button
                        @click="clearError"
                        class="mt-3 text-xs text-red-800 hover:text-red-900 underline font-medium"
                    >
                        Dismiss
                    </button>
                </div>
            </div>
        </div>

        <!-- Clear Response Button -->
        <div
            v-if="aiResponse && !loading && showClearButton"
            class="mt-6 text-center"
        >
            <button
                @click="clearResponse"
                class="text-sm text-gray-500 hover:text-gray-700 underline font-medium transition-colors duration-200"
            >
                Clear Response
            </button>
        </div>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import axios from "axios";

// Props interface
interface Props {
    apiEndpoint?: string;
    inputLabel?: string;
    placeholder?: string;
    sendButtonText?: string;
    loadingText?: string;
    loadingMessage?: string;
    responseTitle?: string;
    textareaRows?: number;
    maxLength?: number;
    showClearButton?: boolean;
    enableMockResponse?: boolean;
}

// Props with default values
const props = withDefaults(defineProps<Props>(), {
    apiEndpoint: "http://localhost:8000/chat",
    inputLabel: "Ask your fitness question:",
    placeholder:
        "e.g., Create a workout plan for beginners, or suggest a healthy meal...",
    sendButtonText: "Send",
    loadingText: "Thinking...",
    loadingMessage: "Getting your personalized fitness advice...",
    responseTitle: "AI Fitness Coach Response:",
    textareaRows: 4,
    maxLength: 1000,
    showClearButton: true,
    enableMockResponse: true,
});

// Emits (for parent component communication)
const emit = defineEmits<{
    messageSent: [message: string];
    responseReceived: [response: string];
    error: [error: string];
}>();

// Reactive state
const userInput = ref<string>("");
const aiResponse = ref<string>("");
const error = ref<string>("");
const loading = ref<boolean>(false);

// Function to send message to AI
const sendMessage = async (): Promise<void> => {
    if (!userInput.value.trim()) return;
    if (props.maxLength && userInput.value.length > props.maxLength) return;

    const message = userInput.value.trim();
    loading.value = true;
    error.value = "";
    aiResponse.value = "";

    // Emit that a message was sent
    emit("messageSent", message);

    try {
        const response = await axios.post(
            props.apiEndpoint,
            {
                message: message,
            },
            {
                headers: {
                    "Content-Type": "application/json",
                },
            },
        );

        // The backend returns { "response": "You said: ..." }
        const responseText = response.data.response || "No response received";
        aiResponse.value = responseText;

        // Emit that a response was received
        emit("responseReceived", responseText);

        // Clear the input after successful send
        userInput.value = "";
    } catch (err: any) {
        console.error("Error sending message:", err);

        // More detailed error handling for debugging
        let errorMessage = "Failed to get AI response";

        if (err.response) {
            // Server responded with error status
            errorMessage = `Backend error (${err.response.status}): ${err.response.data?.detail || err.response.statusText}`;
        } else if (err.request) {
            // Request was made but no response received
            errorMessage =
                "Cannot connect to backend. Make sure the backend server is running on http://localhost:8000";
        } else {
            // Something else happened
            errorMessage = `Request error: ${err.message}`;
        }

        error.value = errorMessage;
        emit("error", errorMessage);

        // For demo purposes, show a mock response if backend isn't ready and mock is enabled
        if (
            props.enableMockResponse &&
            (err.code === "ECONNREFUSED" || err.code === "ERR_NETWORK")
        ) {
            const mockResponse = `Mock AI Response for: "${message}"\n\nThis is a placeholder response. The backend appears to be offline.\n\nTo connect to the real backend:\n1. Make sure the backend server is running\n2. Start it with: uvicorn main:app --reload\n3. Backend should be available at http://localhost:8000\n\nYour question was: ${message}`;
            aiResponse.value = mockResponse;
            emit("responseReceived", mockResponse);
            userInput.value = "";
            error.value = "";
        }
    } finally {
        loading.value = false;
    }
};

// Helper functions
const clearError = (): void => {
    error.value = "";
};

const clearResponse = (): void => {
    aiResponse.value = "";
    error.value = "";
};

// Expose methods to parent component (optional)
defineExpose({
    clearError,
    clearResponse,
    sendMessage,
});
</script>
