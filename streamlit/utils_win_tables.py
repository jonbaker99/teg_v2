from io import StringIO
import pandas as pd
from utils import convert_trophy_name, TROPHY_NAME_LOOKUPS_LONGSHORT, TROPHY_NAME_LOOKUPS_SHORTLONG
from typing import Iterable, Sequence, Union

def summarise_teg_wins(df, column_name):
    """
    Summarises a DataFrame by a specified column, counting TEGs and listing them.

    Args:
        df (pd.DataFrame): The input DataFrame
        column_name (str): The column to group by.

    Returns:
        pd.DataFrame: A summarized and sorted DataFrame.
    """

    key = column_name.strip()
    
    if key.lower() in TROPHY_NAME_LOOKUPS_LONGSHORT:  
        # it's already a long name → use as-is
        column_name = key
    else:
        # otherwise assume it's a short name → convert
        column_name = convert_trophy_name(key)
    

    # Select only the relevant columns and drop rows with NaN values
    temp_df = df[['TEG', column_name]].dropna(subset=[column_name])

    # Group by the specified column and aggregate
    summary_df = temp_df.groupby(column_name).agg(
        Wins=('TEG', 'count'),
        TEGs=('TEG', list)
    ).reset_index()

    # Rename the grouping column to 'Player'
    summary_df.rename(columns={column_name: 'Player'}, inplace=True)
    
    # Sort by the number of wins in descending order
    sorted_summary_df = summary_df.sort_values(by='Wins', ascending=False)
    
    # Convert the list of TEGs to a comma-separated string
    sorted_summary_df['TEGs'] = sorted_summary_df['TEGs'].apply(', '.join)
    
    return sorted_summary_df


from typing import Sequence, Union

def compress_ranges(
    data: Union[str, Sequence[int]],
    *,
    sep: str = ",",
    out_sep: str = ", ",
    sort: bool = True,
    dedupe: bool = True
) -> str:
    """
    Accepts either:
      - a comma-separated string of integers (e.g. "1,2,3,5,6,9,11"), or
      - a sequence of integers (e.g. [1,2,3,5,6,9,11])

    Returns a string where only runs of >=3 consecutive integers are collapsed
    into ranges (e.g. "1,2, 4-6, 9, 11"). Pairs are left uncollapsed.

    Options:
      - sep: input separator for string data (default ",")
      - out_sep: output separator between items (default ", ")
      - sort: sort the numbers before compressing (default True)
      - dedupe: remove duplicates (default True)
    """
    # 1) Normalise input -> list[int]
    if isinstance(data, str):
        if not data.strip():
            nums = []
        else:
            try:
                nums = [int(tok.strip()) for tok in data.split(sep) if tok.strip() != ""]
            except ValueError as e:
                raise ValueError(f"Non-integer token found in string: {e}")
    else:
        nums = list(map(int, data))

    if not nums:
        return ""

    # 2) Optionally sort and/or deduplicate
    if sort:
        nums = sorted(nums)
    if dedupe:
        seen = set()
        nums = [x for x in nums if (x not in seen and not seen.add(x))]

    # 3) Identify consecutive runs
    runs = []
    start = prev = nums[0]
    for n in nums[1:]:
        if n == prev + 1:
            prev = n
            continue
        runs.append((start, prev))
        start = prev = n
    runs.append((start, prev))  # close final run

    # 4) Build output parts: collapse only if run length >= 3
    parts: list[str] = []
    for a, b in runs:
        length = b - a + 1
        if length >= 3:
            parts.append(f"{a}-{b}")
        elif length == 2:
            parts.extend([f"{a}", f"{b}"])
        else:
            parts.append(f"{a}")

    return out_sep.join(parts)

