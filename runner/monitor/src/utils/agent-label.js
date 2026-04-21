/**
 * Resolve the user-facing label for an agent.
 * Priority: user-configured displayName > role from frontmatter > capitalized internal name.
 */
export function agentLabel(agent) {
  if (!agent) return '';
  if (agent.displayName) return agent.displayName;
  if (agent.role) return agent.role;
  const name = agent.name || '';
  return name ? name[0].toUpperCase() + name.slice(1) : '';
}

/**
 * Resolve a label given just the internal name string.
 * Used when only the name (not the full agent object) is in scope.
 */
export function agentLabelByName(name, agentsList = []) {
  if (!name) return '';
  const found = Array.isArray(agentsList) ? agentsList.find(a => a.name === name) : null;
  if (found) return agentLabel(found);
  return name[0].toUpperCase() + name.slice(1);
}
