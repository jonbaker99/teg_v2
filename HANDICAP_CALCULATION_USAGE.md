# TEG Handicap Calculation Function

## Overview

The `calculate_handicaps_for_teg()` function calculates handicaps for a given TEG based on a weighted average of adjusted gross scores from the previous two TEGs.

## Handicap Calculation Formula

Handicaps are calculated using:
- **75% weight** from the most recent previous TEG (target_teg - 1)
- **25% weight** from the previous TEG (target_teg - 2)
- **Adjusted gross score** = 36 - average stableford per round + handicap
- Players missing from a TEG are deemed to have scored **36 stableford points per round**

### Example Calculation
For TEG 18 handicap calculation:
- Use 75% of TEG 17 adjusted gross + 25% of TEG 16 adjusted gross
- If a player with a 15 handicap scored 152 stableford points over 4 rounds in TEG 17:
  - Average stableford per round = 152/4 = 38
  - Adjusted gross score = 36 - 38 + 15 = 13
  - This adjusted gross contributes 75% to the new handicap calculation

## Function Usage

### Basic Usage
```python
from utils import calculate_handicaps_for_teg

# Calculate handicaps for TEG 18 (uses TEG 16 and 17 data)
handicaps_df = calculate_handicaps_for_teg(18)
print(handicaps_df[['Player', 'Handicap']])
```

### Advanced Usage
```python
# Load data first and calculate with options
from utils import calculate_handicaps_for_teg, load_all_data

# Load data with incomplete TEGs included
all_data = load_all_data(exclude_incomplete_tegs=False)

# Calculate handicaps including incomplete TEG data
handicaps_df = calculate_handicaps_for_teg(
    target_teg_num=19,
    all_data=all_data,
    include_incomplete=True
)

# Display detailed results
for _, row in handicaps_df.iterrows():
    print(f"{row['Player']:15} | Handicap: {row['Handicap']:2.0f} | "
          f"TEG18 Score: {row['TEG1_Score']:5.1f} | "
          f"TEG17 Score: {row['TEG2_Score']:5.1f}")
```

## Function Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `target_teg_num` | int | Required | TEG number to calculate handicaps for (must be ≥17) |
| `all_data` | pd.DataFrame | None | Tournament data. If None, loads automatically |
| `include_incomplete` | bool | False | Whether to include incomplete TEGs in calculation |

## Return Value

Returns a pandas DataFrame with columns:
- `Player`: Player name
- `Handicap`: Calculated handicap (rounded to nearest integer)
- `TEG1_Score`: Average stableford per round in most recent TEG
- `TEG2_Score`: Average stableford per round in previous TEG
- `TEG1_Adjusted`: Adjusted gross score for most recent TEG
- `TEG2_Adjusted`: Adjusted gross score for previous TEG
- `TEG1_HC`: Handicap used for most recent TEG
- `TEG2_HC`: Handicap used for previous TEG

## Requirements and Limitations

### TEG Requirements
- **Minimum TEG**: Function works for TEG 17 and later only
- **Data Dependencies**: Requires handicaps.csv file with historical handicap data
- **Player Mapping**: Uses predefined mapping between player codes and full names

### Player Handling
- Players who didn't participate in a TEG are assigned 36 stableford points per round
- Default handicap of 18 is used if historical handicap data is unavailable
- All players who have ever played are included in the calculation

### Error Handling
```python
try:
    handicaps = calculate_handicaps_for_teg(16)  # Will fail
except ValueError as e:
    print(f"Error: {e}")
    # Output: Cannot calculate handicaps for TEG 16: requires TEG 15 or later
```

## Integration with Existing Pages

### Adding to Handicaps Page (500Handicaps.py)
```python
# Add this to show calculated vs current handicaps
from utils import calculate_handicaps_for_teg

# Calculate next TEG handicaps
next_teg_num = 19
calculated_handicaps = calculate_handicaps_for_teg(next_teg_num)

st.subheader(f"Calculated TEG {next_teg_num} Handicaps")
st.write(calculated_handicaps[['Player', 'Handicap']].to_html(index=False), 
         unsafe_allow_html=True)
```

### Creating New Analysis Page
```python
import streamlit as st
from utils import calculate_handicaps_for_teg, load_datawrapper_css

st.title("Handicap Calculator")
load_datawrapper_css()

teg_num = st.number_input("Calculate handicaps for TEG:", 
                         min_value=17, max_value=25, value=19)

if st.button("Calculate"):
    handicaps = calculate_handicaps_for_teg(teg_num)
    st.write(f"Handicaps for TEG {teg_num}:")
    st.dataframe(handicaps)
```

## Validation

The function has been tested and validated against the current handicap values in `500Handicaps.py`:

| Player | Expected (TEG 18) | Calculated | Status |
|--------|------------------|------------|---------|
| Gregg WILLIAMS | 20 | 20 | ✅ PASS |
| David MULLIN | 20 | 20 | ✅ PASS |
| Jon BAKER | 18 | 18 | ✅ PASS |
| John PATTERSON | 28 | 28 | ✅ PASS |
| Stuart NEUMANN | 27 | 27 | ✅ PASS |
| Alex BAKER | 36 | 36 | ✅ PASS |

## Notes

- The function automatically handles the Railway vs local environment data loading
- Caching warnings from Streamlit can be ignored when running outside the Streamlit environment
- Player name mapping may need updates if new players join future TEGs