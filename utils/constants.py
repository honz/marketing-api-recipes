import os

def get_env_var(name, default=None, is_required=True):
    """
    Get an environment variable value, with logging and fallback.
    
    Args:
        name: Name of the environment variable
        default: Default value if not found
        is_required: Whether this variable is required
        
    Returns:
        Value of the environment variable or default
    """
    value = os.environ.get(name)
    
    if value is not None:
        print(f"Using {name}={value} from environment")
        return value
    
    if default is not None:
        print(f"Using default value for {name}: {default}")
        return default
    
    if is_required:
        print(f"ERROR: {name} environment variable not set")
        print(f"Please set it using: export {name}=your_value")
    
    return None

# Meta API credentials
APP_ID = int(get_env_var("META_APP_ID", 123, is_required=True) or 0)
APP_SECRET = get_env_var("META_APP_SECRET", "123", is_required=True)
AD_ACCOUNT_ID = get_env_var("META_AD_ACCOUNT_ID", "act_123", is_required=True)
PAGE_ID = int(get_env_var("META_PAGE_ID", 123, is_required=True) or 0)
CATALOG_ID = int(get_env_var("META_CATALOG_ID", 123, is_required=True) or 0)