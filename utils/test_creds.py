import os
from .constants import get_env_var

# Long-lived access token for Meta API
# This is a placeholder token - never commit real tokens to git
DEFAULT_TOKEN = "PLACEHOLDER_META_ACCESS_TOKEN"
LL_ACCESS_TOKEN = get_env_var("META_ACCESS_TOKEN", DEFAULT_TOKEN, is_required=True)

# Warning: this is a placeholder token, you should replace it with a valid token
if LL_ACCESS_TOKEN == DEFAULT_TOKEN:
    print("WARNING: Using placeholder access token. For production use, set META_ACCESS_TOKEN environment variable.")