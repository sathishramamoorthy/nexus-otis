"use client";

import { createContext, useContext, useState, useCallback, ReactNode } from "react";

export type AgentType = "logistics_agent" | "backlog_agent";

interface AgentContextType {
  agent: AgentType;
  setAgent: (agent: AgentType) => void;
  agentLabel: string;
}

const AgentContext = createContext<AgentContextType | null>(null);

const AGENT_LABELS: Record<AgentType, string> = {
  logistics_agent: "Flight Logistics",
  backlog_agent: "Workable Backlog",
};

export function AgentProvider({ children }: { children: ReactNode }) {
  const [agent, setAgentState] = useState<AgentType>("backlog_agent");

  const setAgent = useCallback((newAgent: AgentType) => {
    setAgentState(newAgent);
  }, []);

  const agentLabel = AGENT_LABELS[agent];

  return (
    <AgentContext.Provider value={{ agent, setAgent, agentLabel }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgent(): AgentContextType {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error("useAgent must be used within an AgentProvider");
  }
  return context;
}

export { AGENT_LABELS };
