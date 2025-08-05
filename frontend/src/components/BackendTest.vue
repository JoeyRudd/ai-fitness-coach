<template>
    <!-- Backend Testing Component -->
    <div class="text-center mb-8">
        <button
            @click="testBackend"
            :disabled="loading"
            class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed"
        >
            {{ loading ? "Testing..." : "Test Backend Connection" }}
        </button>
    </div>

    <!-- Display the message from backend -->
    <div
        v-if="message"
        class="max-w-2xl mx-auto p-4 bg-white rounded-lg shadow mb-4"
    >
        <h2 class="text-lg font-semibold mb-2">Backend Response:</h2>
        <p class="text-gray-700">{{ message }}</p>
    </div>

    <!-- Display error if any -->
    <div
        v-if="error"
        class="max-w-2xl mx-auto p-4 bg-red-50 border border-red-200 rounded-lg mb-4"
    >
        <h2 class="text-lg font-semibold text-red-700 mb-2">Error:</h2>
        <p class="text-red-600">{{ error }}</p>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import axios from "axios";

// Reactive state
const message = ref<string>("");
const error = ref<string>("");
const loading = ref<boolean>(false);

// Function to test backend connection
const testBackend = async (): Promise<void> => {
    loading.value = true;
    error.value = "";
    message.value = "";

    try {
        // Call the backend's root endpoint
        const response = await axios.get("http://localhost:8000/");
        message.value = response.data.message || response.data;
    } catch (err: any) {
        console.error("Error calling backend:", err);
        error.value = `Failed to connect to backend: ${err.message}`;
    } finally {
        loading.value = false;
    }
};
</script>
