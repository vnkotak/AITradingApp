#!/usr/bin/env python3
from scanner import scan_once

if __name__ == "__main__":
    print("Testing optimized scanner...")
    result = scan_once(mode='5m', max_symbols=3)
    print("Scan result:", result)