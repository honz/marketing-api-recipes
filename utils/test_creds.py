import os
from .constants import get_env_var

# Long-lived access token for Meta API
DEFAULT_TOKEN = "EAAIm6aae31oBO5spzqBmYjmKRAdXYFkUFi77ZBZCZBsB8Ec8alrrNf7YZAi7FcmqhcP1GTgBNfE8ZCgtDOsarxsy6A0eMWICxjSh4zjJHLaISRdYwdpSr5RZBQN8zWA9LR5kPk8ymSZCragO9V3aE2iZAxdMcjCr9hkg8ZCIjjsLdBswmXTCrRa72g1kMhnHm2verzGzPXwZDZD"
LL_ACCESS_TOKEN = get_env_var("META_ACCESS_TOKEN", DEFAULT_TOKEN, is_required=True)

# Warning: this is a placeholder token, you should replace it with a valid token
if LL_ACCESS_TOKEN == DEFAULT_TOKEN:
    print("WARNING: Using placeholder access token. For production use, set META_ACCESS_TOKEN environment variable.")