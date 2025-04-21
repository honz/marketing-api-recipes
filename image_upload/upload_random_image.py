import sys
import random
from PIL import Image, ImageDraw
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.adimage import AdImage

# Import credentials from your constants file
import sys
sys.path.append("..")
from utils.constants import (
    AD_ACCOUNT_ID as ad_account_id,
    APP_ID as app_id,
    APP_SECRET as app_secret,
)
from utils.test_creds import LL_ACCESS_TOKEN as access_token

def create_random_image(size=(1080, 1080)):
    # Create a new image with a random background color
    background_color = (
        random.randint(0, 255),
        random.randint(0, 255),
        random.randint(0, 255)
    )
    image = Image.new('RGB', size, background_color)
    draw = ImageDraw.Draw(image)
    
    # Draw some random shapes
    for _ in range(5):
        shape_color = (
            random.randint(0, 255),
            random.randint(0, 255),
            random.randint(0, 255)
        )
        # Draw a random rectangle
        x1 = random.randint(0, size[0])
        y1 = random.randint(0, size[1])
        x2 = random.randint(0, size[0])
        y2 = random.randint(0, size[1])
        draw.rectangle([x1, y1, x2, y2], fill=shape_color)
    
    return image

def upload_image_to_facebook():
    # Initialize the Facebook API
    FacebookAdsApi.init(app_id, app_secret, access_token)
    
    # Create and save the random image
    image = create_random_image()
    temp_image_path = 'temp_ad_image.png'
    image.save(temp_image_path)
    
    try:
        # Create the image object
        image = AdImage(parent_id=ad_account_id)
        
        # Upload the image
        image[AdImage.Field.filename] = temp_image_path
        image.remote_create()
        
        # Get the hash of the uploaded image
        image_hash = image[AdImage.Field.hash]
        print("Image uploaded successfully! Image hash: {}".format(image_hash))
        
        return image_hash
    
    except Exception as e:
        print("Error uploading image: {}".format(str(e)))
        return None
    
    finally:
        # Clean up the temporary file
        import os
        if os.path.exists(temp_image_path):
            os.remove(temp_image_path)

if __name__ == "__main__":
    upload_image_to_facebook() 