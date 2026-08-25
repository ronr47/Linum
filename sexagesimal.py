"""
SEXAGESIMAL TRANSFORMATION MATRIX - BASE-60 GNOMON CONVERSION
"""

def convert_to_sexagesimal(decimal_value: int) -> str:
    major = decimal_value // 60
    minor = decimal_value % 60
    return f"[{major}; {minor:02d}]_{{60}}"


if __name__ == "__main__":
    area_delta = 96
    result = convert_to_sexagesimal(area_delta)
    print(f"[*] Decimal Area Allocation: {area_delta}")
    print(f"[*] Sexagesimal Coordinates: {result}")
