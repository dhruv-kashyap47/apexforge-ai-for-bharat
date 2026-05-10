# ApexForge AI — The Ultimate Beginner's Guide
## Unified Business Identity System: From Zero to Hero

---

## Table of Contents
1. [The Problem (Why This Exists)](#1-the-problem-why-this-exists)
2. [The Solution (What This Does)](#2-the-solution-what-this-does)
3. [Key Terminologies (Explained Like You're 5)](#3-key-terminologies-explained-like-youre-5)
4. [The Full Pipeline (Step-by-Step Journey)](#4-the-full-pipeline-step-by-step-journey)
5. [How to Use the App (Click-by-Click)](#5-how-to-use-the-app-click-by-click)
6. [Understanding the Dashboard](#6-understanding-the-dashboard)
7. [Understanding Analytics](#7-understanding-analytics)
8. [Understanding Match Tiers (The Heart of the System)](#8-understanding-match-tiers-the-heart-of-the-system)
9. [Understanding the Network Graph](#9-understanding-the-network-graph)
10. [Understanding the Review Queue](#10-understanding-the-review-queue)
11. [Understanding UBID Explorer](#11-understanding-ubid-explorer)
12. [Project Files Explained](#12-project-files-explained)
13. [Quick Setup](#13-quick-setup)

---

## 1. The Problem (Why This Exists)

### Imagine This Scenario

You work for the government. You have a **HUGE** list of businesses:
- Some registered with **GST** department
- Some registered with **Income Tax** department
- Some registered with **MCA** (Companies Registry)
- Some registered with **Labour** department

Now here's the **BIG PROBLEM**: The same business is registered **MULTIPLE TIMES** under **SLIGHTLY DIFFERENT NAMES** across different departments.

**Example:**
- GST Department: `Shetty Metal Works Pvt Ltd`
- Income Tax: `Shetty Metals Private Limited`
- MCA: `Shetti Metalworks P Ltd`
- Labour: `Shetty Metal Workz Pvt Ltd`

**Are these 4 different companies? NO! It's the SAME company!**

### Why This Is a Nightmare

1. **Duplicate Payments**: Government might pay subsidies to the same company 4 times
2. **Fake Companies**: Hard to spot shell companies hiding behind name variations
3. **No Single View**: No one knows how many UNIQUE businesses actually exist
4. **Wasted Resources**: Every department stores the same data separately
5. **Fraud**: Someone can register `Google India Pvt Ltd` and `Google India Limited` as two separate entities

### The Real-World Impact
- India has 70+ million registered businesses
- Estimates suggest 20-30% are duplicates
- That's **14-21 MILLION duplicate records**
- Billions of rupees in potential fraud and inefficiency

**This is why ApexForge AI exists.**

---

## 2. The Solution (What This Does)

### In One Sentence
ApexForge AI takes a messy list of business registrations, **finds the duplicates automatically**, assigns each unique business a **single identity number (UBID)**, and shows you **beautiful visualizations** of everything.

### What Happens When You Upload a CSV

```
Your CSV (Messy Data)
    ↓
[Data Cleaner] — Fixes spelling, formats, missing values
    ↓
[Status Analyzer] — Figures out if business is Active/Dormant/Closed
    ↓
[Matching Engine] — Finds duplicates using smart AI matching
    ↓
[UBID Generator] — Gives each unique business ONE permanent ID
    ↓
[Dashboard] — Shows you beautiful charts and insights
```

### The Magic Output

**Before:** 4 separate records for the same business
**After:** 1 UBID (`KA-BAN-TR-0001234`) linking all 4 records together

---

## 3. Key Terminologies (Explained Like You're 5)

### Business Record
A single row in your spreadsheet. One registration of one business.

**Example:**
```
Shetty Metal Works, ABCDE1234F, 29ABCDE1234F1Z5, Bengaluru, Karnataka
```

### Duplicate / Match
When two records are actually the same business, just written differently.

**Example:**
- Record 1: `Shetty Metal Works Pvt Ltd`
- Record 2: `Shetty Metals Private Limited`
- These are **MATCHES** (same business)

### PAN (Permanent Account Number)
A 10-letter code given by Income Tax department to every taxpayer.
- Format: `ABCDE1234F` (5 letters + 4 numbers + 1 letter)
- **If two records have the same PAN, they are DEFINITELY the same business.**

### GSTIN (GST Identification Number)
A 15-character code given to every business registered for GST.
- Format: `29ABCDE1234F1Z5` (State code + PAN + 1 digit + Z + 1 digit)
- **If two records have the same GSTIN, they are DEFINITELY the same business.**

### UBID (Unified Business Identity)
The **hero** of this system. A brand-new, clean ID that replaces all the messy old IDs.

**Format:** `ST-DST-CC-XXXXXXX`

| Part | What It Means | Example |
|------|--------------|---------|
| `ST` | 2-letter State Code | `KA` = Karnataka |
| `DST` | 3-letter District Code | `BAN` = Bengaluru |
| `CC` | 2-letter Category Code | `TR` = Trading |
| `XXXXXXX` | 7-digit Unique Number | `0001234` |

**Full Example:** `KA-BAN-TR-0001234` means:
- Karnataka state
- Bengaluru district
- Trading business
- Unique number 1234

### Confidence Score
A number from 0 to 100 telling you **HOW SURE** the system is that two records match.

- **95%** = "I'm 95% sure these are the same business"
- **72%** = "I'm 72% sure... maybe a human should check"
- **45%** = "Probably different businesses"

### Match Tier
How the match was found. Think of it as "detective levels":

- **Tier 1**: Found by exact PAN or GSTIN match (like finding the same fingerprint)
- **Tier 2**: Found by very similar name + same location (like recognizing someone by face)
- **Tier 3**: Found by somewhat similar name + same location (like a fuzzy memory)
- **New**: No match found at all (brand new, unique business)

### Match Decision
What the system decides to DO with the match:

- **Auto Merge** (≥90% confidence): "These are definitely the same. I'll merge them automatically."
- **Needs Review** (70-89% confidence): "I'm not 100% sure. A human should check this."
- **Keep Separate** (<70% confidence): "These look different. Keep them as separate businesses."

### Active / Dormant / Closed
The "health status" of a business based on when it last did something:

- **Active**: Did something in the last 12 months (alive and kicking!)
- **Dormant**: Nothing for 12-18 months (sleeping, might wake up)
- **Closed**: Nothing for 18+ months (probably dead)

### Fuzzy Matching
A smart technique that finds things that are **ALMOST the same** but not exactly.

**Example:**
- `Shetty Metal Works` and `Shetty Metals` are **fuzzy matches**
- The computer knows these are 95% similar

### Match Group
A cluster of records that all belong to the same business.

**Example:**
```
Group #1:
  - Shetty Metal Works Pvt Ltd (PAN: ABCDE1234F)
  - Shetty Metals Private Limited (PAN: ABCDE1234F)
  - Shetti Metalworks P Ltd (PAN: ABCDE1234F)
  
All 3 get the SAME UBID: KA-BAN-TR-0001234
```

---

## 4. The Full Pipeline (Step-by-Step Journey)

When you click **"Process file now"**, here's what happens behind the scenes:

### Step 1: Data Cleaning (0% → 20%)
**What it does:** Takes your messy data and makes it clean.

**Specific actions:**
- **Cleans business names**: Removes extra spaces, fixes spelling
  - `Shetty  Metal   Works` → `Shetty Metal Works`
  - `Shetty Metal Works Pvt Ltd` → `Shetty Metal Works` (removes suffixes like Pvt/Ltd)
- **Validates PAN**: Checks if PAN follows the correct format (5 letters + 4 numbers + 1 letter)
  - `ABCDE1234F` → Valid ✓
  - `ABCDE12345` → Invalid ✗
- **Validates GSTIN**: Checks if GSTIN follows the correct 15-character format
- **Normalizes addresses**: Removes inconsistencies
  - `42 Whitefield Rd` and `No.42 Whitefield Main Road` → standardized
- **Normalizes pincodes**: Ensures 6-digit format
- **Normalizes states**: Converts full state names to 2-letter codes
  - `Karnataka` → `KA`
  - `Maharashtra` → `MH`
- **Normalizes districts**: Creates 3-letter district codes
  - `Bengaluru Urban` → `BAN`
- **Parses dates**: Converts text dates to proper date format

**Output columns created:**
- `cleaned_name` — standardized business name
- `cleaned_pan` — validated PAN
- `cleaned_gstin` — validated GSTIN
- `cleaned_address` — standardized address
- `normalized_pincode` — 6-digit pincode
- `state_code` — 2-letter state code
- `district_code` — 3-letter district code
- `name_phonetic` — sound-alike code for matching

### Step 2: Status Analysis (20% → 40%)
**What it does:** Figures out if each business is Active, Dormant, or Closed.

**How it works:**
Looks at two dates:
1. `last_activity_date` — when did this business last file a return / do something?
2. `registration_date` — when was this business registered?

**Rules:**
```
If last_activity_date exists:
    If activity was within last 12 months → ACTIVE
    If activity was 12-18 months ago → DORMANT
    If activity was 18+ months ago → CLOSED

If last_activity_date is missing:
    If registered more than 18 months ago → CLOSED
    If registered 12-18 months ago → DORMANT
    Otherwise → CLOSED (no info at all)
```

**Output columns created:**
- `business_status` — Active / Dormant / Closed
- `status_reason` — Why this status was assigned
- `days_inactive` — How many days since last activity
- `months_inactive` — How many months since last activity

### Step 3: Finding Matches (40% → 60%)
**What it does:** Finds duplicate businesses.

**This is the brain of the system.**

**How it works (simplified):**

For EVERY record, the system asks:

#### Question 1: Does any other record have the same PAN or GSTIN? (Tier 1)
```
Record 1 PAN: ABCDE1234F
Record 2 PAN: ABCDE1234F
→ SAME PAN! These MUST be the same business!
Confidence: 100%
Decision: Auto Merge
```

#### Question 2: Does any other record have a VERY similar name in the SAME area? (Tier 2)
```
Record 1: "Shetty Metal Works" in Bengaluru, 560058
Record 2: "Shetty Metals" in Bengaluru, 560058
→ Name is 92% similar + same pincode!
Confidence: 92%
Decision: Auto Merge (because ≥90%)
```

#### Question 3: Does any other record have a SOMEWHAT similar name in the SAME area? (Tier 3)
```
Record 1: "Shetty Metal Works" in Bengaluru
Record 2: "Shetti Metalworks" in Bengaluru
→ Name is 78% similar + same city
Confidence: 78%
Decision: Needs Review (because 70-89%)
```

#### Question 4: Does any other record have a similar name but DIFFERENT area?
```
Record 1: "Shetty Metal Works" in Bengaluru
Record 2: "Shetty Metal Works" in Mumbai
→ Same name but different city!
Confidence: Low (location doesn't match)
Decision: Keep Separate
```

**The system uses "indexes" to be fast:**
Instead of comparing every record with every other record (which would take forever), it builds smart lookup tables:
- PAN Index: Groups all records with the same PAN
- GSTIN Index: Groups all records with the same GSTIN
- Pincode Index: Groups all records in the same pincode
- District Index: Groups all records in the same district
- Name Bucket Index: Groups records with similar-sounding names

This makes matching thousands of records possible in seconds.

**Output:**
- `matches` — list of all pairs that matched
- `match_groups` — clusters of related records
- `match_stats` — counts of tier1, tier2, tier3, auto_merge, needs_review

### Step 4: Assigning UBIDs (60% → 80%)
**What it does:** Gives every unique business a permanent ID.

**Rules:**
1. If records are matched (same group), they ALL get the SAME UBID
2. The first record in the group becomes the "Master"
3. All other records in the group become "Members"
4. Unmatched records get their own new UBID

**Example:**
```
Group 1: Shetty Metal Works (3 records)
  → Master: Record #1
  → Members: Record #2, Record #3
  → All get UBID: KA-BAN-TR-0001234

Group 2: Gowda Enterprises (2 records)
  → Master: Record #4
  → Member: Record #5
  → All get UBID: KA-BAN-RT-0001235

Record 6: Patel Textiles (no matches)
  → Gets its own UBID: GJ-AHM-MF-0001236
```

**Output columns created:**
- `ubid` — the unique business ID
- `is_master` — True for the main record in a group
- `match_confidence` — how sure we are about the match
- `match_tier` — Tier1 / Tier2 / Tier3 / New
- `matched_fields` — which fields matched (PAN, GSTIN, name, etc.)
- `match_decision` — AutoMerge / NeedsReview / KeepSeparate / New

### Step 5: Finalizing (80% → 100%)
**What it does:** Packages everything together for display.

- Attaches all UBID assignments to the main dataframe
- Attaches group summaries (how many records in each group)
- Stores everything in memory for the UI to display
- Creates a batch ID (like `BATCH-20240506-123045`) to identify this run

---

## 5. How to Use the App (Click-by-Click)

### Step 0: Start the App
Open your terminal and type:
```bash
streamlit run app.py
```
Your browser opens automatically to `http://localhost:8501`

### Step 1: Upload Page (Home Page)
**What you see:** A beautiful upload area with instructions.

**What to do:**
1. **Option A — Use your own data:**
   - Drag and drop your CSV file OR click to browse
   - Your CSV should have columns like: `business_name, pan, gstin, address, pincode, district, state, registration_date, last_activity_date, department`
   - The app will auto-detect columns even if your headers are slightly different!

2. **Option B — Use sample data:**
   - Click "Generate Sample CSV" to create test data
   - Download it and upload it back

3. **Click "Process file now"**
   - Wait for the progress bar to reach 100%
   - The system is cleaning, matching, and assigning UBIDs

### Step 2: Dashboard Page
**What you see:** A beautiful overview of your entire dataset.

**What to do:** Look at the metrics and charts. (Explained in Section 6 below)

### Step 3: Results Page
**What you see:** A table showing every processed record.

**What to do:**
- Scroll through the data
- See the UBID column — notice how duplicates share the same UBID
- See the `match_tier` column — shows how each match was found
- See the `business_status` column — Active/Dormant/Closed

### Step 4: Network Graph Page
**What you see:** A colorful interactive web of connected businesses.

**What to do:**
- Zoom in/out with your mouse wheel
- Drag nodes around
- Click on a node to see which records are connected
- Green = high confidence matches
- Orange = medium confidence
- Red = low confidence / needs review

### Step 5: UBID Explorer Page
**What you see:** A search tool for finding businesses.

**What to do:**
- Search by UBID, business name, PAN, or GSTIN
- See all records linked to that UBID
- Understand how the same business appears across departments

### Step 6: Review Queue Page
**What you see:** Records that need human verification.

**What to do:**
- Review pairs that the system flagged as "Needs Review"
- Compare two side-by-side records
- Approve if they're the same business → they get merged
- Reject if they're different → they stay separate

### Step 7: Analytics Page
**What you see:** Deep statistical insights.

**What to do:** Look at distributions and summaries. (Explained in Section 7 below)

---

## 6. Understanding the Dashboard

The Dashboard is your **mission control**. Every section tells you something important.

### Top KPI Cards (The Big Numbers)

| Card | What It Means | Example Value |
|------|--------------|---------------|
| **Total Records** | How many rows you uploaded | `60` |
| **UBIDs Generated** | How many UNIQUE businesses were found | `48` |
| **Match Rate** | What % of records found a duplicate | `35.0%` |
| **Avg Confidence** | Average certainty of all matches | `87.3%` |

**How to read them:**
- If **Total Records** = 60 and **UBIDs** = 48, that means 12 records were duplicates
- **Match Rate** = 35% means 35% of your records matched with at least one other record
- **Avg Confidence** = 87.3% means most matches are very reliable

### Business Status Chart (Left Side)
**What it shows:** A bar chart of Active vs Dormant vs Closed businesses.

**How to read it:**
- Tall green bar = many active businesses (good!)
- Tall orange bar = many dormant businesses (might need follow-up)
- Tall red bar = many closed businesses (clean up your data)

**Why it matters:**
- Active businesses = still operating, can be contacted
- Dormant businesses = might have stopped, investigate
- Closed businesses = can be archived or removed

### Match Decisions Chart (Right Side)
**What it shows:** A bar chart of Auto Merge vs Needs Review vs New records.

**How to read it:**
- **Auto Merge** = System was confident, merged automatically
- **Needs Review** = System was unsure, flagged for human check
- **New** = No duplicates found, brand new unique business

**Why it matters:**
- Lots of "Auto Merge" = your data has many clear duplicates
- Lots of "Needs Review" = your data has messy/ambiguous records
- Lots of "New" = your data is mostly unique (good quality!)

### Match Confidence Distribution
**What it shows:** How confident the system is, broken into buckets:
- 0–25%: Very unsure
- 26–50%: Probably different
- 51–75%: Maybe the same
- 76–90%: Likely the same
- 91–100%: Definitely the same

**How to read it:**
- Most bars should be on the RIGHT side (76-100%) = good matches
- Bars in the middle (50-75%) = need your attention
- Bars on the LEFT = probably false positives

### Match Tier Distribution
**What it shows:** How matches were found:
- **Tier1**: Found by exact PAN/GSTIN
- **Tier2**: Found by very similar name + location
- **Tier3**: Found by somewhat similar name + location
- **New**: No match at all

**How to read it:**
- Lots of Tier1 = your data has good identifier coverage
- Lots of Tier2 = your data has consistent naming but missing PANs
- Lots of Tier3 = your data has inconsistent naming, needs cleanup
- Lots of New = your data is mostly unique

### Geographic — Top States
**What it shows:** Which states have the most businesses.

**How to read it:**
- See where your businesses are concentrated
- Karnataka has 15? Maharashtra has 12? Now you know!

### Department / Industry Breakdown
**What it shows:** Which departments/industries your businesses belong to.

**How to read it:**
- GST: 30 records? Income Tax: 15? MCA: 10? Labour: 5?
- Helps you understand your data sources

### Data Quality Overview
**What it shows:** A table showing missing data in key fields.

| Field | Missing | Pct |
|-------|---------|-----|
| Business Name | 0 | 0.0% |
| Pan | 3 | 5.0% |
| Gstin | 8 | 13.3% |
| Address | 2 | 3.3% |

**How to read it:**
- **Missing** = how many records have blank values
- **Pct** = what percentage of total records
- High percentages = your data needs cleanup before processing

### Processing Summary
**What it shows:** A detailed table of ALL metrics.

**Key rows to watch:**
- **Batch ID**: Unique identifier for this processing run
- **Match Groups**: How many clusters of duplicates were found
- **Duplicate Rate**: What % of records are duplicates
- **Solo Record Rate**: What % of records are unique (no duplicates)

---

## 7. Understanding Analytics

The Analytics page gives you **deeper insights** than the Dashboard.

### What You See Here

1. **Status Distribution Chart**
   - Same as Dashboard but dedicated full view
   - Helps you focus just on business health

2. **Match Tier Distribution Chart**
   - Same as Dashboard but dedicated full view
   - Helps you focus just on match quality

3. **Recent Records Table**
   - Shows the first 20 processed records
   - Columns: UBID, business name, status, tier, confidence
   - Quick sanity check that processing worked correctly

### How to Use Analytics
- **Before making decisions:** Check the distribution charts to understand your data
- **After processing:** Verify that match tiers look reasonable
- **For reporting:** Use the numbers here in your presentations

---

## 8. Understanding Match Tiers (The Heart of the System)

This is the **most important concept** in ApexForge AI. Master this, and you master the system.

### Tier 1 — The Fingerprint Match (Exact Identifiers)

**How it works:**
The system finds two records with the **exact same PAN or exact same GSTIN**.

**Why this is powerful:**
- PAN and GSTIN are government-issued unique identifiers
- No two businesses can have the same PAN
- No two businesses can have the same GSTIN
- **If PAN matches = 100% guaranteed same business**

**Example:**
```
Record 1: Shetty Metal Works, PAN: ABCDE1234F
Record 2: Shetty Metals Pvt Ltd, PAN: ABCDE1234F
→ TIER 1 MATCH! Same PAN!
Confidence: 100%
Decision: Auto Merge
```

**When you see Tier 1:** You can trust it completely. The system never makes mistakes on Tier 1.

---

### Tier 2 — The Detective Match (Strong Name + Location)

**How it works:**
1. Name similarity is **85% or higher** (using fuzzy matching)
2. AND they are in the **same pincode OR same district**

**Why this works:**
- Two businesses with almost identical names in the same area are probably the same
- The system uses `RapidFuzz` library to calculate name similarity
- It ignores suffixes like "Pvt Ltd", "Limited", "Inc"

**Example:**
```
Record 1: "Shetty Metal Works", pincode: 560058
Record 2: "Shetty Metals", pincode: 560058
→ Name similarity: 92%
→ Same pincode
→ TIER 2 MATCH!
Confidence: 92%
Decision: Auto Merge (because ≥90%)
```

**Another example:**
```
Record 1: "Gowda Enterprises", district: Bengaluru
Record 2: "Gowda Ent.", district: Bengaluru Urban
→ Name similarity: 88%
→ Same district
→ TIER 2 MATCH!
Confidence: 88%
Decision: Needs Review (because 70-89%)
```

**When you see Tier 2:** Usually correct, but double-check if confidence is below 90%.

---

### Tier 3 — The Hunch Match (Moderate Name + Location)

**How it works:**
1. Name similarity is **70% to 85%**
2. AND they are in the **same pincode OR same district**

**Why this is tricky:**
- The names are similar but not extremely close
- Could be the same business with a typo
- Could be two different but related businesses

**Example:**
```
Record 1: "Shetti Metalworks", pincode: 560058
Record 2: "Shetty Metal Works", pincode: 560058
→ Name similarity: 78%
→ Same pincode
→ TIER 3 MATCH!
Confidence: 78%
Decision: Needs Review
```

**When you see Tier 3:** ALWAYS review manually. These need human judgment.

---

### New — The Lone Wolf (No Match Found)

**How it works:**
No other record has the same PAN, GSTIN, or a similar enough name in the same area.

**What happens:**
- The record gets its own brand-new UBID
- It becomes a "Master" record with no members
- Confidence: 100% (because there's nothing to be unsure about)

**Example:**
```
Record: "Patel Textiles Pvt Ltd", PAN: FGHIJ5678K
No other record has PAN FGHIJ5678K
No other record has a similar name in the same area
→ NEW RECORD!
Gets UBID: GJ-AHM-MF-0001234
```

**When you see New:** This is a unique business. No duplicates found.

---

### Confidence Score Deep Dive

**How confidence is calculated:**

| Match Type | Confidence | Why |
|-----------|-----------|-----|
| Same PAN | 100% | Government ID is unique |
| Same GSTIN | 100% | Government ID is unique |
| Name 95% + Same Pincode | 95% | Very likely same |
| Name 90% + Same District | 90% | Likely same |
| Name 85% + Same Pincode | 85% | Probably same |
| Name 78% + Same District | 78% | Maybe same |
| Name 65% + Same Pincode | 65% | Uncertain |

**Confidence thresholds:**
- **≥90%** → Auto Merge (system decides automatically)
- **70-89%** → Needs Review (human must decide)
- **<70%** → Keep Separate (system decides they're different)

---

## 9. Understanding the Network Graph

### What It Is
A **visual web** showing how businesses are connected to each other.

### How to Read It
- **Each dot (node)** = one business record
- **Lines between dots (edges)** = a match was found
- **Colors** = match tier
  - Green = Tier 1 (exact identifier)
  - Blue = Tier 2 (strong fuzzy)
  - Orange = Tier 3 (moderate fuzzy)
- **Line thickness** = confidence (thicker = more confident)

### What to Look For
1. **Clusters (groups of connected dots)** = duplicate groups
   - A cluster of 4 dots = 4 records for the same business
2. **Solo dots** = unique businesses with no duplicates
3. **Central dots** = the "Master" record in a group
4. **Orange lines** = matches that need review

### How to Interact
- **Zoom**: Scroll mouse wheel
- **Pan**: Click and drag background
- **Move nodes**: Click and drag individual dots
- **Hover**: See record details
- **Click**: See connections highlighted

---

## 10. Understanding the Review Queue

### What It Is
A list of **uncertain matches** that need a human to decide.

### When Something Goes to Review Queue
Any match with confidence between **70% and 89%**.

**Examples of "Needs Review":**
- `Krishna Dairy` vs `Krishna Dairy Products` — are they the same?
- `Banerjee Software` vs `Banerjee Software Solutions` — same company?
- `Agarwal Cement Traders` vs `Agarwal Cement Trading` — same business?

### How to Decide
**Approve (Merge) if:**
- The businesses are clearly the same
- Same owner, same address, same activity
- Only difference is suffix (Pvt Ltd vs Limited) or spelling

**Reject (Keep Separate) if:**
- Different owners
- Different addresses
- Different business activities
- One is a parent company, one is a subsidiary

### Why This Matters
The Review Queue is where **human intelligence** beats AI. Some decisions need context that computers don't have.

---

## 11. Understanding UBID Explorer

### What It Does
Lets you **search for any business** and see its full identity profile.

### Search Options
1. **By UBID**: Enter `KA-BAN-TR-0001234`
2. **By Business Name**: Enter `Shetty Metal Works`
3. **By PAN**: Enter `ABCDE1234F`
4. **By GSTIN**: Enter `29ABCDE1234F1Z5`

### What You See
For any UBID, you see:
- **Master Record**: The primary record
- **Member Records**: All duplicates linked to it
- **Match Confidence**: How sure the system is
- **Match Tier**: How the match was found
- **Status**: Active/Dormant/Closed

### Use Cases
- **Verify a duplicate**: "Show me all records for UBID KA-BAN-TR-0001234"
- **Investigate fraud**: "Show me all businesses with PAN ABCDE1234F"
- **Audit**: "Show me all records from the GST department"

---

## 12. Project Files Explained

### Main Application
- **`app.py`** — The entire user interface and app logic. This is what runs when you type `streamlit run app.py`.

### Core Logic (The Brain)
- **`core/data_cleaner.py`** — Cleans and fixes your data
- **`core/matching_engine.py`** — Finds duplicates using smart algorithms
- **`core/status_analyzer.py`** — Determines if businesses are Active/Dormant/Closed
- **`core/ubid_generator.py`** — Creates unique UBIDs

### Sample Data
- **`india_govt_business_data.csv`** — A sample file with realistic Indian business data
- **`apexforge_rich_sample.csv`** — A test file specifically designed to trigger all features

### Configuration
- **`requirements.txt`** — List of Python libraries needed
- **`schema.sql`** — Database table definitions (if using PostgreSQL)
- **`.env.example`** — Template for database credentials

---

## 13. Quick Setup

### 1. Install Python Dependencies
```bash
pip install -r requirements.txt
```

If you plan to use the optional AI explanation feature, also set `GEMINI_API_KEY` in your `.env` file. The app will stay fully functional without it.

### 2. (Optional) Set Up Database
If you want to save results to PostgreSQL:
```bash
# Create a .env file with your database URL
echo "DATABASE_URL=postgresql://user:password@localhost:5432/apexforge_db" > .env
```

When `DATABASE_URL` is set, ApexForge AI now uses a safe database-backed pipeline that writes raw records, match logs, matched groups, review items, and UBIDs into Neon/PostgreSQL without dropping existing data.

If you DON'T set up a database, the app works in **Local Mode** — all data stays in memory.

### 3. Run the App
```bash
streamlit run app.py
```

### 4. Test with Sample Data
1. Click **"Generate Sample CSV"** on the Upload page
2. Download the file
3. Upload it back
4. Click **"Process file now"**
5. Explore all the pages!

---

## Summary Cheat Sheet

| Question | Answer |
|----------|--------|
| What does this app do? | Finds duplicate businesses and gives them unique IDs |
| What file do I upload? | A CSV with business data |
| What is a UBID? | A clean, unique ID for each business |
| What is a Match? | Two records that are the same business |
| What is Tier 1? | Exact PAN/GSTIN match (100% reliable) |
| What is Tier 2? | Very similar name + same location (85-100% confidence) |
| What is Tier 3? | Somewhat similar name + same location (70-85% confidence) |
| What is Auto Merge? | System automatically merged duplicates |
| What is Needs Review? | System is unsure, needs human check |
| What is Active? | Business had activity in last 12 months |
| What is Dormant? | No activity for 12-18 months |
| What is Closed? | No activity for 18+ months |
| What is Match Rate? | % of records that found a duplicate |
| What is Confidence? | How sure the system is (0-100%) |

---

**You are now ready to use ApexForge AI like a pro!** 🚀
