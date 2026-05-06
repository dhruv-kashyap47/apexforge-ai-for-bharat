"""Helper utility functions."""
import io
import csv
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import random

import pandas as pd


# Expected CSV columns
REQUIRED_COLUMNS = [
    'business_name', 'pan', 'gstin', 'address', 'pincode',
    'district', 'state', 'registration_date', 'last_activity_date', 'department'
]

# Flexible column name mappings
# Each internal field can have multiple possible source column names
COLUMN_MAPPINGS = {
    'business_name': ['business_name', 'company_name', 'firm_name', 'entity_name', 'organization_name', 'trade_name', 'legal_name', 'proprietor_owner_name'],
    'pan': ['pan', 'pan_number', 'pan_no', 'permanent_account_number'],
    'gstin': ['gstin', 'gstin_number', 'gstin_no', 'gst_number', 'gst_no'],
    'address': ['address', 'full_address', 'registered_address', 'business_address', 'office_address', 'communication_address'],
    'pincode': ['pincode', 'pin_code', 'pin', 'postal_code', 'zip_code', 'zip'],
    'district': ['district', 'dist', 'district_name', 'city', 'city_name'],
    'state': ['state', 'state_name', 'state_code', 'province', 'region'],
    'registration_date': ['registration_date', 'reg_date', 'date_of_registration', 'incorporation_date', 'commencement_date'],
    'last_activity_date': ['last_activity_date', 'activity_date', 'last_return_filed_date', 'last_filing_date', 'last_gstr1_filed', 'last_gstr3b_filed', 'last_transaction_date'],
    'department': ['department', 'source_status', 'gstin_status', 'source', 'department_name', 'jurisdiction', 'sector', 'constitution_type']
}

# Composite columns (when address is split across multiple fields)
COMPOSITE_MAPPINGS = {
    'address': {
        'parts': ['address_line1', 'address_line2', 'landmark', 'city', 'state', 'pin_code'],
        'separator': ', '
    }
}


def find_matching_column(df_columns: List[str], possible_names: List[str]) -> Optional[str]:
    """Find the first matching column name from possible options."""
    df_columns_lower = {col.lower().replace(' ', '_').replace('-', '_'): col for col in df_columns}

    for name in possible_names:
        name_normalized = name.lower().replace(' ', '_').replace('-', '_')
        # Exact match
        if name in df_columns:
            return name
        # Case-insensitive match
        if name_normalized in df_columns_lower:
            return df_columns_lower[name_normalized]
        # Substring match (e.g., 'pincode' matches 'pin_code')
        for col in df_columns:
            col_normalized = col.lower().replace(' ', '_').replace('-', '_')
            if name_normalized in col_normalized or col_normalized in name_normalized:
                return col
    return None


def map_and_transform_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Map various CSV column formats to standard internal format."""
    df_mapped = df.copy()
    column_mapping = {}  # source -> target
    unmatched_columns = []

    # Find mappings for each required column
    for target_col, possible_sources in COLUMN_MAPPINGS.items():
        matched_source = find_matching_column(df.columns.tolist(), possible_sources)
        if matched_source:
            column_mapping[matched_source] = target_col
        else:
            unmatched_columns.append(target_col)

    # Rename columns
    df_mapped = df_mapped.rename(columns=column_mapping)

    # Handle composite fields (e.g., address from multiple columns)
    if 'address' not in df_mapped.columns or df_mapped['address'].isna().all():
        address_parts = []
        for part in ['address_line1', 'address_line2', 'landmark', 'city', 'state']:
            if part in df.columns:
                address_parts.append(part)

        if address_parts:
            # Combine address parts
            def combine_address(row):
                parts = []
                for part in address_parts:
                    val = row.get(part)
                    if pd.notna(val) and str(val).strip():
                        parts.append(str(val).strip())
                return ', '.join(parts) if parts else None

            df_mapped['address'] = df.apply(combine_address, axis=1)
            if 'address' in unmatched_columns:
                unmatched_columns.remove('address')

    # Handle pincode variations (extract from pin_code if needed)
    if 'pincode' not in df_mapped.columns and 'pin_code' in df.columns:
        df_mapped['pincode'] = df['pin_code']
        if 'pincode' in unmatched_columns:
            unmatched_columns.remove('pincode')

    # Handle date column variations
    if 'last_activity_date' not in df_mapped.columns:
        # Try to use last filing dates as activity date
        for date_col in ['last_return_filed_date', 'last_gstr1_filed', 'last_gstr3b_filed', 'activity_date']:
            if date_col in df.columns:
                df_mapped['last_activity_date'] = df[date_col]
                if 'last_activity_date' in unmatched_columns:
                    unmatched_columns.remove('last_activity_date')
                break

    # Handle department/source variations
    if 'department' not in df_mapped.columns:
        for dept_col in ['source_status', 'gstin_status', 'sector', 'constitution_type']:
            if dept_col in df.columns:
                df_mapped['department'] = df[dept_col]
                if 'department' in unmatched_columns:
                    unmatched_columns.remove('department')
                break

    return df_mapped, unmatched_columns


def validate_and_map_csv(df: pd.DataFrame) -> Tuple[bool, pd.DataFrame, List[str], List[str]]:
    """
    Validate and map CSV columns automatically.
    Returns: (is_valid, mapped_df, missing_columns, detected_mappings)
    """
    # First try to map columns
    df_mapped, unmatched = map_and_transform_columns(df)

    # Check which required columns are still missing
    still_missing = [col for col in REQUIRED_COLUMNS if col not in df_mapped.columns]

    # Create list of detected mappings for display
    detected = []
    for target in REQUIRED_COLUMNS:
        if target in df_mapped.columns:
            # Find what source column was used
            for src, tgt in [(k, v) for k, v in {
                **{c: c for c in df.columns if c in df_mapped.columns},
            }.items()]:
                if tgt == target and src != target:
                    detected.append(f"{src} → {target}")
                    break
            else:
                if target in df.columns:
                    detected.append(f"{target} (exact match)")

    if still_missing:
        return False, df_mapped, still_missing, detected

    return True, df_mapped, [], detected


def validate_csv_columns(df: pd.DataFrame) -> Tuple[bool, List[str]]:
    """Validate that dataframe has required columns."""
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing:
        return False, missing

    return True, []


def format_date(date_val, format_str: str = '%Y-%m-%d') -> str:
    """Format a date value to string."""
    if date_val is None or pd.isna(date_val):
        return 'N/A'

    if isinstance(date_val, str):
        return date_val

    if isinstance(date_val, (datetime, pd.Timestamp)):
        return date_val.strftime(format_str)

    return str(date_val)


def generate_sample_csv(num_records: int = 50, include_duplicates: bool = True) -> str:
    """Generate a sample CSV for testing."""

    # Sample business data pools
    business_prefixes = ['Tech', 'Global', 'Indian', 'Super', 'Prime', 'Royal', 'Smart', 'Best', 'First', 'Metro']
    business_suffixes = ['Solutions', 'Services', 'Trading', 'Enterprises', 'Industries', 'Corporation', 'Limited', 'Company', 'Consultants', 'Exports']

    states = ['Maharashtra', 'Karnataka', 'Delhi', 'Tamil Nadu', 'Telangana', 'Gujarat', 'West Bengal']
    state_codes = {'Maharashtra': 'MH', 'Karnarashtra': 'KA', 'Delhi': 'DL', 'Tamil Nadu': 'TN', 'Telangana': 'TG', 'Gujarat': 'GJ', 'West Bengal': 'WB'}

    districts = {
        'Maharashtra': ['Mumbai', 'Pune', 'Nagpur', 'Thane'],
        'Karnataka': ['Bangalore', 'Mysore', 'Hubli', 'Mangalore'],
        'Delhi': ['New Delhi', 'North Delhi', 'South Delhi'],
        'Tamil Nadu': ['Chennai', 'Coimbatore', 'Madurai'],
        'Telangana': ['Hyderabad', 'Warangal', 'Nizamabad'],
        'Gujarat': ['Ahmedabad', 'Surat', 'Vadodara'],
        'West Bengal': ['Kolkata', 'Howrah', 'Darjeeling']
    }

    departments = ['GST', 'Income Tax', 'Commercial Tax', 'ROC', 'MSME']

    records = []
    generated_pans = []
    generated_gstins = []

    # Generate base records
    for i in range(num_records):
        state = random.choice(states)
        district = random.choice(districts.get(state, ['Central']))

        # Generate business name
        name = f"{random.choice(business_prefixes)} {random.choice(business_suffixes)}"
        if random.random() > 0.7:
            name = f"{name} {random.randint(1, 999)}"

        # Generate PAN (10 chars: 5 letters + 4 digits + 1 letter)
        pan = None
        if random.random() > 0.1:  # 90% have PAN
            pan = f"{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{random.randint(1000,9999)}{chr(65+random.randint(0,25))}"
            generated_pans.append(pan)

        # Generate GSTIN (15 chars: 2 state code + 10 PAN-like + 1Z + 1 digit/letter)
        gstin = None
        if random.random() > 0.1:  # 90% have GSTIN
            state_code = state_codes.get(state, '00')
            if pan:
                gstin = f"{state_code}{pan}{random.randint(1,9)}Z{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')}"
            else:
                gstin = f"{state_code}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{chr(65+random.randint(0,25))}{random.randint(1000,9999)}{chr(65+random.randint(0,25))}{random.randint(1,9)}Z{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')}"
            generated_gstins.append(gstin)

        # Generate address
        address = f"{random.randint(1, 999)}, {random.choice(['Main Road', 'Market Street', 'Industrial Area', 'Business Park'])}, {district}, {state}"

        # Generate pincode (6 digits)
        pincode = f"{random.randint(100000, 999999)}"

        # Generate dates
        reg_date = datetime(2015, 1, 1) + timedelta(days=random.randint(0, 3000))

        # Last activity based on status
        status_roll = random.random()
        if status_roll > 0.6:  # Active
            last_activity = datetime.now() - timedelta(days=random.randint(1, 180))
        elif status_roll > 0.3:  # Dormant
            last_activity = datetime.now() - timedelta(days=random.randint(365, 540))
        else:  # Closed
            last_activity = datetime.now() - timedelta(days=random.randint(600, 1000))

        department = random.choice(departments)

        records.append({
            'business_name': name,
            'pan': pan,
            'gstin': gstin,
            'address': address,
            'pincode': pincode,
            'district': district,
            'state': state,
            'registration_date': reg_date.strftime('%Y-%m-%d'),
            'last_activity_date': last_activity.strftime('%Y-%m-%d'),
            'department': department
        })

    # Add duplicates if requested
    if include_duplicates:
        # Create ~20% duplicates with variations
        num_duplicates = num_records // 5
        for i in range(num_duplicates):
            # Pick a random record to duplicate
            base_record = random.choice(records[:num_records])

            duplicate = base_record.copy()

            # Vary the name slightly
            duplicate['business_name'] = f"{base_record['business_name']} Pvt Ltd"

            # Keep same PAN or GSTIN (to create matches)
            if random.random() > 0.5 and base_record['pan']:
                pass  # Keep same PAN
            elif base_record['gstin']:
                pass  # Keep same GSTIN

            # Vary address slightly
            duplicate['address'] = f"Shop {random.randint(1, 50)}, {base_record['address'].split(', ', 1)[1] if ', ' in base_record['address'] else base_record['address']}"

            records.append(duplicate)

    # Convert to CSV string with proper quoting
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=REQUIRED_COLUMNS,
        quoting=csv.QUOTE_ALL,  # Quote all fields to prevent comma issues
        lineterminator='\n'
    )
    writer.writeheader()
    writer.writerows(records)

    return output.getvalue()


def get_status_badge_color(status: str) -> str:
    """Get Streamlit badge color for status."""
    status_colors = {
        'active': 'green',
        'dormant': 'orange',
        'closed': 'red',
        'merged': 'blue',
        'pending': 'yellow',
        'approved': 'green',
        'rejected': 'red'
    }
    return status_colors.get(status.lower(), 'gray')


def truncate_string(s: str, max_length: int = 50) -> str:
    """Truncate string to max length with ellipsis."""
    if not s:
        return ''
    if len(s) <= max_length:
        return s
    return s[:max_length-3] + '...'


def format_number(num: int) -> str:
    """Format number with commas."""
    return f"{num:,}"
