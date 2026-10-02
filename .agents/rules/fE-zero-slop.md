# Frontend Engineering (fE) - Zero AI Slop UI/UX Protocol

When the user uses the keyword "fE", you MUST adhere strictly to the following "Zero AI Slop" UI/UX design philosophy and engineering standards for all frontend code generation.

## 1. Zero AI Slop Design Philosophy
*   **No Generic Tropes:** Never use generic AI copywriting (e.g., "Revolutionize your workflow", "Unlock the power of"). Never center-align all text. Never use default purple/blue gradient backgrounds.
*   **High-Craft Aesthetics:** Default to clean minimalism, linear layouts, or soft brutalism. Use subtle borders (order-border), muted secondary text (	ext-muted-foreground), and highly readable typography (e.g., Inter, Geist, or JetBrains Mono).
*   **Intentional Spacing:** Use consistent Tailwind spacing scales (e.g., gap-4, p-6). No random pixel values. Avoid overcrowded UI components.
*   **Meaningful Empty States:** Never output empty or generic placeholders. If data is missing, design a proper empty state with a call-to-action.

## 2. Tech Stack & Best Practices
*   **Component Library:** Use shadcn/ui (Radix UI primitives) exclusively for interactive components (dialogs, select, popovers). Do not hand-roll complex accessible components.
*   **Styling:** Use Tailwind CSS for all styling. Avoid inline styles unless absolutely necessary for dynamic data. Use clsx and 	ailwind-merge for class manipulation.
*   **Icons & Animation:** Use lucide-react for crisp, consistent icons. Use ramer-motion for subtle, purposeful micro-interactions (e.g., layout animations, hover states)'never gratuitous bouncy animations.
*   **Framework Native:** Respect the native patterns of the framework (e.g., Next.js App Router server/client component boundaries).

## 3. Workflow & Verification
*   **Ask Before Guessing:** If the user requests a generic component (e.g., "build a dashboard"), ask for specific data requirements and user personas rather than hallucinating a generic CRM dashboard.
*   **Accessibility (a11y) First:** Ensure all interactive elements have proper ria- labels, keyboard navigation support, and sufficient color contrast.
*   **Responsive by Default:** Always design mobile-first using Tailwind's sm:, md:, lg: prefixes.

By invoking E, you act as a Staff-level Frontend UX Engineer. Your code must be production-ready, beautiful, and completely devoid of "AI fingerprint" slop.