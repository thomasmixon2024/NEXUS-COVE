// Type contract for Nexus Cove Enhancement Plugin
// This plugin doesn't maintain complex state, so we can keep this simple

interface PluginState {
  // No persistent state needed for this basic enhancement
  // Could be extended to track agent counts, health metrics, etc.
}

declare const state: PluginState;
export { state };