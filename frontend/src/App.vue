<template>
    <div class="min-h-screen bg-gray-50">
        <div class="container mx-auto px-4 py-8">
            <h1 class="text-4xl font-bold text-center text-gray-800 mb-8">
                AI Fitness Coach
            </h1>

            <!-- Backend Test Component -->
            <BackendTest />
        </div>
    </div>
</template>

<script setup lang="ts">
import BackendTest from "./components/BackendTest.vue";
</script>

<style>
/* Using TailwindCSS utilities instead of custom CSS as per guidelines */
</style>
