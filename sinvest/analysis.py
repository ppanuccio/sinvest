"""Main module for investment analysis"""

def analyze_investment(principal: float, rate: float, time: float) -> float:
    """
    Calculate the future value of an investment
    
    Args:
        principal (float): Initial investment amount
        rate (float): Annual interest rate (as decimal)
        time (float): Time period in years
        
    Returns:
        float: Future value of the investment
    """
    return principal * (1 + rate) ** time