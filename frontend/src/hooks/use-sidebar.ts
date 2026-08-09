"use client";

import { create } from "zustand";

/**
 * Shared open/close state for the mobile sidebar drawer.
 *
 * The header renders the "hamburger" trigger and the sidebar renders the
 * drawer itself; they live in different subtrees of the layout, so a tiny
 * Zustand store is the simplest way to keep them in sync without threading
 * props (or reaching for React Context for something this trivial).
 */
interface SidebarState {
  isOpen: boolean;
  open: () => void;
  close: () => void;
  toggle: () => void;
}

export const useSidebarStore = create<SidebarState>((set) => ({
  isOpen: false,
  open: () => set({ isOpen: true }),
  close: () => set({ isOpen: false }),
  toggle: () => set((s) => ({ isOpen: !s.isOpen })),
}));
