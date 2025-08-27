/// <reference types="vite/client" />

// Provide typing for importing .vue Single File Components
declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
