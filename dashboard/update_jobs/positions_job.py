import os
import json
import datetime
import uuid
from pathlib import Path
from dotenv import load_dotenv
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import GetAssetsRequest
from alpaca.trading.enums import AssetClass, AssetStatus

# Load environment variables (in local development)
# In GitHub Actions, environment variables are set directly
load_dotenv(dotenv_path=None, verbose=True)

# Configure Alpaca client
ALPACA_API_KEY = os.getenv('ALPACA_API_KEY')
ALPACA_SECRET_KEY = os.getenv('ALPACA_SECRET_KEY')
ALPACA_PAPER = os.getenv('ALPACA_PAPER', 'true').lower() == 'true'

# Set up data directory
DATA_DIR = Path(__file__).parent.parent / 'data' / 'snapshots'
DATA_DIR.mkdir(parents=True, exist_ok=True)

def get_malaysia_time():
    """Get current time in Malaysia timezone (UTC+8)"""
    utc_now = datetime.datetime.utcnow()
    malaysia_time = utc_now + datetime.timedelta(hours=8)
    return malaysia_time

def debug_environment():
    """Debug environment and configuration"""
    print("=== ENVIRONMENT DEBUG ===")
    print(f"Current working directory: {os.getcwd()}")
    print(f"Script location: {Path(__file__).parent}")
    print(f"Data directory: {DATA_DIR}")
    print(f"Data directory exists: {DATA_DIR.exists()}")
    print(f"Current UTC time: {datetime.datetime.utcnow()}")
    print(f"Current Malaysia time: {get_malaysia_time()}")
    print(f"ALPACA_API_KEY set: {'Yes' if ALPACA_API_KEY else 'No'}")
    print(f"ALPACA_SECRET_KEY set: {'Yes' if ALPACA_SECRET_KEY else 'No'}")
    print(f"ALPACA_PAPER: {ALPACA_PAPER}")
    
    # Check existing files in snapshots directory
    if DATA_DIR.exists():
        files = list(DATA_DIR.glob("*.json"))
        print(f"Existing snapshot files: {len(files)}")
        if files:
            # Show the 3 most recent files
            recent_files = sorted(files, key=lambda x: x.stat().st_mtime)[-3:]
            print("Most recent files:")
            for f in recent_files:
                mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
                print(f"  {f.name} (modified: {mtime})")
    print("=== END DEBUG ===\n")

def fetch_alpaca_data():
    """
    Fetch account data and positions from Alpaca API and save to JSON file
    """
    print("Initializing Alpaca client...")
    
    # Validate credentials before creating client
    if not ALPACA_API_KEY or not ALPACA_SECRET_KEY:
        raise ValueError("Missing Alpaca API credentials")
    
    # Initialize Alpaca trading client
    trading_client = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=ALPACA_PAPER)
    
    print("Fetching account data...")
    # Get account info
    account = trading_client.get_account()
    account_data = {
        'id': account.id,
        'cash': float(account.cash),
        'portfolio_value': float(account.portfolio_value),
        'buying_power': float(account.buying_power),
        'currency': account.currency,
        'account_status': account.status,
        'trading_blocked': account.trading_blocked,
        'equity': float(account.equity),
        'updated_at': get_malaysia_time().isoformat()
    }
    print(f"Account data fetched - Portfolio value: ${account.portfolio_value}")
    
    print("Fetching positions...")
    # Get positions
    positions = trading_client.get_all_positions()
    positions_data = []
    
    for position in positions:
        positions_data.append({
            'symbol': position.symbol,
            'qty': float(position.qty),
            'market_value': float(position.market_value),
            'cost_basis': float(position.cost_basis),
            'unrealized_pl': float(position.unrealized_pl),
            'unrealized_plpc': float(position.unrealized_plpc),
            'current_price': float(position.current_price),
            'avg_entry_price': float(position.avg_entry_price),
            'side': position.side,
            'exchange': position.exchange
        })
    
    print(f"Positions fetched - {len(positions_data)} positions found")
    
    # Combine account and positions data
    data = {
        'account': account_data,
        'positions': positions_data,
        'cash': float(account.cash),  # Added for compatibility with app.py
        'timestamp': get_malaysia_time().isoformat()
        # 'timestamp': datetime.datetime.now().isoformat()
    }
    
    return data

class JSONEncoder(json.JSONEncoder):
    """Custom JSON encoder to handle UUID objects"""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return json.JSONEncoder.default(self, obj)

def save_data(data, agent_name='default'):
    """
    Save data to a JSON file with timestamp in filename
    
    Args:
        data (dict): Data to save
        agent_name (str): Name of the agent
    """
    # timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    timestamp = get_malaysia_time().strftime('%Y%m%d_%H%M%S')
    filename = f"{agent_name}_{timestamp}.json"
    filepath = DATA_DIR / filename
    
    # with open(filepath, 'w') as f:
    #     json.dump(data, f, indent=2, cls=JSONEncoder)
    print(f"Attempting to save data to: {filepath}")
    
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2, cls=JSONEncoder)
        
        print(f"✅ Successfully saved data to {filepath}")
        print(f"File size: {filepath.stat().st_size} bytes")
        return filepath
    except Exception as e:
        print(f"❌ Error saving file: {str(e)}")
        raise

def run_job(agent_name='default'):
    """
    Run the job to fetch and save Alpaca positions data
    
    Args:
        agent_name (str): Name of the agent
    """
    debug_environment()
    
    try:
        print("Starting Alpaca data fetch...")
        data = fetch_alpaca_data()
        print("Data fetch successful, saving to file...")
        save_data(data, agent_name)
        success_msg = "✅ Successfully fetched and saved Alpaca data"
        print(success_msg)
        return True, success_msg
    except Exception as e:
        error_msg = f"❌ Error in run_job: {str(e)}"
        print(error_msg)
        import traceback
        print("Full traceback:")
        traceback.print_exc()
        return False, error_msg

if __name__ == "__main__":
    print(f"Starting positions job at {get_malaysia_time()}")
    # Run the job for the default agent
    success, message = run_job()
    print(f"Job completed. Success: {success}")
    print(f"Message: {message}")
    
    # Final directory check
    print(f"\nFinal check - Files in {DATA_DIR}:")
    if DATA_DIR.exists():
        files = sorted(DATA_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime)
        for f in files[-5:]:  # Show last 5 files
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            print(f"  {f.name} (modified: {mtime})")
    else:
        print("  Data directory does not exist!")