"""
EJB LLM Module

This module contains AI-powered functions for generating documentation
for EJB (Enterprise Java Beans) interfaces.
"""

import os
from dotenv import load_dotenv
from typing import Optional

# Load environment variables from .env file
load_dotenv()

# Import shared functions from doc_gen_llm
from ai.doc_gen_llm import _send_request, MODEL_NAME, openai


# ==================== EJB ANALYSIS FUNCTIONS ====================

def generate_ejb_template(interface_context: str, interface_name: str, model: str = None) -> str:
    """
    Generate EJB interface documentation using the Super-Context.

    This function analyzes an EJB interface with its implementation bean and
    related DTOs/Entities to generate comprehensive technical documentation.

    Args:
        interface_context: Super-Context containing Interface + Bean + DTOs code
        interface_name: Name of the EJB interface being documented
        model: Model to use for generation (default: MODEL_NAME from config)

    Returns:
        Generated markdown documentation
    """
    # Use default model if not specified
    if model is None:
        model = MODEL_NAME

    # Try to use gemini model if requested
    if model.startswith("gemini"):
        try:
            import google.generativeai as genai
            api_key = os.getenv("GEMINI_API_KEY", "")
            if api_key:
                genai.configure(api_key=api_key)
                model_client = genai.GenerativeModel(model)
                return _send_gemini_request(model_client, interface_context, interface_name)
        except ImportError:
            # Fall back to default model if Gemini not available
            pass
        except Exception:
            # Fall back to default model on error
            pass

    # Use default model
    return _send_ejb_request(interface_context, interface_name)


def _send_gemini_request(model_client, interface_context: str, interface_name: str) -> str:
    """Send request to Gemini API."""
    from ai.doc_gen_llm import _clean_response
    prompt = _build_ejb_prompt(interface_context, interface_name)

    try:
        response = model_client.generate_content(prompt)
        return _clean_response(response.text)
    except Exception as e:
        return f"AI Error: {str(e)}"


def _send_ejb_request(interface_context: str, interface_name: str) -> str:
    """Send request using the default OpenAI-compatible API."""
    prompt = _build_ejb_prompt(interface_context, interface_name)
    return _send_request(prompt)


def _build_ejb_prompt(interface_context: str, interface_name: str) -> str:
    """Build the prompt for EJB documentation generation."""
    return f"""
# Role:
You are a Senior Java Architect specializing in Enterprise Java Beans (EJB) systems.
Your expertise includes analyzing EJB interfaces, implementation beans, and related
data transfer objects to produce comprehensive technical documentation.

# Task:
Analyze the provided EJB interface code (including its implementation bean and
related DTOs/Entities) and generate structured technical documentation following
the specified format.

# Input Code:
<ejb_super_context>
{interface_context}
</ejb_super_context>

# Output Format:
Please generate documentation with the following sections:

## 1. Interface Overview
Provide a summary of the interface including:
- **Purpose**: What business capability this interface provides
- **Type**: Remote/Local/Business interface type
- **Package**: Java package name
- **JNDI Name** (if applicable): The JNDI binding name

## 2. Interface Contract
List all methods defined in the interface in a table format:

| Method Name | Return Type | Parameters | Description |
|-------------|-------------|------------|-------------|
| methodName1 | ReturnType1 | param1: Type1 | Brief description |
| methodName2 | ReturnType2 | param2: Type2, param3: Type3 | Brief description |

## 3. Business Logic Flow
For each main business method in the interface:
1. Analyze the implementation bean code
2. Write step-by-step pseudocode describing the business logic flow
3. Include key decisions, validations, and data transformations

Format:
### Method: methodName
```
Step 1: [Action description]
Step 2: [Action description]
    - Sub-step 2.1: [Detail]
    - Sub-step 2.2: [Detail]
Step 3: [Action description]
...
```

## 4. Data Structures
Document all related DTOs and Entities:
- For each DTO: List its fields and their types
- For each Entity: Describe the database mapping and relationships

## 5. Dependencies and Integrations
List external dependencies, databases, or other systems this interface interacts with.

## 6. Exception Handling
Document the exceptions that can be thrown and their conditions.

# Important Guidelines:
1. Use proper Markdown formatting
2. Focus on business logic and architectural decisions
3. Include code snippets from the provided context where relevant
4. If JNDI name is not explicitly defined, derive it from standard naming conventions
5. The pseudocode should be language-agnostic and focus on business logic flow

---
***Begin your analysis:**
"""


def get_available_interfaces(chroma_db_path: str = "./chroma_db") -> list:
    """
    Get a list of all available EJB interface names from ChromaDB.

    Args:
        chroma_db_path: Path to the ChromaDB persistence directory

    Returns:
        List of interface names
    """
    try:
        from utils.ejb_rag_builder import ChromaDBManager
        manager = ChromaDBManager(persist_directory=chroma_db_path)
        return manager.get_all_interface_names()
    except Exception:
        return []


def get_interface_context(interface_name: str, chroma_db_path: str = "./chroma_db") -> Optional[str]:
    """
    Retrieve the Super-Context for a specific interface from ChromaDB.

    Args:
        interface_name: Name of the interface to retrieve
        chroma_db_path: Path to the ChromaDB persistence directory

    Returns:
        Super-Context string or None if not found
    """
    try:
        from utils.ejb_rag_builder import ChromaDBManager
        manager = ChromaDBManager(persist_directory=chroma_db_path)
        results = manager.query_by_interface_name(interface_name)

        if results and results[0].get('document'):
            return results[0]['document']

        return None
    except Exception:
        return None
