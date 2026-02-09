"""
Application configuration.

Central configuration file for DevMate AI.
Imports tool configuration and API settings from environment variables.
"""

import os
from dotenv import load_dotenv
from utils.tool_config import ToolConfig

# Load environment variables
load_dotenv()

# Tool configuration
tool_config = ToolConfig()

# API Configuration
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "https://open.bigmodel.cn/api/coding/paas/v4")

# Model Configuration
MODEL_NAME = os.getenv("MODEL_NAME", "GLM-4.7")
