<template>
    <div class="bg-white rounded-lg shadow-lg p-6">
        <!-- Input Section -->
        <div class="mb-6">
            <label
                for="user-input"
                class="block text-sm font-medium text-gray-700 mb-2"
            >
                {{ inputLabel }}
            </label>
            <textarea
                id="user-input"
                v-model="userInput"
                :placeholder="placeholder"
                :rows="textareaRows"
                :maxlength="maxLength"
                class="w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 resize-none"
                :disabled="loading"
                @keydown.ctrl.enter="sendMessage"
                @keydown.meta.enter="sendMessage"
            ></textarea>
            <div class="flex justify-between items-center mt-1">
                <p class="text-xs text-gray-500">
                    Press Ctrl+Enter (Cmd+Enter on Mac) to send
                </p>
                <p v-if="maxLength" class="text-xs text-gray-500">
                    {{ userInput.length }}/{{ maxLength }}
                </p>
            </div>
        </div>

        <!-- Send Button -->
        <div class="mb-6">
            <button
                @click="sendMessage"
                :disabled="
                    loading ||
                    !userInput.trim() ||
                    (maxLength && userInput.length > maxLength)
                "
                class="w-full sm:w-auto px-6 py-3 bg-blue-500 text-white font-medium rounded-lg hover:bg-blue-600 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors duration-200"
            >
                {{ loading ? loadingText : sendButtonText }}
            </button>
        </div>

        <!-- AI Response Section -->
        <div v-if="aiResponse || loading" class="border-t pt-6">
            <h2 class="text-lg font-semibold text-gray-800 mb-3">
                {{ responseTitle }}
            </h2>

            <!-- Loading indicator -->
            <div
                v-if="loading"
                class="flex items-center space-x-2 text-gray-600"
            >
                <div
                    class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-500"
                ></div>
                <span>{{ loadingMessage }}</span>
            </div>

            <!-- AI Response -->
            <div
                v-else-if="aiResponse"
                class="bg-gray-50 rounded-lg p-4 whitespace-pre-wrap text-gray-800 leading-relaxed"
            >
                {{ aiResponse }}
            </div>
        </div>

        <!-- Error Display -->
        <div
            v-if="error"
            class="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg"
        >
            <h3 class="text-sm font-medium text-red-700 mb-1">Error:</h3>
            <p class="text-red-600 text-sm">{{ error }}</p>
            <button
                @click="clearError"
                class="mt-2 text-xs text-red-700 hover:text-red-800 underline"
            >
                Dismiss
            </button>
        </div>

        <!-- Clear Response Button -->
        <div
            v-if="aiResponse && !loading && showClearButton"
            class="mt-4 text-center"
        >
            <button
                @click="clearResponse"
                class="text-sm text-gray-600 hover:text-gray-800 underline"
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
