"use client";

import { ReactNode } from "react";
import { AgentProvider, useAgent } from "@/lib/AgentContext";
import { AuthenticatedCopilotKit } from "@/components/AuthenticatedCopilotKit";
import { NoAuthCopilotKit } from "@/components/NoAuthCopilotKit";

// Check if authentication is enabled via environment variable
const isAuthEnabled = process.env.NEXT_PUBLIC_AUTH_ENABLED === "true";

/**
 * Inner component that reads the agent from context and renders CopilotKit
 * with the appropriate agent. Uses key prop to force remount when agent changes.
 */
function CopilotKitWithAgent({ children }: { children: ReactNode }) {
  const { agent } = useAgent();

  // Key forces remount when agent changes, creating a fresh CopilotKit session
  if (!isAuthEnabled) {
    return (
      <NoAuthCopilotKit key={agent} agent={agent}>
        {children}
      </NoAuthCopilotKit>
    );
  }
  return (
    <AuthenticatedCopilotKit key={agent} agent={agent}>
      {children}
    </AuthenticatedCopilotKit>
  );
}

/**
 * Wrapper that provides AgentContext and CopilotKit.
 * Agent can be switched at runtime via useAgent hook.
 */
export function AgentCopilotKitWrapper({ children }: { children: ReactNode }) {
  return (
    <AgentProvider>
      <CopilotKitWithAgent>
        {children}
      </CopilotKitWithAgent>
    </AgentProvider>
  );
}
