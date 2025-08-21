<template>
    <div class="flex items-center gap-3">
      <!-- Logo Icon -->
      <div class="relative flex-shrink-0">
        <!-- Hypertrofit H with barbell plates -->
        <svg 
          viewBox="0 0 100 60" 
          class="w-12 h-12 sm:w-16 sm:h-16 text-gray-800 dark:text-white"
          xmlns="http://www.w3.org/2000/svg"
        >
          <!-- Left outer plate -->
          <rect x="0" y="18" width="6" height="24" rx="1" fill="currentColor" />
          <!-- Left inner plate -->
          <rect x="8" y="14" width="6" height="32" rx="1" fill="currentColor" />
  
          <!-- Left connector bar -->
          <rect x="14" y="26" width="10" height="8" fill="currentColor" />
  
          <!-- H verticals -->
          <rect x="24" y="8" width="10" height="44" fill="currentColor" />
          <rect x="56" y="8" width="10" height="44" fill="currentColor" />
  
          <!-- H crossbar -->
          <rect x="24" y="26" width="42" height="8" fill="currentColor" />
  
          <!-- Right connector bar -->
          <rect x="66" y="26" width="10" height="8" fill="currentColor" />
  
          <!-- Right inner plate -->
          <rect x="76" y="14" width="6" height="32" rx="1" fill="currentColor" />
          <!-- Right outer plate -->
          <rect x="84" y="18" width="6" height="24" rx="1" fill="currentColor" />
        </svg>
      </div>
      
      <!-- Text -->
      <h1 class="text-xl sm:text-2xl font-bold text-gray-800 dark:text-white">
        Hypertrofit
      </h1>
    </div>
  </template>
  
  <script setup lang="ts">
  // No props needed - uses CSS dark mode classes directly
  </script>