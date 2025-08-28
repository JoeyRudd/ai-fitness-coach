<template>
    <div class="flex items-center gap-2">
      <!-- Logo Icon -->
      <div class="relative flex-shrink-0">
        <!-- Hypertrofit H with simplified barbell -->
        <svg
          viewBox="0 0 48 48"
          class="w-8 h-8 sm:w-10 sm:h-10 text-gray-800 dark:text-white"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Left plates: inner ~75% of H height (24), outer ~50% (12) -->
          <rect x="9" y="12" width="6" height="24" rx="2" fill="currentColor" />
          <rect x="3" y="18" width="4" height="12" rx="2" fill="currentColor" />

          <!-- H structure -->
          <rect x="16" y="8" width="8" height="32" fill="currentColor" />
          <rect x="26" y="8" width="8" height="32" fill="currentColor" />
          <rect x="16" y="19" width="18" height="10" fill="currentColor" />

          <!-- Right plates: inner ~75% of H height (24), outer ~50% (12) -->
          <rect x="35" y="12" width="6" height="24" rx="2" fill="currentColor" />
          <rect x="43" y="18" width="4" height="12" rx="2" fill="currentColor" />
        </svg>
      </div>
      
      <!-- Text -->
      <h1 class="text-lg sm:text-xl font-bold text-gray-800 dark:text-white">
        Hypertrofit
      </h1>
    </div>
  </template>
  
  <script setup lang="ts">
  // No props needed - uses CSS dark mode classes directly
  </script>