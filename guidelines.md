# Project Guidelines for GitHub Copilot: AI Fitness Coach

This document provides context and rules for generating code for the AI Fitness Coach project. Please adhere to these guidelines to ensure consistency, maintainability, and alignment with the project's goals.

## 1. Project Overview & Goal

-   **Product:** A simple, user-friendly AI-powered fitness and nutrition coach application.
-   **Target User:** A 45-year-old beginner (the developer's dad). The language and suggestions must be simple, encouraging, and safe.
-   **Core Technology:** The application uses a Retrieval-Augmented Generation (RAG) pipeline. The AI's knowledge is grounded in a local `knowledge_base/` directory containing custom Markdown files.
-   **Core Principle:** Keep it simple and cheap/free to run. Avoid suggesting complex solutions or paid cloud services beyond the specified tech stack.

## 2. The AI Coach Persona

When generating prompts or any user-facing text, the AI Coach must be:

-   **Friendly and Encouraging:** Use positive language. Avoid judgmental or overly technical terms.
-   **Simple and Clear:** Explain concepts in plain English. For example, instead of "caloric deficit," say "burning slightly more calories than you eat."
-   **Safety-First:** Always prioritize safety. Suggest consulting a doctor before starting a new routine. Recommend starting with light weights and simple exercises.
-   **Action-Oriented:** Provide clear, actionable steps.

## 3. Tech Stack

Adhere strictly to the following technologies. Do not introduce new frameworks or libraries without explicit instruction.

### Backend (Python)

-   **Framework:** `FastAPI`
-   **AI Generation:** `transformers` library using the `microsoft/phi-3-mini-4k-instruct` model.
-   **RAG Retrieval:**
    -   `sentence-transformers` for creating text embeddings (specifically the `all-MiniLM-L6-v2` model).
    -   `faiss-cpu` for in-memory vector search.
-   **Dependencies:** Manage with `requirements.txt`.
-   **Hosting:** The target is Fly.io or Railway (implying a containerized environment).

### Frontend (JavaScript/Vue)

-   **Framework:** `Vue 3` with the Composition API (`<script setup>`).
-   **Build Tool:** `Vite`
-   **Styling:** `TailwindCSS` (utility-first approach). Do not write custom CSS files unless absolutely necessary.
-   **API Calls:** Use `axios` for all communication with the backend.
-   **Hosting:** The target is Vercel or Netlify (implying a static site build).

## 4. Coding Conventions & Style

### Python (Backend)

-   **Type Hinting:** All function definitions and Pydantic models **must** include type hints.
-   **Pydantic:** Use Pydantic's `BaseModel` for all API request and response data structures.
-   **Async:** Use `async def` for FastAPI path operations where appropriate, although synchronous is acceptable for the CPU-bound ML tasks in this project.
-   **Formatting:** Follow PEP 8 guidelines. Use f-strings for string formatting.
-   **RAG Logic:** The RAG pipeline in `main.py` follows this order:
    1.  Receive user query.
    2.  Encode query to a vector using `retriever`.
    3.  Search the `faiss` index to get relevant document indices.
    4.  Construct an augmented prompt with persona, context, and the user query.
    5.  Send the prompt to the `generator` pipeline.
    6.  Parse the `generated_text` to extract the final answer.

### Vue (Frontend)

-   **Composition API:** Always use `<script setup>` syntax for components.
-   **State Management:** Use `ref` for primitive reactive values and `reactive` for objects.
-   **Component Structure:** Keep components small and focused on a single responsibility.
-   **TailwindCSS:** Apply utilities directly in the `<template>` block. Use `@apply` in CSS sparingly.
-   **API Calls:** Wrap `axios` calls in `async` functions within the script setup. Always include `try...catch` blocks for error handling and update a `loading` state variable.

## 5. What to Avoid

-   **Complex Jargon:** Do not use advanced fitness or nutrition terminology in user-facing text.
-   **Paid Services:** Do not suggest using AWS SageMaker, Google Vertex AI, OpenAI APIs, or any other paid service. The project is designed to run on free tiers.
-   **Over-Engineering:** Do not suggest complex state management libraries (like Pinia or Vuex) for the frontend unless the app's complexity grows significantly. A simple `ref` is often enough.
-   **Hardcoding:** Never hardcode URLs or sensitive information. Use environment variables for configuration where appropriate (e.g., the backend API URL in the frontend).

By following these guidelines, you will help create a focused, consistent, and high-quality application.
