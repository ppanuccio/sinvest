"""Test cases for investment analysis"""
import pytest
from sinvest.analysis import analyze_investment

def test_analyze_investment():
    """Test basic investment calculation"""
    assert analyze_investment(1000, 0.05, 1) == 1050.0
    assert analyze_investment(1000, 0.05, 2) == 1102.5