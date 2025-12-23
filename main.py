# main.py

import logging
from bedrock_agentcore.runtime import BedrockAgentCoreApp
from supervisor_agent import SupervisorAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

try:
    app = BedrockAgentCoreApp(enable_metrics=False)
except TypeError:
    # If the parameter doesn't exist, just create normally
    app = BedrockAgentCoreApp()

@app.entrypoint
async def invoke(payload, context):
    """
    Streaming entry point for AgentCore via Strands.
    Two-stage architecture:
    - Stage 1: Supervisor gathers information using tools
    - Stage 2: Synthesizer formats the response
    """
    user_prompt = payload.get('prompt', '')
    user_context = payload.get('context', {})
    
    # Create supervisor instance (session_id removed, will add back with memory integration)
    supervisor = SupervisorAgent()
    
    # Stream the response
    async for chunk in supervisor.handle_request({
        "prompt": user_prompt,
        "context": user_context
    }):
        yield chunk

if __name__ == "__main__":
    app.run()
