/**
 * Agent 状态管理 Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Agent, AgentCategory } from '@/types';

interface AgentState {
  agents: Agent[];
  activeAgent: string;
  searchQuery: string;
  selectedCategory: AgentCategory | 'all';

  // Actions
  setAgents: (agents: Agent[]) => void;
  setActiveAgent: (agentId: string) => void;
  returnToConductor: () => void;
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: AgentCategory | 'all') => void;

  // Getters
  getActiveAgent: () => Agent | undefined;
  getFilteredAgents: () => Agent[];
}

export const useAgentStore = create<AgentState>()(
  devtools(
    (set, get) => ({
      // Initial state — 默认自动编排，不强制先选专家
      agents: [],
      activeAgent: 'auto',
      searchQuery: '',
      selectedCategory: 'all',

      // Actions
      setAgents: (agents) =>
        set((state) => {
          const currentActive = state.activeAgent;
          const hasActive =
            currentActive === 'auto' ||
            currentActive === 'juben_conductor' ||
            agents.some((a) => a.id === currentActive);
          return {
            agents,
            activeAgent: hasActive ? currentActive : 'auto',
          };
        }),
      setActiveAgent: (agentId) => set({ activeAgent: agentId }),
      returnToConductor: () => set({ activeAgent: 'auto' }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setSelectedCategory: (category) => set({ selectedCategory: category }),

      // Getters
      getActiveAgent: () => {
        const state = get();
        if (state.activeAgent === 'auto') {
          return (
            state.agents.find((a) => a.id === 'auto') ||
            state.agents.find((a) => a.id === 'juben_conductor') || {
              id: 'auto',
              name: 'JubenConductor',
              displayName: '自动编排',
              description: '按需组合调用专家',
              category: 'orchestration' as AgentCategory,
              icon: '🧭',
              model: '',
              apiEndpoint: '/juben/chat',
              features: [],
              capabilities: [],
              inputExample: '',
              outputExample: '',
              status: 'active' as const,
            }
          );
        }
        return state.agents.find((a) => a.id === state.activeAgent);
      },

      getFilteredAgents: () => {
        const state = get();
        let filtered = state.agents;

        // Filter by category
        if (state.selectedCategory !== 'all') {
          filtered = filtered.filter((a) => a.category === state.selectedCategory);
        }

        // Filter by search query
        if (state.searchQuery) {
          const query = state.searchQuery.toLowerCase();
          filtered = filtered.filter(
            (a) =>
              a.name.toLowerCase().includes(query) ||
              a.displayName.toLowerCase().includes(query) ||
              a.description.toLowerCase().includes(query)
          );
        }

        return filtered;
      },
    }),
    { name: 'AgentStore' }
  )
);
