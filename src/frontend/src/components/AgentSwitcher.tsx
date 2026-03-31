"use client";

import { useAgent, AgentType, AGENT_LABELS } from "@/lib/AgentContext";

const AGENT_OPTIONS: AgentType[] = ["logistics_agent", "backlog_agent"];

const AGENT_ICONS: Record<AgentType, string> = {
  logistics_agent: "✈️",
  backlog_agent: "📋",
};

/**
 * Agent switcher component that allows switching between different agents.
 * Switching agents will remount CopilotKit and start a new conversation.
 */
export function AgentSwitcher() {
  const { agent, setAgent } = useAgent();

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-gray-400">Agent:</span>
      <div className="flex bg-gray-700 rounded-lg p-1">
        {AGENT_OPTIONS.map((agentOption) => (
          <button
            key={agentOption}
            onClick={() => setAgent(agentOption)}
            className={`px-3 py-1 text-sm rounded-md transition-colors ${
              agent === agentOption
                ? "bg-blue-600 text-white"
                : "text-gray-300 hover:text-white hover:bg-gray-600"
            }`}
          >
            {AGENT_ICONS[agentOption]} {AGENT_LABELS[agentOption]}
          </button>
        ))}
      </div>
    </div>
  );
}
