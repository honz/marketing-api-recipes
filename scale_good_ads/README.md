# Scale Good Ads Demo

This demo shows how to:

1. Identify top-performing ads based on ROAS (Return on Ad Spend) metrics
2. Pause the original ad to avoid competition
3. Scale the successful ad by duplicating it to multiple ad sets defined in a file

## Prerequisites

- Facebook Marketing API access
- Python 3.6+
- `facebook-business` SDK

## Usage

1. Set up environment variables (see `/utils/README.md`)
2. Create a text file with target ad sets (see `target_adsets.example`)
   - One ad set ID per line
   - Lines starting with # are treated as comments
3. Run the script:

```bash
cd /path/to/marketing-api-recipes
./scale_good_ads/scale_good_ads.py
```

### Command Line Options

```bash
# Specify a custom target ad sets file
./scale_good_ads/scale_good_ads.py -f /path/to/my_adsets.txt

# Use a different ROAS threshold
./scale_good_ads/scale_good_ads.py -r 3.0

# Change lookback period for performance data
./scale_good_ads/scale_good_ads.py -d 14

# Dry run mode (no actual changes)
./scale_good_ads/scale_good_ads.py -n
```

## Configuration

- `MIN_ROAS_THRESHOLD`: The minimum ROAS value required for scaling
- Target ad sets are defined in a text file that can be specified when running the script

## How It Works

The script:
1. Retrieves active ads from your ad account
2. Evaluates performance metrics (ROAS) for each ad
3. Identifies ads that exceed the defined ROAS threshold
4. Pauses the original high-performing ad
5. Creates copies of the successful ad in each of the target ad sets
6. Uses Facebook's Ad Copy API for efficient duplication
7. Logs all actions for auditing and tracking

## Sample Output

```
Checking 24 active ads for performance metrics...
Found 3 ads with ROAS greater than 2.5
Scaling ad 123456789 with ROAS 3.2 to 5 target ad sets...
Successfully scaled ad to ad set 111111111
Successfully scaled ad to ad set 222222222
Successfully scaled ad to ad set 333333333
Successfully scaled ad to ad set 444444444
Successfully scaled ad to ad set 555555555
Original ad 123456789 has been paused
```