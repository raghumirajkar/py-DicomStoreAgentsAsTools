import os
from strands import Agent, tool
from strands_tools import retrieve
from strands.models import BedrockModel
from SystemPrompts.design_analyzer_system_prompt import DESIGN_ANALYZER_SYSTEM_PROMPT

# Also set as constants for code reference
KNOWLEDGE_BASE_ID = 'UIM2DUECHX'
AWS_REGION = 'us-east-1'
SCORE_THRESHOLD = 0.3

# Configuration - Set environment variables that the retrieve tool reads
os.environ['KNOWLEDGE_BASE_ID'] = KNOWLEDGE_BASE_ID
os.environ['AWS_REGION'] = AWS_REGION
os.environ['AWS_DEFAULT_REGION'] = AWS_REGION

@tool
def design_analyzer_tool(prompt: str) -> str:
    """
    Analyzes design specifications from the knowledge base using RAG.
    
    Args:
        prompt: The user's design question or request
        
    Returns:
        A comprehensive analysis based on design documentation
    """
    import logging
    logger = logging.getLogger(__name__)
    
    logger.info("Design analyzer started")
    
    model_id = 'amazon.nova-pro-v1:0'
    model = BedrockModel(model_id=model_id, region_name=AWS_REGION)
    
    tools = [retrieve]

    agent = Agent(
        model=model, 
        tools=tools,
        system_prompt=f'''
            {DESIGN_ANALYZER_SYSTEM_PROMPT}
            When using the retrieve tool:
                - Always set score to {SCORE_THRESHOLD} for better results
                - Set numberOfResults to 5 for comprehensive answers'''
    )
    
    try:
        # Agents are callable - just call them directly
        result = agent(prompt)
        
        # Extract the response text from the AgentResult
        if hasattr(result, 'response'):
            response_text = result.response
        elif hasattr(result, 'text'):
            response_text = result.text
        elif isinstance(result, str):
            response_text = result
        else:
            response_text = str(result)
            
        logger.info(f"Design analyzer completed ({len(response_text)} chars)")
        return response_text
        
    except Exception as e:
        logger.error(f"Design analyzer failed: {str(e)}", exc_info=True)
        raise