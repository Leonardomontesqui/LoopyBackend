import asyncio
import os
import json
from dotenv import load_dotenv
from agents import Agent, Runner, trace, function_tool, OpenAIChatCompletionsModel
from openai import AsyncOpenAI
from pydantic import BaseModel

# Load environment variables
load_dotenv(override=True)

# Get Gemini API key
gemini_api_key = os.getenv('GEMINI_API_KEY')
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"

# Initialize Gemini client for the agent using AsyncOpenAI
gemini_client = AsyncOpenAI(
    api_key=gemini_api_key,
    base_url=GEMINI_BASE_URL
)

# Create the model for the agent
gemini_model = OpenAIChatCompletionsModel(model="gemini-2.0-flash", openai_client=gemini_client)

class ErrorAnalysisOutput(BaseModel):
    title: str
    description: str

@function_tool
def analyze_session_errors(errors: list) -> dict:
    """Analyze JavaScript console errors and generate a title and description for a bug report"""
    error_summary = "\n".join([f"- {error['message']} (occurred {error['count']} times)" for error in errors])
    
    prompt = f"""
    Analyze these JavaScript console errors from a user session and create:
    1. A concise, descriptive title (max 60 characters)
    2. A detailed description explaining what went wrong and potential impact
    
    Errors:
    {error_summary}
    
    Please respond ONLY with a JSON object in this exact format, and nothing else:
    {{
        "title": "Your concise title here",
        "description": "Your detailed description here"
    }}
    Do not include any code, markdown, or explanation. Only output the JSON object.
    """
    
    return {"prompt": prompt, "errors_count": len(errors)}

def create_analysis_agent():
    """Create an agent for analyzing session errors using Gemini API"""
    analysis_instructions = """You are an expert at analyzing JavaScript console errors and creating clear, actionable titles and descriptions for bug reports. Focus on the most impactful errors and provide insights that would help developers understand and fix the issues. MAX 2 SENTENCES\n\nUse the analyze_session_errors tool to process the errors and generate appropriate titles and descriptions."""
    
    analysis_agent = Agent(
        name="Session Error Analyzer", 
        instructions=analysis_instructions, 
        model=gemini_model,
        output_type=ErrorAnalysisOutput
    )
    
    return analysis_agent

async def test_agent_analysis():
    """Test the agent with sample error data"""
    print("Testing OpenAI Agent SDK with Gemini...")
    
    # Sample error data
    test_errors = [
        {"message": "TypeError: Cannot read property 'length' of undefined", "count": 3},
        {"message": "NetworkError: Failed to fetch", "count": 1},
        {"message": "ReferenceError: $ is not defined", "count": 2}
    ]
    
    try:
        # Create the agent
        agent = create_analysis_agent()
        print("✓ Agent created successfully")
        
        # Prepare the error data for the agent
        error_summary = "\n".join([f"- {error['message']} (occurred {error['count']} times)" for error in test_errors])
        
        print(f"Running agent with test errors:\n{error_summary}")
        
        # Run the agent with the errors using the correct Runner pattern
        result = await Runner.run(agent, f"Analyze these JavaScript console errors and create a title and description for a bug report:\n\n{error_summary}")
        
        print("✓ Agent execution completed")
        print(f"Result type: {type(result)}")
        print(f"Result attributes: {dir(result)}")
        print(f"Result: {result}")
        
        # Use structured output
        if result and hasattr(result, 'final_output') and result.final_output:
            print(f"Final output: {result.final_output}")
            return {
                "title": result.final_output.title,
                "description": result.final_output.description
            }
        else:
            print("No structured output found")
            return {
                "title": "Session Console Errors",
                "description": f"Session with {len(test_errors)} different types of console errors."
            }
            
    except Exception as e:
        print(f"❌ Agent analysis failed: {e}")
        return {
            "title": "Session Console Errors",
            "description": f"Session with {len(test_errors)} different types of console errors."
        }

async def main():
    """Main test function"""
    if not gemini_api_key:
        print("❌ GEMINI_API_KEY not found in environment variables")
        return
    
    print("🚀 Starting OpenAI Agent SDK with Gemini test...")
    print(f"Using Gemini API Key: {gemini_api_key[:10]}...")
    print(f"Using Gemini Base URL: {GEMINI_BASE_URL}")
    
    result = await test_agent_analysis()
    
    print("\n📋 Final Result:")
    print(json.dumps(result, indent=2))
    
    print("\n✅ Test completed!")

if __name__ == "__main__":
    asyncio.run(main()) 