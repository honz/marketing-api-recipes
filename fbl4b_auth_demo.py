import sys
import webbrowser
import os
import json
import urllib
import urllib2
from BaseHTTPServer import HTTPServer, BaseHTTPRequestHandler
from urlparse import parse_qs, urlparse

sys.path.append("/opt/homebrew/lib/python2.7/site-packages")
sys.path.append("/opt/homebrew/lib/python2.7/site-packages/facebook_business-3.0.0-py2.7.egg-info")

from constants import APP_ID, APP_SECRET
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.user import User
from facebook_business.session import FacebookSession

# Configuration
REDIRECT_URI = "http://localhost:8000/callback"
CONFIG_ID = "1293011281794423"  # FBL4B Configuration ID

class AuthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/callback"):
            # Parse the authorization code from the callback URL
            query_components = parse_qs(urlparse(self.path).query)
            
            # Check for error response
            if "error" in query_components:
                error = query_components["error"][0]
                error_description = query_components.get("error_description", ["No description"])[0]
                error_reason = query_components.get("error_reason", ["No reason"])[0]
                print("\nAuthorization Error:")
                print("Error: {}".format(error))
                print("Description: {}".format(error_description))
                print("Reason: {}".format(error_reason))
                
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("Authorization failed! Please check the console for details.")
                os._exit(1)
            
            if "code" in query_components:
                code = query_components["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("Authorization successful! You can close this window.")
                
                try:
                    # Exchange the code for an access token
                    print("\nExchanging code for access token...")
                    token_url = "https://graph.facebook.com/v3.0/oauth/access_token"
                    params = urllib.urlencode({
                        "client_id": APP_ID,
                        "client_secret": APP_SECRET,
                        "redirect_uri": REDIRECT_URI,
                        "code": code
                    })
                    url = "{}?{}".format(token_url, params)
                    response = urllib2.urlopen(url)
                    response_data = json.loads(response.read())
                    
                    if "error" in response_data:
                        print("\nToken Exchange Error:")
                        print("Error: {}".format(response_data.get("error", {}).get("message", "Unknown error")))
                        print("Type: {}".format(response_data.get("error", {}).get("type", "Unknown type")))
                        print("Code: {}".format(response_data.get("error", {}).get("code", "Unknown code")))
                        os._exit(1)
                    
                    access_token = response_data["access_token"]
                    print("Access token received: {}".format(access_token))
                    
                    # Initialize the API with the access token
                    session = FacebookSession(
                        app_id=APP_ID,
                        app_secret=APP_SECRET,
                        access_token=access_token
                    )
                    api = FacebookAdsApi(session)
                    FacebookAdsApi.set_default_api(api)
                    
                    # Get the current user
                    print("\nGetting user information...")
                    user = User(fbid='me')
                    user_info = user.api_get(fields=['name', 'id'])
                    print("Logged in as: {} (ID: {})".format(user_info['name'], user_info['id']))
                    
                    # Get ad accounts accessible to the user
                    print("\nFetching accessible ad accounts...")
                    ad_accounts = user.get_ad_accounts(fields=['name', 'account_status', 'id'])
                    print("\nFound {} ad accounts:".format(len(ad_accounts)))
                    
                    for account in ad_accounts:
                        print("\nAd Account:")
                        print("Name: {}".format(account['name']))
                        print("ID: {}".format(account['id']))
                        print("Status: {}".format(account['account_status']))
                        
                        # Test reading account details
                        try:
                            account_details = AdAccount(account['id']).api_get(fields=['name', 'account_status'])
                            print("Successfully read account details")
                        except Exception as e:
                            print("Error reading account details: {}".format(str(e)))
                    
                except Exception as e:
                    print("\nError during API access: {}".format(str(e)))
                    print("Full error details:", e)
                    if hasattr(e, 'response'):
                        print("Response data:", e.response.read())
                
                # Stop the server
                os._exit(0)
            else:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write("Authorization failed! No code received.")
                os._exit(1)

def main():
    # Generate the authorization URL using the configuration ID
    auth_url = "https://www.facebook.com/v3.0/dialog/oauth?client_id={}&redirect_uri={}&config_id={}&response_type=code".format(
        APP_ID,
        REDIRECT_URI,
        CONFIG_ID
    )
    
    print("Starting FBL4B authorization demo...")
    print("\nOpening browser for authorization...")
    print("Please make sure you have the necessary permissions in the ad account.")
    webbrowser.open(auth_url)
    
    # Start local server to handle the callback
    print("\nWaiting for authorization callback...")
    server = HTTPServer(("localhost", 8000), AuthHandler)
    server.serve_forever()

if __name__ == "__main__":
    main() 