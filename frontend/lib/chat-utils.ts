import type { Message } from './chat-types';

/**
 * Consolidates consecutive assistant messages into single cards
 * Merges thinking messages and combines tool calls
 */
export function consolidateMessages(msgs: Message[]): Message[] {
  const consolidated: Message[] = [];
  let currentAssistantGroup: Message | null = null;

  // Event types that should be consolidated into assistant messages
  const assistantEventTypes = [
    'thinking',
    'tool_started',
    'tool_completed',
    'planner_complete',
    'builder_complete',
    'validator_complete'
  ];

  // Event types that should be filtered out (wrapper events with no content)
  const filterOutEvents = ['started', 'completed'];

  for (const msg of msgs) {
    // Handle user messages - always push and close any assistant group
    if (msg.role === 'user') {
      if (currentAssistantGroup) {
        consolidated.push(currentAssistantGroup);
        currentAssistantGroup = null;
      }
      consolidated.push(msg);
      continue;
    }

    // Handle assistant messages
    if (msg.role === 'assistant') {
      // Skip wrapper events with no real content
      if (msg.event_type && filterOutEvents.includes(msg.event_type)) {
        continue;
      }

      // Check if this should be consolidated
      if (!msg.event_type || assistantEventTypes.includes(msg.event_type)) {
        if (currentAssistantGroup) {
          // Append to current group
          if (msg.content && msg.content.trim()) {
            currentAssistantGroup.content += '\n' + msg.content;
          }
          // Merge tool_calls if they exist
          if (msg.tool_calls && msg.tool_calls.length > 0) {
            if (!currentAssistantGroup.tool_calls) {
              currentAssistantGroup.tool_calls = [];
            }
            currentAssistantGroup.tool_calls.push(...msg.tool_calls);
          }
        } else {
          // Start new assistant group
          currentAssistantGroup = { 
            ...msg,
            event_type: 'thinking' // Normalize event type for display
          };
        }
      } else {
        // Other assistant message types (errors, etc.) - push separately
        if (currentAssistantGroup) {
          consolidated.push(currentAssistantGroup);
          currentAssistantGroup = null;
        }
        consolidated.push(msg);
      }
    }
  }

  // Don't forget the last group if it exists
  if (currentAssistantGroup) {
    consolidated.push(currentAssistantGroup);
  }

  return consolidated;
}

/**
 * Gets all tool calls from message history
 */
export function getAllToolCalls(messages: Message[]) {
  const allTools: Array<{
    name: string;
    status: 'success' | 'error' | 'running';
    output?: string;
  }> = [];
  
  messages.forEach(msg => {
    if (msg.tool_calls && msg.tool_calls.length > 0) {
      allTools.push(...msg.tool_calls);
    }
  });
  
  return allTools;
}
