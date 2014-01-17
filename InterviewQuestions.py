import os
from   Utility.Utility import *
import Utility.Actions as Actions

RomanValue = dictn({
    'I' :    1,
    'V' :    5,
    'X' :   10,
    'L' :   50,
    'C' :  100,
    'D' :  500,
    'M' : 1000,
    })

@action
def ConvertRomanNumeral(RomanNumeral=''):
    """
        Key is to keep running total of current digits (III) == 3
        When arrive at new letter, if new is greater than previous:
            negate running total and add to total
        Repeat
    """
    Trace(RomanNumeral)
    if not RomanNumeral or len(RomanNumeral) == 0:
        return 0

    digitValue = 0
    current = 0
    total = 0

    for letter in RomanNumeral.upper():
        curValue = RomanValue.get(letter, None)
        if not curValue:
            Error('Invalid roman numeral [letter] in [RomanNumeral]')

        if digitValue != curValue:
            if digitValue < curValue:
                current *= -1
            total += current
            current = 0
            digitValue = curValue

        current += curValue

    total += current
    Log('[RomanNumeral] = [total]')
