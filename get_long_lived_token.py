#!/usr/bin/env python
"""
Script to exchange a short-lived access token for a long-lived access token
and update the META_ACCESS_TOKEN environment variable.

Usage:
    python get_long_lived_token.py [short_lived_token]
    
If no token is provided as an argument, the script will use the token from
the META_ACCESS_TOKEN environment variable.
"""

import sys
import os
import requests
import json

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import project constants
from utils.constants import APP_ID, APP_SECRET, get_env_var
from utils.test_creds import LL_ACCESS_TOKEN, DEFAULT_TOKEN

def get_long_lived_token(app_id, app_secret, short_lived_token):
    """
    Exchange a short-lived token for a long-lived token using the Meta Graph API.
    
    Args:
        app_id: Meta app ID
        app_secret: Meta app secret
        short_lived_token: Short-lived access token to exchange
        
    Returns:
        Long-lived access token or None if exchange failed
    """
    if not short_lived_token or short_lived_token == DEFAULT_TOKEN:
        print("ERROR: No valid short-lived token provided")
        return None
        
    # Graph API endpoint for token exchange
    token_url = "https://graph.facebook.com/v18.0/oauth/access_token"
    
    # Parameters for token exchange
    params = {
        "grant_type": "fb_exchange_token",
        "client_id": app_id,
        "client_secret": app_secret,
        "fb_exchange_token": short_lived_token
    }
    
    try:
        print("Exchanging token...")
        response = requests.get(token_url, params=params)
        response_data = response.json()
        
        if "error" in response_data:
            print("Error exchanging token:")
            print(f"Message: {response_data.get('error', {}).get('message', 'Unknown error')}")
            print(f"Type: {response_data.get('error', {}).get('type', 'Unknown type')}")
            print(f"Code: {response_data.get('error', {}).get('code', 'Unknown code')}")
            return None
            
        access_token = response_data.get("access_token")
        if not access_token:
            print("No access token received in response")
            return None
            
        # Get token expiration info
        expires_in = response_data.get("expires_in", "unknown")
        print(f"Long-lived token received! Valid for approximately {expires_in} seconds")
        
        return access_token
        
    except Exception as e:
        print(f"Exception during token exchange: {str(e)}")
        return None

def update_env_var(token):
    """
    Update the META_ACCESS_TOKEN environment variable with the new token.
    
    Args:
        token: The new token value
        
    Returns:
        True if environment variable was updated, False otherwise
    """
    if not token:
        return False
        
    # Set environment variable for current process
    os.environ["META_ACCESS_TOKEN"] = token
    
    # Determine user's shell configuration file
    home = os.path.expanduser("~")
    shell = os.environ.get("SHELL", "").lower()
    
    if "zsh" in shell:
        config_file = os.path.join(home, ".zshrc")
    elif "bash" in shell:
        # Check for both .bashrc and .bash_profile
        if os.path.exists(os.path.join(home, ".bash_profile")):
            config_file = os.path.join(home, ".bash_profile")
        else:
            config_file = os.path.join(home, ".bashrc")
    else:
        # Default to .profile for other shells
        config_file = os.path.join(home, ".profile")
    
    # Look for existing META_ACCESS_TOKEN export
    token_exists = False
    token_line = f'export META_ACCESS_TOKEN="{token}"'
    updated_lines = []
    
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r') as f:
                lines = f.readlines()
                
                for line in lines:
                    if "export META_ACCESS_TOKEN=" in line:
                        updated_lines.append(token_line + '\n')
                        token_exists = True
                    else:
                        updated_lines.append(line)
            
            if token_exists:
                # Write back with updated token
                with open(config_file, 'w') as f:
                    f.writelines(updated_lines)
            else:
                # Append new token export
                with open(config_file, 'a') as f:
                    f.write(f"\n# Meta API access token (added by get_long_lived_token.py)\n{token_line}\n")
            
            print(f"Updated META_ACCESS_TOKEN in {config_file}")
            print(f"To use the new token in your current shell session, run:\nsource {config_file}")
            return True
            
    except Exception as e:
        print(f"Failed to update configuration file: {str(e)}")
        print(f"Please manually add the following line to your shell configuration file:")
        print(token_line)
    
    return False

def main():
    # Get short-lived token from command line or environment
    short_lived_token = None
    
    if len(sys.argv) > 1:
        # Use token provided as command line argument
        short_lived_token = sys.argv[1]
        print("Using token provided as command line argument")
    else:
        # Use token from environment variable
        short_lived_token = LL_ACCESS_TOKEN
        if short_lived_token == DEFAULT_TOKEN:
            print("ERROR: No valid token found in environment variable META_ACCESS_TOKEN")
            print("Please provide a valid short-lived token as an argument or set the META_ACCESS_TOKEN environment variable")
            sys.exit(1)
        print("Using token from META_ACCESS_TOKEN environment variable")
    
    # Exchange for long-lived token
    long_lived_token = get_long_lived_token(APP_ID, APP_SECRET, short_lived_token)
    
    if not long_lived_token:
        print("Failed to obtain long-lived token. Exiting.")
        sys.exit(1)
    
    # Update environment variable and shell config
    if update_env_var(long_lived_token):
        print("Successfully updated META_ACCESS_TOKEN")
    else:
        print("Token obtained but environment variable update failed")
        print(f"New long-lived token: {long_lived_token}")
        print("Set this token manually:")
        print(f'export META_ACCESS_TOKEN="{long_lived_token}"')
    
    print("\nToken exchange complete!")

if __name__ == "__main__":
    main()