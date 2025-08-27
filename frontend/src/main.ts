import { createApp } from 'vue'
import './style.css'
import App from './App.vue'

// Add error boundary for Vue app
const app = createApp(App)

// Global error handler
app.config.errorHandler = (err, instance, info) => {
  console.error('Vue Error:', err, info)
  // Ensure the app still renders even if there are errors
}

// Global warn handler
app.config.warnHandler = (msg, instance, trace) => {
  console.warn('Vue Warning:', msg, trace)
}

app.mount('#app')

// Register service worker with better error handling
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    // Add timeout to prevent hanging
    const timeout = setTimeout(() => {
      console.warn('Service Worker registration timed out')
    }, 5000)

    navigator.serviceWorker.register('/sw.js')
      .then((registration) => {
        clearTimeout(timeout)
        console.log('Service Worker registered:', registration)
      })
      .catch((error) => {
        clearTimeout(timeout)
        console.log('Service Worker registration failed:', error)
        // Don't let service worker errors break the app
      })
  })
}

// Add iOS Safari specific fixes
if (/iPad|iPhone|iPod/.test(navigator.userAgent)) {
  // Fix for iOS Safari viewport issues
  const fixIOSViewport = () => {
    const viewport = document.querySelector('meta[name="viewport"]')
    if (viewport) {
      viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0, viewport-fit=cover')
    }
  }
  
  // Apply fix on load and orientation change
  window.addEventListener('load', fixIOSViewport)
  window.addEventListener('orientationchange', fixIOSViewport)
  
  // Prevent iOS Safari from hiding the address bar
  window.addEventListener('scroll', () => {
    if (document.documentElement.scrollTop === 0) {
      window.scrollTo(0, 1)
    }
  })
  
  // Additional zoom prevention for iOS Safari
  const preventZoom = () => {
    // Force viewport scale to 1.0 when inputs are focused
    const viewport = document.querySelector('meta[name="viewport"]')
    if (viewport) {
      viewport.setAttribute('content', 'width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=0, viewport-fit=cover')
    }
  }
  
  // Apply zoom prevention on input focus
  document.addEventListener('focusin', (e) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      preventZoom()
    }
  })
  
  // Apply zoom prevention on input blur
  document.addEventListener('focusout', (e) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
      preventZoom()
    }
  })
  
  // Prevent zoom on touch events
  let lastTouchEnd = 0
  document.addEventListener('touchend', (e) => {
    const now = Date.now()
    if (now - lastTouchEnd <= 300) {
      e.preventDefault()
    }
    lastTouchEnd = now
  }, false)
}
