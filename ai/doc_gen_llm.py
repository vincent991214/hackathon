import openai
import re
import os
from pathlib import Path
from typing import Optional, Tuple, List
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration
openai.api_key = os.getenv("OPENAI_API_KEY", "")
openai.api_base = os.getenv("OPENAI_API_BASE", "https://open.bigmodel.cn/api/coding/paas/v4")
MODEL_NAME = "GLM-4.7"




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


def _read_project_docs(project_path: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Read README.md and CLAUDE.md files from the project.

    Args:
        project_path: Path to the project directory

    Returns:
        Tuple of (readme_content, claude_md_content) - None if file not found
    """
    path = Path(project_path)
    readme_content = None
    claude_md_content = None

    # Search for README.md (case-insensitive)
    for readme_name in ['README.md', 'readme.md', 'README.MD']:
        readme_path = path / readme_name
        if readme_path.exists():
            try:
                with open(readme_path, 'r', encoding='utf-8') as f:
                    readme_content = f.read()
                break
            except Exception:
                pass

    # Search for CLAUDE.md (case-insensitive)
    for claude_name in ['CLAUDE.md', 'claude.md', 'CLAUDE.MD']:
        claude_path = path / claude_name
        if claude_path.exists():
            try:
                with open(claude_path, 'r', encoding='utf-8') as f:
                    claude_md_content = f.read()
                break
            except Exception:
                pass

    # Also search in parent directories (up to 3 levels)
    if readme_content is None or claude_md_content is None:
        for i in range(1, 4):
            parent_path = path.parents[min(i, len(path.parents) - 1)]
            if parent_path == path:
                break

            if readme_content is None:
                for readme_name in ['README.md', 'readme.md', 'README.MD']:
                    readme_path = parent_path / readme_name
                    if readme_path.exists():
                        try:
                            with open(readme_path, 'r', encoding='utf-8') as f:
                                readme_content = f.read()
                            break
                        except Exception:
                            pass

            if claude_md_content is None:
                for claude_name in ['CLAUDE.md', 'claude.md', 'CLAUDE.MD']:
                    claude_path = parent_path / claude_name
                    if claude_path.exists():
                        try:
                            with open(claude_path, 'r', encoding='utf-8') as f:
                                claude_md_content = f.read()
                            break
                        except Exception:
                            pass

    return readme_content, claude_md_content


def _format_file_contents(file_contents) -> str:
    """Format smart file reader results for LLM consumption."""
    output = []
    output.append("# PROJECT FILES (Smart Scan)\n")

    # Group by language
    by_language = {}
    for fc in file_contents:
        lang = fc.language
        if lang not in by_language:
            by_language[lang] = []
        by_language[lang].append(fc)

    for lang, files in sorted(by_language.items()):
        output.append(f"## {lang} Files ({len(files)} files)\n")

        for fc in files[:50]:  # Limit to prevent overflow
            output.append(f"### `{fc.file_path}`")
            output.append(f"**Size:** {fc.file_size // 1024}KB | **Lines:** {fc.line_count}")
            output.append(f"**Strategy:** {fc.reading_strategy}\n")
            output.append("```")
            output.append(fc.content[:2000])  # Truncate very long contents
            output.append("```\n")

    return "\n".join(output)


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


def generate_docs(template_md, project_analysis, instructions=""):
    """
    Generate documentation using parsed project analysis.

    Args:
        template_md: Template structure
        project_analysis: ProjectAnalysis from parser (contains files + metadata + project_path)
        instructions: Additional user instructions

    Returns:
        Generated documentation
    """
    # Check if project_analysis is a string (legacy code path)
    if isinstance(project_analysis, str):
        # Legacy mode - treat as raw code string
        prompt = f"""
        You are a professional technical writer.

        Task: Using the provided template structure and codebase, generate comprehensive technical documentation. Follow the template hierarchy strictly.

        TEMPLATE STRUCTURE:
        {template_md}

        CODEBASE:
        {project_analysis[:15000]}
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

    # Read project documentation files for additional context
    # project_analysis.project_path contains the path to the project
    readme_content, claude_md_content = _read_project_docs(project_analysis.project_path)

    # Format code context based on parser type
    if project_analysis.parser_type == "tree_sitter_java":
        # For tree-sitter Java parser (not yet implemented)
        code_context = "# Java AST parsing not yet implemented\n"
    else:
        code_context = _format_file_contents(project_analysis.files)
    

    # Build project documentation section
    project_docs_section = ""
    if readme_content or claude_md_content:
        project_docs_section = "\n## PROJECT DOCUMENTATION\n"
        if readme_content:
            project_docs_section += f"\n### README.md\n{readme_content[:5000]}\n"  # Limit length
        if claude_md_content:
            project_docs_section += f"\n### CLAUDE.md (Project Instructions)\n{claude_md_content[:5000]}\n"  # Limit length
        project_docs_section += "\n"

    # Build prompt
    prompt = f"""
You are a professional technical writer.

Task: Using the provided template structure and codebase analysis, generate comprehensive technical documentation.

TEMPLATE STRUCTURE:
{template_md}

README.md and CLAUDE.md:
{project_docs_section}

CODEBASE:

{code_context}

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

