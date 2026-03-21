# test_feature_validation.py - Run in your project

from simpandas import SimDataFrame, SimSeries
import pandas as pd
import numpy as np

# Test 1: GroupBy
print("=" * 60)
print("TEST 1: GroupBy")
print("=" * 60)

sdf = SimDataFrame({
    'group': ['A', 'A', 'B', 'B', 'C', 'C'],
    'value': [10, 20, 30, 40, 50, 60],
    'weight': [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
}, units={'value': 'm', 'weight': 'kg'})

print("Original DataFrame units:", sdf.get_units())

# GroupBy sum
grouped = sdf.groupby('group')['value'].sum()
print(f"Type of grouped.sum(): {type(grouped)}")
print(f"Units preserved: {getattr(grouped, 'units', 'NO UNITS ATTRIBUTE')}")
if hasattr(grouped, 'get_units'):
    print(f"Units via get_units(): {grouped.get_units()}")

# GroupBy with multiple columns
grouped_df = sdf.groupby('group').sum()
print(f"\nType of groupby().sum(): {type(grouped_df)}")
if hasattr(grouped_df, 'get_units'):
    print(f"Units via get_units(): {grouped_df.get_units()}")
else:
    print("No get_units method")

# Test 2: Rolling
print("\n" + "=" * 60)
print("TEST 2: Rolling")
print("=" * 60)

ss = SimSeries([1, 2, 3, 4, 5], units='m', name='distance')
print("Original Series units:", ss.units)

rolling = ss.rolling(2)
print(f"Type of rolling object: {type(rolling)}")

if hasattr(rolling, 'mean'):
    result = rolling.mean()
    print(f"Type of rolling.mean(): {type(result)}")
    if hasattr(result, 'units'):
        print(f"Units preserved: {result.units}")

# Test 3: Value Counts
print("\n" + "=" * 60)
print("TEST 3: Value Counts")
print("=" * 60)

ss2 = SimSeries(['a', 'b', 'a', 'c', 'b', 'a'], units='', name='category')
vc = ss2.value_counts()
print(f"Type of value_counts(): {type(vc)}")
if hasattr(vc, 'units'):
    print(f"Units: {vc.units}")

# Test 4: Unique
print("\n" + "=" * 60)
print("TEST 4: Unique")
print("=" * 60)

ss3 = SimSeries([1, 2, 1, 3, 2], units='kg', name='mass')
try:
    unique_values = ss3.unique()
    print(f"Type of unique(): {type(unique_values)}")
    print(f"Has units: {hasattr(unique_values, 'units')}")
except Exception as e:
    print(f"unique() not available: {e}")

# Test 5: Apply
print("\n" + "=" * 60)
print("TEST 5: Apply")
print("=" * 60)

sdf2 = SimDataFrame({
    'A': [1, 2, 3],
    'B': [4, 5, 6]
}, units={'A': 'm', 'B': 's'})

try:
    result = sdf2.apply(np.sum)
    print(f"Type of apply(np.sum): {type(result)}")
    if hasattr(result, 'units'):
        print(f"Units: {result.units}")
except Exception as e:
    print(f"apply() issue: {e}")

# Test 6: Where (mask)
print("\n" + "=" * 60)
print("TEST 6: Where")
print("=" * 60)

ss4 = SimSeries([1, 2, 3, 4, 5], units='ft', name='height')
try:
    result = ss4.where(ss4 > 2)
    print(f"Type of where(): {type(result)}")
    if hasattr(result, 'units'):
        print(f"Units preserved: {result.units}")
except Exception as e:
    print(f"where() issue: {e}")