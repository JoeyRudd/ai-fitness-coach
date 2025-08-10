<template>
    <!-- Backend Testing Component -->
    <div class="text-center mb-8">
        <button
            @click="testBackend"
            :disabled="loading"
            class="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg"
        >
            {{ loading ? "Testing..." : "Test Backend Connection" }}
        </button>
    </div>

    <!-- Display the message from backend -->
    <div
        v-if="message"
        class="max-w-2xl mx-auto p-4 rounded-lg shadow mb-4 bg-white/80 border border-gray-200 text-gray-800 dark:bg-neutral-900/80 dark:border-neutral-800 dark:text-gray-100"
    >
        <h2 class="text-lg font-semibold mb-2">Backend Response:</h2>
        <p class="text-gray-700 dark:text-gray-300">{{ message }}</p>
    </div>

    <!-- Display error if any -->
    <div
        v-if="error"
        class="max-w-2xl mx-auto p-4 rounded-lg mb-4 bg-red-50 border border-red-200 text-red-700 dark:bg-red-950/60 dark:border-red-900 dark:text-red-300"
    >
        <h2 class="text-lg font-semibold mb-2">Error:</h2>
        <p>{{ error }}</p>
    </div>
</template>

<script setup lang="ts">
import { ref } from "vue";
import axios from "axios";

// Reactive state
const message = ref<string>("");
const error = ref<string>("");
const loading = ref<boolean>(false);

const API_BASE = (import.meta.env.VITE_API_BASE as string | undefined) || '/api/v1';

// Function to test backend connection
const testBackend = async (): Promise<void> => {
    loading.value = true;
    error.value = "";
    message.value = "";

    try {
        // Proper chat POST (backend only defines POST for /chat)
        const base = API_BASE.replace(/\/$/, '');
        const response = await axios.post(`${base}/chat`, { history: [], message: 'test connection' }, { headers: { 'Content-Type': 'application/json' } });
        if (response.data && response.data.response) {
            message.value = `OK (chars: ${response.data.response.length})`;
        } else {
            message.value = 'Received response but unexpected shape';
        }
    } catch (err: any) {
        console.error('Error calling backend chat:', err?.response || err);
        if (err?.response) {
            error.value = `Failed: ${err.response.status} ${err.response.statusText}`;
        } else {
            error.value = `Failed: ${err.message}`;
        }
    } finally {
        loading.value = false;
    }
};
</script>

<style scoped>
</style>
