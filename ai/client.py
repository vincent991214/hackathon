import openai
import re
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
openai.api_key = "KlPuOX3MvbmNVUYAGjWaEnZYOreipYZyRigY4oTXIYM"
openai.api_base = "https://api.poe.com/v1"
MODEL_NAME = "gemini-3-pro"




def _clean_response(text):
    """
    Removes the 'Thinking...' block often produced by reasoning models.
    It usually appears as lines starting with '>' or wrapped in *Thinking*.
    """
    # Remove blockquotes (common representation of thinking)
    text = re.sub(r'^>.*$', '', text, flags=re.MULTILINE)

    # Remove explicit *Thinking...* lines
    text = re.sub(r'\*Thinking\.\.\.\*', '', text)

    # Remove leading/trailing whitespace
    return text.strip()


def _send_request(prompt):
    try:
        response = openai.ChatCompletion.create(
            model=MODEL_NAME,
            temperature=0.1,
            messages=[{"role": "user", "content": prompt}]
        )
        raw_content = response.choices[0].message.content
        return _clean_response(raw_content)
    except Exception as e:
        return f"AI Error: {str(e)}"


def generate_template(template_text=None, instructions=""):
    if not template_text:
        template_text = """
        # Executive Summary
        # System Architecture
        # Component Description
        | Component | Type | Description |
        |---|---|---|
        | Main | Entry | Entry point |
        # API Reference
        """

    prompt = f"""
    # Role:
    You are an expert Information Architect and Prompt Engineer. Your specialty is analyzing technical documentation to extract reuseable structural templates for AI generation pipelines.

    # Task:
    Analyze the provided specific documentation content (`<example_documentation>`) and reverse-engineer it into a **generalized documentation template**.

    Your goal is to create a hierarchical outline where each section contains a specific **Intent Instruction**. This instruction will guide an AI agent on *what* to write in that section for a completely different software project, without carrying over the specific technical implementation details (like class names, specific logic, or variable names) from the source text.
    
    # Input Data:
    <example_documentation>
    {template_text}
    </example_documentation>

    # Output Format:
    <output-format>
    # PROJECT-TITLE
    ## 1. Major section 1
    The inent of major section 1, guiding AI to write content under this section.
    ### 1.N Sub-section 1.N
    The intent of sub-section 1.N
    #### 1.N.M Sub-sub-section 1.N.M
    The intent of sub-sub-section 1.N.M
    ####...# 1.N.M...O Sub-sub-...-sub-section 1.N.M...O
    The intent of sub-sub-...-sub-section 1.N.M...O
    ## 2 Major section 2
    The intent of major section 2
    ...
    ## N. Major section N
    The intent of major section N
    </output-format>

    # Abstraction Rules (CRITICAL):
    1. Maintain the section structure generally, BUT **omit sub-sections** if they merely list specific implementation classes, tools, or vendors (e.g., specific file names, technical details).
    2. **De-contextualize Intent**: When writing the "Intent", strip away specific entities (e.g., "JMS", "XMLValidator", "GenericConsumerImpl"). Replace them with generic functional terms (e.g., "the component", "the implementation", "the validation logic").
    3. **Focus on "The What" and "The Why"**: The intent should explain the *purpose* of the section (e.g., "describe the workflow", "explain the validation rules"), not simply copy the content.

    # Few-Shot Example (Learn from this)

    <example1>
    **Input Text:**
    > ### 4.1 Database Connection Pool
    > The `HikariCP` wrapper manages the connection lifecycle. It initializes a pool of 10 connections at startup and validates them using a `SELECT 1` query. If the database is unreachable, it retries 3 times before throwing a `ConnectionException`.

    **Desired Output:**
    > ### 4.1 Database Connection Pool
    > The intent of this section is to describe the mechanism used for managing database connections, including initialization strategies, validation methods, and error handling behavior during connection failures.
    </example1>

    <example_2>
    **Input Text:**
    > ### 5.1 Payment Gateway Integration**
    > 
    > #### 5.1.1 AliPaySDKHandler
    > This class encapsulates the RSA signature logic required by AliPay...
    > 
    > #### 5.1.2 WeChatPayXmlParser
    > This component handles the XML serialization for WeChat Pay APIs...

    **Desired Output:**
    > ### 5.1 Payment Gateway Integration
    > The intent of this section is to document the integration with external payment providers, summarizing how specific SDK handlers and parsers are implemented to satisfy third-party protocol requirements.
    </example_2>

    # Output Format Specification
    Please output the result in **Markdown**.
    - The content under each header must be the **Intent Instruction**.

    ---
    ***Begin your analysis:**
    """
    return _send_request(prompt)


def generate_docs(template_md, code, instructions=""):
    prompt = f"""
    You are a professional technical writer.

    Task: Using the provided template structure and codebase, generate comprehensive technical documentation. Follow the template hierarchy strictly.

    TEMPLATE STRUCTURE:
    {template_md}

    CODEBASE:
    {code[:15000]} 
    (Note: Code truncated to 15000 chars to fit limits)

    ADDITIONAL INSTRUCTIONS:
    {instructions}

    IMPORTANT FORMATTING RULES:
    1. Use Markdown headers (# for H1, ## for H2).
    2. Use Markdown tables for lists of components or parameters.
    3. Do NOT use code blocks for normal text.
    4. Ensure clarity and conciseness in explanations.

    Output ONLY the documentation content.
    """
    return _send_request(prompt)

def chat_with_code(code, user_question, history=""):
    prompt = f"""
    You are a Lead Developer assisting a user.

    CODEBASE CONTEXT:
    {code[:20000]}

    CHAT HISTORY:
    {history[-2000:]}

    USER QUESTION: {user_question}

    IMPORTANT: 
    1. Be helpful and professional.
    2. If referencing a file, use the format: `path/to/file.py`.
    3. Do not output internal thought processes.
    """
    return _send_request(prompt)


def suggest_refactor(code):
    prompt = f"""
    You are a Code Quality Expert.
    Analyze the codebase and suggest 3 specific improvements.

    CODEBASE CONTEXT:
    {code[:20000]}

    OUTPUT FORMAT:
    ### Suggestion 1: [Title]
    [Explanation]
    ```python
    [Code Snippet]
    ```
    """
    return _send_request(prompt)


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
    """
    Generate EJB interface documentation using the Super-Context.

    This function analyzes an EJB interface with its implementation bean and
    related DTOs/Entities to generate comprehensive technical documentation.

    Args:
        interface_context: Super-Context containing Interface + Bean + DTOs code
        interface_name: Name of the EJB interface being documented
        model: Model to use for generation (default: gemini-2.5-pro)

    Returns:
        Generated markdown documentation
    """
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
        except Exception as e:
            # Fall back to default model on error
            pass

    # Use default model
    return _send_ejb_request(interface_context, interface_name)


def _send_gemini_request(model_client, interface_context: str, interface_name: str) -> str:
    """Send request to Gemini API."""
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
    except Exception as e:
        return []


def get_interface_context(interface_name: str, chroma_db_path: str = "./chroma_db") -> str:
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
    except Exception as e:
        return None