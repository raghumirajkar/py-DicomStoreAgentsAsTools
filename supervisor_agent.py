# supervisor_agent.py

import os
import json
import logging
from typing import Dict, List, AsyncGenerator

from strands import Agent
from strands.models import BedrockModel
from requirements_analyzer_tool import requirements_analyzer_tool
from design_analyzer_tool import design_analyzer_tool
from SystemPrompts.supervisor_system_prompt import SUPERVISOR_SYSTEM_PROMPT
from SystemPrompts.synthesizer_system_prompt import SYNTHESIZER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

AWS_REGION = 'us-east-1'
#MODEL_ID_NOVA_PRO="amazon.nova-pro-v1:0"
MODEL_ID_NOVA_MICRO="amazon.nova-micro-v1:0"

os.environ['STRANDS_TOOL_CONSOLE_MODE'] = 'enabled'


class SupervisorAgent:
    def __init__(self):
        self.collected_outputs: Dict[str, str] = {}
        self.failures: List[str] = []
        
        # Initialize Strands Supervisor Agent with tools
        model = BedrockModel(model_id=MODEL_ID_NOVA_MICRO, region_name=AWS_REGION)
        
        self.supervisor = Agent(
            model=model,
            tools=[requirements_analyzer_tool, design_analyzer_tool],
            system_prompt=SUPERVISOR_SYSTEM_PROMPT
        )
        
        logger.info("SupervisorAgent initialized with Strands Agent")
        logger.info(f"Available tools: requirements_analyzer_tool, design_analyzer_tool")

    async def synthesize(self, user_prompt: str) -> AsyncGenerator[str, None]:
        """Streaming synthesis using boto3 bedrock runtime"""
        import boto3
        
        logger.info("Stage 2: Starting response synthesis")
        if self.failures:
            logger.warning(f"Synthesis includes {len(self.failures)} failures: {self.failures}")
        
        synthesis_prompt = f"""
You are an AI Text Synthesis Agent. 
Your primary function is to generate high-quality, coherent, and context-aware text based on 
the provided information. Combine the following information into a clean, comprehensive response.

Original user request:
{user_prompt}

Collected information from specialized tools:
{json.dumps(self.collected_outputs, indent=2)}

Failures (if any):
{self.failures if self.failures else 'None'}

{SYNTHESIZER_SYSTEM_PROMPT}
"""

        try:
            bedrock_runtime = boto3.client("bedrock-runtime", region_name=AWS_REGION)
            
            response = bedrock_runtime.invoke_model_with_response_stream(
                modelId=MODEL_ID_NOVA_MICRO,
                body=json.dumps({
                    "messages": [
                        {
                            "role": "user",
                            "content": [{"text": synthesis_prompt}]
                        }
                    ],
                    "inferenceConfig": {
                        "temperature": 0.5,
                        "maxTokens": 4000
                    }
                })
            )

            stream = response.get('body')
            total_chars = 0
            
            if stream:
                for event in stream:
                    chunk = event.get('chunk')
                    if chunk:
                        chunk_obj = json.loads(chunk.get('bytes').decode())
                        
                        if 'contentBlockDelta' in chunk_obj:
                            delta = chunk_obj['contentBlockDelta'].get('delta', {})
                            if 'text' in delta:
                                text_chunk = delta['text']
                                total_chars += len(text_chunk)
                                yield text_chunk
            
            logger.info(f"Synthesis completed ({total_chars} chars)")
            
        except Exception as e:
            logger.error(f"Synthesis failed: {str(e)}", exc_info=True)
            raise

    async def handle_request(self, payload: Dict) -> AsyncGenerator[str, None]:
        """
        Two-stage streaming request handler:
        Stage 1: Supervisor gathers information using tools
        Stage 2: Synthesizer formats the gathered information
        """
        user_prompt = payload.get("prompt", "")
        
        logger.info("=" * 80)
        logger.info("Starting two-stage request handling")
        logger.info(f"User prompt: {user_prompt[:100]}...")
        logger.info("=" * 80)

        try:
            # STAGE 1: Supervisor gathers information using tools
            logger.info("Stage 1: Supervisor gathering information with autonomous tool selection")
            
            try:
                supervisor_result = self.supervisor(user_prompt)
                
                # Extract text from AgentResult object
                supervisor_response = str(supervisor_result)
                
                if not supervisor_response or len(supervisor_response.strip()) == 0:
                    logger.error("Supervisor returned empty response")
                    self.failures.append("supervisor: Empty response returned")
                    error_msg = "Error: The supervisor agent failed to gather any information. Please try again or rephrase your query."
                    yield error_msg
                    return
                
                self.collected_outputs["supervisor"] = supervisor_response
                
                logger.info(f"✓ Stage 1 completed successfully")
                logger.info(f"  - Gathered: {len(supervisor_response)} characters")
                
            except Exception as e:
                logger.error(f"✗ Stage 1 failed: {str(e)}", exc_info=True)
                self.failures.append(f"supervisor: {str(e)}")
                
                # Return error message to user
                error_msg = f"Error: The supervisor agent encountered an error while gathering information: {str(e)}\n\nPlease try again or contact support if the issue persists."
                yield error_msg
                return

            # STAGE 2: Synthesize the gathered information
            logger.info("Stage 2: Synthesizing final response")
            
            try:
                async for chunk in self.synthesize(user_prompt):
                    yield chunk
                
                logger.info("✓ Stage 2 completed successfully")
                
            except Exception as e:
                logger.error(f"✗ Stage 2 failed: {str(e)}", exc_info=True)
                error_msg = f"\n\nError: Failed to synthesize the final response: {str(e)}"
                yield error_msg
                return
        
        finally:
            logger.info("=" * 80)
            logger.info("Request handling completed")
            logger.info(f"  - Outputs collected: {len(self.collected_outputs)}")
            logger.info(f"  - Failures: {len(self.failures)}")
            if self.failures:
                for failure in self.failures:
                    logger.warning(f"    ✗ {failure}")
            logger.info("=" * 80)