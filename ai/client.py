import openai
import re

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
            messages=[{"role": "user", "content": prompt}]
        )
        raw_content = response.choices[0].message.content
        return _clean_response(raw_content)
    except Exception as e:
        return f"AI Error: {str(e)}"


def generate_docs(code, template_text=None, instructions=""):
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
    You are a Senior Technical Writer for DXC Technology.
    Task: Write professional documentation.

    IMPORTANT FORMATTING RULES:
    1. Use Markdown headers (# for H1, ## for H2).
    2. Use Markdown tables for lists of components or parameters.
    3. Use **Bold** for emphasis.
    4. Do NOT use code blocks for normal text.

    USER INSTRUCTIONS: {instructions}

    TARGET STRUCTURE:
    {template_text}

    CODEBASE CONTEXT:
    {code[:25000]}
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