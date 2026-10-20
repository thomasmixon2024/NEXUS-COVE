# NEXUS-COVE Enhanced Agent Invocations (Situational Awareness Edition)

This directory contains enhanced agent invocation patterns designed to provide **situational awareness** when working with language models in the NEXUS-COVE repository. These invocations help reduce looping and improve context-awareness while maintaining the personalized nature you requested.

## 🔑 **Key Improvements Over Basic Prompts**

These enhanced invocations address the common problems with static prompts:
- ✅ **Memory Awareness**: Reference to using recent conversation context
- ✅ **Situational Awareness**: Guidelines for connecting analysis to current activity
- ✅ **Reduced Looping**: Structured approaches that build on context rather than repeat
- ✅ **Enhanced Personalities**: Integration of the actual NEXUS-COVE agent temperaments
- ✅ **Better Context Tracking**: Methods for linking analysis to recent exchanges

## 📋 **Available Enhanced Invocations**

1. **Nexus Architect** (`agent-invocations/nexus-architect/AGENT.md`)
   - Role: Architecture planner with situational awareness
   - Enhancements: Memory-integrated reasoning, context-aware analysis, boundary consciousness
   - Best for: Architectural decisions that benefit from understanding recent discussions

2. **Nexus Debug** (`agent-invocations/nexus-debug/AGENT.md`)
   - Role: Debugging specialist with situational awareness  
   - Enhancements: Memory-integrated investigation, context-aware symptom analysis, evidence chain tracking
   - Best for: Bug investigation where connecting to recent context improves effectiveness

3. **Nexus Docs/Ops** (`agent-invocations/nexus-docs-ops/AGENT.md`)
   - Role: Documentation and ops specialist with situational awareness
   - Enhancements: Memory-integrated alignment checking, context-aware change impact analysis, recent activity awareness
   - Best for: Documentation needs that connect to current project activity

4. **Nexus Validator** (`agent-invocations/nexus-validator/AGENT.md`)
   - Role: Validation specialist with situational awareness
   - Enhancements: Memory-integrated evidence evaluation, context-aware test relevance assessment, recent change awareness
   - Best for: Validation work that benefits from understanding recent changes and discussions

## 🚀 **Usage Instructions**

### Basic Pattern with Situational Awareness
```bash
ollama run <model-name> << 'EOF'
[PASTE THE COMPLETE ENHANCED AGENT DEFINITION HERE]

[YOUR QUESTION THAT BENEFITS FROM CONTEXT AWARENESS HERE]
EOF
```

### Example Usage Pattern
```bash
ollama run qwen2.5:0.5b << 'EOF'
[PASTE THE COMPLETE CONTENT OF agent-invocations/nexus-architect/AGENT.md HERE]

Based on our recent discussion about improving connection reliability and the code changes we just reviewed in the transport layer, how should I approach adding heartbeat monitoring to the WebSocket client connections?
EOF
```

## ⚙️ **How These Enhancements Help**

### 🧠 **Reducing Loops Through Context Awareness**
Instead of repeating the same analysis, these invocations:
- Reference **recent memory** (last 6 exchanges) to avoid reprocessing known information
- Build on **current context** rather than starting from scratch each time
- Provide **structured approaches** that evolve with the conversation
- Acknowledge **context limits** to prevent overconfidence in incomplete analysis

### 👁️ **Improving Situational Awareness**
The enhancements help agents:
- **Connect to recent activity**: Understand how current questions relate to ongoing work
- **Prioritize effectively**: Focus on what's currently relevant based on recent exchanges
- **Link analysis to specifics**: Connect architectural/debugging decisions to specific recent discussions
- **Validate appropriately**: Suggest verification approaches that match current project state
- **Maintain awareness**: Stay oriented within the current project context rather than drifting

### 💝 **Maintaining Personalization**
Despite the enhancements, these invocations:
- **Preserve core personalities**: Keep the fundamental temperaments and styles intact
- **Respect individual approaches**: Maintain each agent's characteristic way of working
- **Allow personal expression**: Still enable the unique voice of each agent type
- **Support individual growth**: Permit agents to develop while keeping their core identity

## 📁 **File Structure**

```
NEXUS-COVE/
├── AGENT_INVOCATIONS_README.md          # This file
├── CHECKPOINT_AGENT_INVOCATIONS.md      # Development history
└── agent-invocations/
    ├── nexus-architect/
    │   └── AGENT.md                     # Enhanced architecture planner
    ├── nexus-debug/
    │   └── AGENT.md                     # Enhanced debugging specialist
    ├── nexus-docs-ops/
    │   └── AGENT.md                     # Enhanced documentation specialist
    └── nexus-validator/
        └── AGENT.md                     # Enhanced validation specialist
```

## 🔬 **Testing Recommendations**

To test the effectiveness of these enhanced invocations:

### 1. **Context Continuity Test**
```bash
# First exchange
ollama run qwen2.5:0.5b << 'EOF'
[PASTE nexus-debug/AGENT.md HERE]

I'm seeing timeout errors in the WebSocket client connections.
EOF

# Second exchange (should reference first)
ollama run qwen2.5:0.5b << 'EOF'
[PASTE nexus-debug/AGENT.md HERE]

Based on what we just discussed, where should I look first for the root cause?
EOF
```

### 2. **Situational Response Test**
```bash
ollama run qwen2.5:0.5b << 'EOF'
[PASTE nexus-architect/AGENT.md HERE]

We were just discussing the authentication system - how should I approach adding rate limiting to prevent abuse?
EOF
```

### 3. **Personalization Check**
Verify that each agent maintains their characteristic approach:
- **Architect**: Methodical, boundary-aware, minimal design focus
- **Debug**: Systematic, evidence-driven, reproduction-focused  
- **Docs/Ops**: Detail-oriented, alignment-focused, procedure-conscious
- **Validator**: Rigorous, skeptical, evidence-requiring

## 🧪 **Validation Approach**

These enhancements are designed to:
- ✅ **Reduce repetitive analysis** by leveraging recent context
- ✅ **Improve relevance** by connecting to current project activity
- ✅ **Maintain core personalities** while enhancing effectiveness
- ✅ **Provide clear situational awareness guidelines**
- ✅ **Support better human-agent collaboration** through context-aware responses
- ✅ **Work with existing NEXUS-COVE systems** without modification

## 📝 **Important Notes**

- **No existing files modified** - all additions are new files only
- **Existing agent system unchanged** - `/src/nexus_cove/agents/` remains intact
- **Compatible with any model** - works with Ollama, LlamaCpp, or similar
- **Easy iteration** - refine based on your testing results
- **Safe to remove** - delete `agent-invocations/` directory and README files anytime

## 🔄 **Next Steps for Testing**

1. **Try basic usage** as shown in the examples above
2. **Test context continuity** by asking follow-up questions that should reference prior exchanges
3. **Verify personalization** - ensure each agent maintains their characteristic approach
4. **Assess effectiveness** - note whether responses feel more context-aware and less repetitive
5. **Iterate and refine** - adjust the enhancements based on your actual usage patterns