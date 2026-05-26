# Module 7: Frontend / Dashboard UI — Implementation Plan

## Overview

Module 7 tạo React dashboard cho pipeline 2D animation. UI gồm: project manager, story bible editor, character DNA editor, timeline/storyboard viewer, và generation control panel. Sử dụng Vite + React + TypeScript + Tailwind CSS.

## Architecture

```
apps/dashboard/
  src/
    components/     # Reusable UI components
    pages/          # Route-level pages
    hooks/          # Custom hooks (API, state)
    api/            # API client layer
    store/          # Zustand stores
    types/          # Shared TypeScript types
  index.html
  package.json
  vite.config.ts
  tailwind.config.ts
```

---

## Step 7.1 — Project Scaffold

```bash
npm create vite@latest apps/dashboard -- --template react-ts
cd apps/dashboard
npm install zustand react-router-dom@7 @tanstack/react-query
npm install -D tailwindcss @tailwindcss/vite lucide-react
```

Configure Tailwind, Vite proxy to API backend (`localhost:8000`).

---

## Step 7.2 — Type Definitions

**File:** `apps/dashboard/src/types/index.ts` (NEW)

Port shared Pydantic schemas to TypeScript interfaces:
- `Project`, `Scene`, `Shot`, `Character`, `Asset`
- `StoryBible`, `Episode`, `StoryArc`
- `CameraConfig`, `MotionConfig`, `AudioConfig`
- `ApiResponse<T>`

---

## Step 7.3 — API Client

**File:** `apps/dashboard/src/api/client.ts` (NEW)

- `api.get<T>(url)`, `api.post<T>(url, data)`, `api.patch`, `api.delete`
- Base URL from env `VITE_API_URL` or proxy `/api/v1`
- Auto JSON parse, error handling

**File:** `apps/dashboard/src/api/endpoints.ts` (NEW)
- Typed endpoint functions: `getProjects()`, `createShot()`, `generateKeyframe()`, etc.

---

## Step 7.4 — Store (Zustand)

**Files:**
- `apps/dashboard/src/store/projectStore.ts` — active project, projects list
- `apps/dashboard/src/store/sceneStore.ts` — scenes, shots per scene
- `apps/dashboard/src/store/uiStore.ts` — sidebar, modals, alerts

---

## Step 7.5 — Layout & Routing

**Files:**
- `apps/dashboard/src/App.tsx` — React Router setup
- `apps/dashboard/src/components/Layout.tsx` — sidebar nav + header
- `apps/dashboard/src/components/Sidebar.tsx` — project switcher, nav links

**Routes:**
- `/` — Project list / dashboard home
- `/projects/:id` — Project detail
- `/projects/:id/story` — Story bible editor
- `/projects/:id/characters` — Character list
- `/projects/:id/characters/:cid` — Character DNA editor
- `/projects/:id/timeline` — Timeline + storyboard
- `/projects/:id/scenes/:sid` — Scene detail + shot editor
- `/projects/:id/export` — Export/download panel

---

## Step 7.6 — Pages

### Project Manager (`/`)
- Grid/list of projects with create/delete actions
- Style badge, aspect ratio, episode count

### Story Bible Editor (`/projects/:id/story`)
- Structured form for series overview, episodic breakdown
- Character relationship visualization
- "Regenerate" and "Materialize" buttons with loading states

### Character DNA Editor (`/projects/:id/characters/:cid`)
- Visual trait editor (sliders, color pickers)
- Reference image upload + crop
- Body type, outfit, expression variations
- Prompt preview

### Timeline / Storyboard (`/projects/:id/timeline`)
- Horizontal timeline with scene blocks × shot cards
- Drag-drop reorder
- Shot detail popover: camera, motion, audio config
- Generation status badges per shot
- "Generate All" buttons per scene

### Shot Editor (`/projects/:id/scenes/:sid`)
- Shot list with editable fields
- Single-click actions: generate background, generate keyframe, generate audio

### Export Panel (`/projects/:id/export`)
- Progress per scene: background ✓, keyframes ✓, audio ✓
- Export button → download `.mp4`

---

## Step 7.7 — Generation Controls

**Component:** `GenerationPanel`
- Shows current generation status for a shot (background, keyframe, audio)
- One-click generate with loading spinner
- Error display with retry

**Component:** `GenerateAllBar`
- Floating action bar for scene: "Generate All Backgrounds", "Generate All Keyframes", "Generate All Audio"
- Progress counter (3/5 completed)

---

## Step 7.8 — TanStack Query Integration

- `useQuery` for all list/get endpoints (auto-refetch)
- `useMutation` for create/update/delete with optimistic updates
- Invalidation on mutations

---

## Files Summary

| File | Action |
|------|--------|
| `apps/dashboard/package.json` | NEW |
| `apps/dashboard/vite.config.ts` | NEW |
| `apps/dashboard/tailwind.config.ts` | NEW |
| `apps/dashboard/src/types/index.ts` | NEW |
| `apps/dashboard/src/api/client.ts` | NEW |
| `apps/dashboard/src/api/endpoints.ts` | NEW |
| `apps/dashboard/src/store/projectStore.ts` | NEW |
| `apps/dashboard/src/store/sceneStore.ts` | NEW |
| `apps/dashboard/src/store/uiStore.ts` | NEW |
| `apps/dashboard/src/App.tsx` | NEW |
| `apps/dashboard/src/components/Layout.tsx` | NEW |
| `apps/dashboard/src/components/Sidebar.tsx` | NEW |
| `apps/dashboard/src/pages/ProjectList.tsx` | NEW |
| `apps/dashboard/src/pages/StoryEditor.tsx` | NEW |
| `apps/dashboard/src/pages/CharacterList.tsx` | NEW |
| `apps/dashboard/src/pages/CharacterEditor.tsx` | NEW |
| `apps/dashboard/src/pages/Timeline.tsx` | NEW |
| `apps/dashboard/src/pages/ShotEditor.tsx` | NEW |
| `apps/dashboard/src/pages/ExportPanel.tsx` | NEW |
| `apps/dashboard/src/components/GenerationPanel.tsx` | NEW |

---

## Deliverables Checkpoint

```text
□ Vite + React + TypeScript + Tailwind scaffold
□ Shared TypeScript types (mirrored from shared lib)
□ Typed API client + endpoints
□ Zustand stores (project, scene, UI)
□ Layout with sidebar navigation
□ 7 route-level pages
□ Generation control components
□ TanStack Query data fetching
```

---

## Next: Module 8 — Pipeline Orchestration

Job queue, Celery/Redis workers, batch generation across all scenes/episodes, progress tracking, error recovery.
