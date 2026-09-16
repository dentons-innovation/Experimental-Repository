# Frontend Architecture Rules (React & TypeScript)

- **Server State Management**:
  - Use TanStack Query (`@tanstack/react-query`) for all remote data fetching and mutations. Do not use standalone `useEffect` hooks for API data fetching.
  - Standardize query keys using the centralized definitions in `src/api/queryKeys.ts`.
  - Place API communication logic in `src/api/fetchers.ts` via the configured client.
- **Type Safety**:
  - Enforce strict TypeScript types. Prohibit `any`, `unknown` casts without guards, or `@ts-ignore` on domain models and API responses; leverage schemas defined in `src/types/index.ts`.
- **Component Architecture**:
  - Keep components modular and focused on presentation. Extract multi-step mutation logic, complex local states, and side effects into custom hooks.
- **Error & Loading States**:
  - Explicitly handle loading and error states for asynchronous actions, presenting accessible UI feedback or toast notifications.
- **Linter Deference**:
  - Defer formatting and syntax rules to ESLint and Prettier; prioritize state consistency, hook dependency correctness, and type safety.
