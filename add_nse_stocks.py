import os
import requests
import time
from datetime import datetime, timezone
from supabase import create_client

# Set up environment variables
os.environ['SUPABASE_URL'] = 'https://lfwgposvyckptsrjkkyx.supabase.co'
os.environ['SUPABASE_SERVICE_KEY'] = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imxmd2dwb3N2eWNrcHRzcmpra3l4Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTg0MjI3MSwiZXhwIjoyMDY1NDE4MjcxfQ.7Pjsw_HpyE5RHHFshsRT3Ibpn1b6N4CO3F4rIw_GSvc'

sb = create_client(os.environ['SUPABASE_URL'], os.environ['SUPABASE_SERVICE_KEY'])

def fetch_nse_symbols():
    """Fetch NSE stock symbols from various sources"""

    # Comprehensive list of NSE stocks (top liquid stocks)
    nse_stocks = [
        # NIFTY 50 (Most liquid)
        ('RELIANCE', 'NSE', 'Reliance Industries', 'Oil & Gas'),
        ('TCS', 'NSE', 'Tata Consultancy Services', 'IT'),
        ('HDFCBANK', 'NSE', 'HDFC Bank', 'Banking'),
        ('INFY', 'NSE', 'Infosys', 'IT'),
        ('ITC', 'NSE', 'ITC Ltd', 'FMCG'),
        ('HINDUNILVR', 'NSE', 'Hindustan Unilever', 'FMCG'),
        ('KOTAKBANK', 'NSE', 'Kotak Mahindra Bank', 'Banking'),
        ('LT', 'NSE', 'Larsen & Toubro', 'Infrastructure'),
        ('AXISBANK', 'NSE', 'Axis Bank', 'Banking'),
        ('MARUTI', 'NSE', 'Maruti Suzuki', 'Auto'),
        ('BAJFINANCE', 'NSE', 'Bajaj Finance', 'Finance'),
        ('BHARTIARTL', 'NSE', 'Bharti Airtel', 'Telecom'),
        ('ASIANPAINT', 'NSE', 'Asian Paints', 'Consumer'),
        ('HCLTECH', 'NSE', 'HCL Technologies', 'IT'),
        ('TITAN', 'NSE', 'Titan Company', 'Consumer'),
        ('SUNPHARMA', 'NSE', 'Sun Pharmaceutical', 'Pharma'),
        ('ULTRACEMCO', 'NSE', 'UltraTech Cement', 'Cement'),
        ('ADANIPORTS', 'NSE', 'Adani Ports', 'Logistics'),
        ('NESTLEIND', 'NSE', 'Nestle India', 'FMCG'),
        ('POWERGRID', 'NSE', 'Power Grid Corp', 'Power'),
        ('NTPC', 'NSE', 'NTPC Ltd', 'Power'),
        ('BAJAJFINSV', 'NSE', 'Bajaj Finserv', 'Finance'),
        ('GRASIM', 'NSE', 'Grasim Industries', 'Diversified'),
        ('M&M', 'NSE', 'Mahindra & Mahindra', 'Auto'),
        ('CIPLA', 'NSE', 'Cipla', 'Pharma'),
        ('JSWSTEEL', 'NSE', 'JSW Steel', 'Steel'),
        ('HEROMOTOCO', 'NSE', 'Hero MotoCorp', 'Auto'),
        ('DRREDDY', 'NSE', 'Dr. Reddy\'s Labs', 'Pharma'),
        ('SHREECEM', 'NSE', 'Shree Cement', 'Cement'),
        ('BPCL', 'NSE', 'Bharat Petroleum', 'Oil & Gas'),
        ('COALINDIA', 'NSE', 'Coal India', 'Mining'),
        ('EICHERMOT', 'NSE', 'Eicher Motors', 'Auto'),
        ('BRITANNIA', 'NSE', 'Britannia Industries', 'FMCG'),
        ('UPL', 'NSE', 'UPL Ltd', 'Agrochemicals'),
        ('INDIGO', 'NSE', 'IndiGo', 'Aviation'),
        ('GODREJCP', 'NSE', 'Godrej Consumer', 'FMCG'),
        ('HAVELLS', 'NSE', 'Havells India', 'Electrical'),
        ('DABUR', 'NSE', 'Dabur India', 'FMCG'),
        ('MARICO', 'NSE', 'Marico Ltd', 'FMCG'),
        ('COLPAL', 'NSE', 'Colgate Palmolive', 'FMCG'),

        # Additional liquid stocks (NIFTY NEXT 50)
        ('ADANIGREEN', 'NSE', 'Adani Green Energy', 'Power'),
        ('ADANITRANS', 'NSE', 'Adani Transmission', 'Power'),
        ('ALKEM', 'NSE', 'Alkem Laboratories', 'Pharma'),
        ('AMBUJACEM', 'NSE', 'Ambuja Cements', 'Cement'),
        ('APOLLOHOSP', 'NSE', 'Apollo Hospitals', 'Healthcare'),
        ('AUROPHARMA', 'NSE', 'Aurobindo Pharma', 'Pharma'),
        ('BANDHANBNK', 'NSE', 'Bandhan Bank', 'Banking'),
        ('BEL', 'NSE', 'Bharat Electronics', 'Defense'),
        ('BERGEPAINT', 'NSE', 'Berger Paints', 'Consumer'),
        ('BIOCON', 'NSE', 'Biocon', 'Pharma'),
        ('BOSCHLTD', 'NSE', 'Bosch Ltd', 'Auto'),
        ('CADILAHC', 'NSE', 'Cadila Healthcare', 'Pharma'),
        ('CHOLAFIN', 'NSE', 'Cholamandalam Finance', 'Finance'),
        ('CONCOR', 'NSE', 'Container Corp', 'Logistics'),
        ('CROMPTON', 'NSE', 'Crompton Greaves', 'Consumer'),
        ('DIVISLAB', 'NSE', 'Divi\'s Laboratories', 'Pharma'),
        ('DLF', 'NSE', 'DLF Ltd', 'Real Estate'),
        ('DIXON', 'NSE', 'Dixon Technologies', 'Electronics'),
        ('FEDERALBNK', 'NSE', 'Federal Bank', 'Banking'),
        ('GAIL', 'NSE', 'GAIL India', 'Oil & Gas'),
        ('GLAND', 'NSE', 'Gland Pharma', 'Pharma'),
        ('GODREJPROP', 'NSE', 'Godrej Properties', 'Real Estate'),
        ('HAL', 'NSE', 'Hindustan Aeronautics', 'Defense'),
        ('HDFCAMC', 'NSE', 'HDFC AMC', 'Finance'),
        ('HDFCLIFE', 'NSE', 'HDFC Life Insurance', 'Insurance'),
        ('ICICIGI', 'NSE', 'ICICI General Insurance', 'Insurance'),
        ('ICICIPRULI', 'NSE', 'ICICI Prudential Life', 'Insurance'),
        ('IDFCFIRSTB', 'NSE', 'IDFC First Bank', 'Banking'),
        ('IGL', 'NSE', 'Indraprastha Gas', 'Oil & Gas'),
        ('INDHOTEL', 'NSE', 'Indian Hotels', 'Hospitality'),
        ('INDUSTOWER', 'NSE', 'Indus Towers', 'Telecom'),
        ('IRCTC', 'NSE', 'IRCTC', 'Railways'),
        ('JINDALSTEL', 'NSE', 'Jindal Steel', 'Steel'),
        ('JUBLFOOD', 'NSE', 'Jubilant FoodWorks', 'Food'),
        ('LICHSGFIN', 'NSE', 'LIC Housing Finance', 'Finance'),
        ('LTI', 'NSE', 'L&T Infotech', 'IT'),
        ('LTTS', 'NSE', 'L&T Technology Services', 'IT'),
        ('LUPIN', 'NSE', 'Lupin Ltd', 'Pharma'),
        ('MCDOWELL-N', 'NSE', 'United Spirits', 'Alcohol'),
        ('MFSL', 'NSE', 'Max Financial Services', 'Finance'),
        ('MGL', 'NSE', 'Mahanagar Gas', 'Oil & Gas'),
        ('MINDTREE', 'NSE', 'Mindtree', 'IT'),
        ('MPHASIS', 'NSE', 'MphasiS', 'IT'),
        ('MRF', 'NSE', 'MRF Ltd', 'Tyres'),
        ('MUTHOOTFIN', 'NSE', 'Muthoot Finance', 'Finance'),
        ('NAM-INDIA', 'NSE', 'Nippon India AMC', 'Finance'),
        ('NATIONALUM', 'NSE', 'National Aluminium', 'Metals'),
        ('NAUKRI', 'NSE', 'Info Edge', 'Internet'),
        ('NAVINFLUOR', 'NSE', 'Navin Fluorine', 'Chemicals'),
        ('NMDC', 'NSE', 'NMDC Ltd', 'Mining'),
        ('OBEROIRLTY', 'NSE', 'Oberoi Realty', 'Real Estate'),
        ('OFSS', 'NSE', 'Oracle Financial', 'IT'),
        ('PAGEIND', 'NSE', 'Page Industries', 'Textiles'),
        ('PEL', 'NSE', 'Piramal Enterprises', 'Diversified'),
        ('PETRONET', 'NSE', 'Petronet LNG', 'Oil & Gas'),
        ('PFC', 'NSE', 'Power Finance Corp', 'Finance'),
        ('PFIZER', 'NSE', 'Pfizer Ltd', 'Pharma'),
        ('PIDILITIND', 'NSE', 'Pidilite Industries', 'Chemicals'),
        ('PIIND', 'NSE', 'PI Industries', 'Agrochemicals'),
        ('PNB', 'NSE', 'Punjab National Bank', 'Banking'),
        ('POLYCAB', 'NSE', 'Polycab India', 'Cables'),
        ('PVR', 'NSE', 'PVR Ltd', 'Entertainment'),
        ('RAMCOCEM', 'NSE', 'Ramco Cements', 'Cement'),
        ('RBLBANK', 'NSE', 'RBL Bank', 'Banking'),
        ('RECLTD', 'NSE', 'REC Ltd', 'Finance'),
        ('SBICARD', 'NSE', 'SBI Cards', 'Finance'),
        ('SBILIFE', 'NSE', 'SBI Life Insurance', 'Insurance'),
        ('SBIN', 'NSE', 'State Bank of India', 'Banking'),
        ('SIEMENS', 'NSE', 'Siemens Ltd', 'Engineering'),
        ('SRF', 'NSE', 'SRF Ltd', 'Chemicals'),
        ('SRTRANSFIN', 'NSE', 'Shriram Transport', 'Finance'),
        ('STAR', 'NSE', 'Star Health Insurance', 'Insurance'),
        ('SUNTV', 'NSE', 'Sun TV Network', 'Media'),
        ('SYNGENE', 'NSE', 'Syngene International', 'Pharma'),
        ('TATACHEM', 'NSE', 'Tata Chemicals', 'Chemicals'),
        ('TATACOMM', 'NSE', 'Tata Communications', 'Telecom'),
        ('TATACONSUM', 'NSE', 'Tata Consumer', 'FMCG'),
        ('TATAELXSI', 'NSE', 'Tata Elxsi', 'IT'),
        ('TATAMOTORS', 'NSE', 'Tata Motors', 'Auto'),
        ('TATAPOWER', 'NSE', 'Tata Power', 'Power'),
        ('TATASTEEL', 'NSE', 'Tata Steel', 'Steel'),
        ('TECHM', 'NSE', 'Tech Mahindra', 'IT'),
        ('TORNTPHARM', 'NSE', 'Torrent Pharma', 'Pharma'),
        ('TRENT', 'NSE', 'Trent Ltd', 'Retail'),
        ('TVSMOTOR', 'NSE', 'TVS Motor', 'Auto'),
        ('UBL', 'NSE', 'United Breweries', 'Alcohol'),
        ('VEDL', 'NSE', 'Vedanta Ltd', 'Metals'),
        ('VOLTAS', 'NSE', 'Voltas Ltd', 'Consumer'),
        ('WIPRO', 'NSE', 'Wipro Ltd', 'IT'),
        ('ZEEL', 'NSE', 'Zee Entertainment', 'Media'),

        # Additional high-liquidity stocks
        ('ACC', 'NSE', 'ACC Ltd', 'Cement'),
        ('ADANIENT', 'NSE', 'Adani Enterprises', 'Diversified'),
        ('AMARAJABAT', 'NSE', 'Amara Raja Batteries', 'Auto'),
        ('APOLLOTYRE', 'NSE', 'Apollo Tyres', 'Tyres'),
        ('ASHOKLEY', 'NSE', 'Ashok Leyland', 'Auto'),
        ('ASTRAL', 'NSE', 'Astral Ltd', 'Pipes'),
        ('ATUL', 'NSE', 'Atul Ltd', 'Chemicals'),
        ('BAJAJ-AUTO', 'NSE', 'Bajaj Auto', 'Auto'),
        ('BAJAJELEC', 'NSE', 'Bajaj Electricals', 'Consumer'),
        ('BALKRISIND', 'NSE', 'Balkrishna Industries', 'Tyres'),
        ('BALMLAWRIE', 'NSE', 'Balmer Lawrie', 'Diversified'),
        ('BATAINDIA', 'NSE', 'Bata India', 'Footwear'),
        ('BEML', 'NSE', 'BEML Ltd', 'Engineering'),
        ('BHARATFORG', 'NSE', 'Bharat Forge', 'Auto'),
        ('BHEL', 'NSE', 'BHEL', 'Engineering'),
        ('CANBK', 'NSE', 'Canara Bank', 'Banking'),
        ('CASTROLIND', 'NSE', 'Castrol India', 'Oil & Gas'),
        ('CENTURYTEX', 'NSE', 'Century Textiles', 'Textiles'),
        ('CESC', 'NSE', 'CESC Ltd', 'Power'),
        ('CHENNPETRO', 'NSE', 'Chennai Petroleum', 'Oil & Gas'),
        ('CUMMINSIND', 'NSE', 'Cummins India', 'Engineering'),
        ('ESCORTS', 'NSE', 'Escorts Ltd', 'Auto'),
        ('EXIDEIND', 'NSE', 'Exide Industries', 'Auto'),
        ('FCONSUMER', 'NSE', 'Future Consumer', 'FMCG'),
        ('FORTIS', 'NSE', 'Fortis Healthcare', 'Healthcare'),
        ('FRETAIL', 'NSE', 'Future Retail', 'Retail'),
        ('GODFRYPHLP', 'NSE', 'Godfrey Phillips', 'Tobacco'),
        ('GODREJAGRO', 'NSE', 'Godrej Agrovet', 'Agrochemicals'),
        ('GRANULES', 'NSE', 'Granules India', 'Pharma'),
        ('GUJGASLTD', 'NSE', 'Gujarat Gas', 'Oil & Gas'),
        ('HEIDELBERG', 'NSE', 'Heidelberg Cement', 'Cement'),
        ('HINDALCO', 'NSE', 'Hindalco Industries', 'Metals'),
        ('HINDCOPPER', 'NSE', 'Hindustan Copper', 'Metals'),
        ('HINDPETRO', 'NSE', 'HPCL', 'Oil & Gas'),
        ('HONAUT', 'NSE', 'Honeywell Automation', 'Engineering'),
        ('IBULHSGFIN', 'NSE', 'Indiabulls Housing', 'Finance'),
        ('IDBI', 'NSE', 'IDBI Bank', 'Banking'),
        ('IFBIND', 'NSE', 'IFB Industries', 'Consumer'),
        ('IOB', 'NSE', 'Indian Overseas Bank', 'Banking'),
        ('IOC', 'NSE', 'Indian Oil Corp', 'Oil & Gas'),
        ('IPCALAB', 'NSE', 'IPCA Laboratories', 'Pharma'),
        ('IRB', 'NSE', 'IRB Infrastructure', 'Infrastructure'),
        ('J&KBANK', 'NSE', 'Jammu & Kashmir Bank', 'Banking'),
        ('JINDALSAW', 'NSE', 'Jindal Saw', 'Steel'),
        ('JKCEMENT', 'NSE', 'JK Cement', 'Cement'),
        ('JKLAKSHMI', 'NSE', 'JK Lakshmi Cement', 'Cement'),
        ('JSLHISAR', 'NSE', 'JSL Hisar', 'Steel'),
        ('JUBILANT', 'NSE', 'Jubilant Life Sciences', 'Pharma'),
        ('JUSTDIAL', 'NSE', 'Justdial', 'Internet'),
        ('KAJARIACER', 'NSE', 'Kajaria Ceramics', 'Ceramics'),
        ('KANSAINER', 'NSE', 'Kansai Nerolac', 'Paints'),
        ('KARURVYSYA', 'NSE', 'Karur Vysya Bank', 'Banking'),
        ('KEC', 'NSE', 'KEC International', 'Engineering'),
        ('KNRCON', 'NSE', 'KNR Constructions', 'Infrastructure'),
        ('KSB', 'NSE', 'KSB Ltd', 'Engineering'),
        ('LAOPALA', 'NSE', 'La Opala RG', 'Glass'),
        ('LINDEINDIA', 'NSE', 'Linde India', 'Industrial Gases'),
        ('MAHABANK', 'NSE', 'Bank of Maharashtra', 'Banking'),
        ('MAHINDCIE', 'NSE', 'Mahindra CIE', 'Auto'),
        ('MAHLIFE', 'NSE', 'Mahindra Lifespace', 'Real Estate'),
        ('MANAPPURAM', 'NSE', 'Manappuram Finance', 'Finance'),
        ('MCX', 'NSE', 'Multi Commodity Exchange', 'Finance'),
        ('METROPOLIS', 'NSE', 'Metropolis Healthcare', 'Healthcare'),
        ('MHRIL', 'NSE', 'Mahindra Holidays', 'Hospitality'),
        ('MINDAIND', 'NSE', 'Minda Industries', 'Auto'),
        ('MMTC', 'NSE', 'MMTC Ltd', 'Trading'),
        ('MOIL', 'NSE', 'MOIL Ltd', 'Mining'),
        ('MRPL', 'NSE', 'MRPL', 'Oil & Gas'),
        ('NATCOPHARM', 'NSE', 'Natco Pharma', 'Pharma'),
        ('NBCC', 'NSE', 'NBCC India', 'Infrastructure'),
        ('NHPC', 'NSE', 'NHPC Ltd', 'Power'),
        ('NILKAMAL', 'NSE', 'Nilkamal Ltd', 'Plastics'),
        ('OIL', 'NSE', 'Oil India Ltd', 'Oil & Gas'),
        ('ORIENTELEC', 'NSE', 'Orient Electric', 'Consumer'),
        ('PCJEWELLER', 'NSE', 'PC Jeweller', 'Jewelry'),
        ('PRESTIGE', 'NSE', 'Prestige Estates', 'Real Estate'),
        ('PTC', 'NSE', 'PTC India', 'Power'),
        ('RADICO', 'NSE', 'Radico Khaitan', 'Alcohol'),
        ('RAIN', 'NSE', 'Rain Industries', 'Cement'),
        ('RAJESHEXPO', 'NSE', 'Rajesh Exports', 'Jewelry'),
        ('RALLIS', 'NSE', 'Rallis India', 'Agrochemicals'),
        ('RCF', 'NSE', 'Rashtriya Chemicals', 'Chemicals'),
        ('RELINFRA', 'NSE', 'Reliance Infrastructure', 'Infrastructure'),
        ('RITES', 'NSE', 'RITES Ltd', 'Infrastructure'),
        ('RVNL', 'NSE', 'RVNL', 'Infrastructure'),
        ('SAIL', 'NSE', 'Steel Authority of India', 'Steel'),
        ('SANOFI', 'NSE', 'Sanofi India', 'Pharma'),
        ('SCHAEFFLER', 'NSE', 'Schaeffler India', 'Auto'),
        ('SCHNEIDER', 'NSE', 'Schneider Electric', 'Electrical'),
        ('SJVN', 'NSE', 'SJVN Ltd', 'Power'),
        ('SONATSOFTW', 'NSE', 'Sonata Software', 'IT'),
        ('SOUTHBANK', 'NSE', 'South Indian Bank', 'Banking'),
        ('SPARC', 'NSE', 'Sun Pharma Advanced', 'Pharma'),
        ('SUZLON', 'NSE', 'Suzlon Energy', 'Power'),
        ('SWANENERGY', 'NSE', 'Swan Energy', 'Textiles'),
        ('TASTYBITE', 'NSE', 'Tasty Bite Eatables', 'Food'),
        ('TCI', 'NSE', 'Transport Corp of India', 'Logistics'),
        ('TCIEXP', 'NSE', 'TCI Express', 'Logistics'),
        ('THERMAX', 'NSE', 'Thermax Ltd', 'Engineering'),
        ('TIMKEN', 'NSE', 'Timken India', 'Engineering'),
        ('TRIDENT', 'NSE', 'Trident Ltd', 'Textiles'),
        ('TTKPRESTIG', 'NSE', 'TTK Prestige', 'Consumer'),
        ('UNIONBANK', 'NSE', 'Union Bank of India', 'Banking'),
        ('VGUARD', 'NSE', 'V-Guard Industries', 'Electrical'),
        ('VTL', 'NSE', 'Vardhman Textiles', 'Textiles'),
        ('WELCORP', 'NSE', 'Welspun Corp', 'Steel'),
        ('WELSPUNIND', 'NSE', 'Welspun India', 'Textiles'),
        ('WHIRLPOOL', 'NSE', 'Whirlpool India', 'Consumer'),
        ('ZEEMEDIA', 'NSE', 'Zee Media', 'Media'),
    ]

    return nse_stocks

def add_stocks_to_database(stocks_list):
    """Add stocks to the symbols table"""

    print(f"🚀 Adding {len(stocks_list)} NSE stocks to database...")

    added = 0
    skipped = 0

    for ticker, exchange, name, sector in stocks_list:
        try:
            # Check if already exists
            existing = sb.table('symbols').select('id').eq('ticker', ticker).eq('exchange', exchange).execute().data

            if existing:
                print(f"  ⏭️ {ticker} already exists")
                skipped += 1
                continue

            # Add new symbol
            sb.table('symbols').insert({
                'ticker': ticker,
                'exchange': exchange,
                'name': name,
                'sector': sector,
                'is_active': True,
                'is_fno': ticker in ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ITC', 'HINDUNILVR', 'AXISBANK'],  # F&O stocks
                'lot_size': 1  # Default lot size
            }).execute()

            print(f"  ✅ Added {ticker} ({sector})")
            added += 1

            # Be respectful to database
            time.sleep(0.1)

        except Exception as e:
            print(f"  ❌ Error adding {ticker}: {e}")
            skipped += 1

    print(f"\n📊 Summary: {added} added, {skipped} skipped")
    return added

def main():
    print("📈 NSE STOCK UNIVERSE EXPANSION")
    print("=" * 50)

    # Get NSE stocks
    nse_stocks = fetch_nse_symbols()

    print(f"📋 Found {len(nse_stocks)} NSE stocks")

    # Show sample
    print("\n📋 Sample stocks:")
    for i, (ticker, exchange, name, sector) in enumerate(nse_stocks[:10]):
        print(f"  {ticker} - {name} ({sector})")

    if len(nse_stocks) > 10:
        remaining = len(nse_stocks) - 10
        print(f"  ... and {remaining} more stocks")

    # Auto-confirm for testing - remove this line for production
    print(f"\n⚠️ Auto-adding {len(nse_stocks)} stocks to database...")

    # Add to database
    added = add_stocks_to_database(nse_stocks)

    print(f"\n🎉 Successfully added {added} NSE stocks!")
    print("📈 Your trading universe is now much larger!")

    # Show database summary
    try:
        total_symbols = sb.table('symbols').select('id').execute().data
        active_symbols = sb.table('symbols').select('id').eq('is_active', True).execute().data

        print("\n📊 Database Summary:")
        print(f"  Total symbols: {len(total_symbols)}")
        print(f"  Active symbols: {len(active_symbols)}")

        # Show sector breakdown
        sectors = sb.table('symbols').select('sector').execute().data
        sector_count = {}
        for s in sectors:
            sector = s.get('sector', 'Unknown')
            sector_count[sector] = sector_count.get(sector, 0) + 1

        print("\n📈 Sector Breakdown:")
        for sector, count in sorted(sector_count.items(), key=lambda x: x[1], reverse=True):
            print(f"  {sector}: {count} stocks")

    except Exception as e:
        print(f"❌ Error getting summary: {e}")

if __name__ == "__main__":
    main()