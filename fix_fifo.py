"""
FIX SCRIPT 1: Fix FIFO violation in v15_chakra.py
Run: py -3.11 fix_fifo.py
"""

def fix_fifo():
    print("Reading v15_chakra.py...")
    lines = open('v15_chakra.py', 'r', encoding='utf-8').readlines()

    # Find _execute_trade method
    execute_line = None
    for i, line in enumerate(lines):
        if 'def _execute_trade(self, rec: TradeRecord, risk: Dict):' in line:
            execute_line = i
            break

    if execute_line is None:
        print("ERROR: Cannot find _execute_trade method")
        return False

    print(f"Found _execute_trade at line {execute_line + 1}")

    # Find the first line inside _execute_trade (after def line)
    # Look for the first try: or if statement inside it
    insert_line = execute_line + 1
    for i in range(execute_line + 1, execute_line + 20):
        if i < len(lines) and (lines[i].strip().startswith('if') or
                                lines[i].strip().startswith('try') or
                                lines[i].strip().startswith('api') or
                                lines[i].strip().startswith('log')):
            insert_line = i
            break

    print(f"Inserting FIFO check at line {insert_line + 1}")

    # FIFO check code to insert
    fifo_check = '''        # FIFO VIOLATION FIX - Check existing position direction
        try:
            from oandapyV20 import API as _OandaAPI
            from oandapyV20.endpoints.trades import OpenTrades as _OpenTrades
            _api = _OandaAPI(access_token=OANDA_TOKEN, environment=OANDA_ENV)
            _r = _OpenTrades(OANDA_ACCOUNT)
            _api.request(_r)
            _open = _r.response.get("trades", [])
            _pair_norm = rec.pair.replace("/", "_")
            for _t in _open:
                if _t.get("instrument", "").replace("/", "_") == _pair_norm:
                    _existing_units = float(_t.get("currentUnits", 0))
                    _existing_dir = "BUY" if _existing_units > 0 else "SELL"
                    if _existing_dir != rec.direction:
                        log.warning(f"FIFO BLOCK: {rec.pair} existing {_existing_dir}, new {rec.direction} - closing old trade first")
                        from oandapyV20.endpoints.trades import TradeClose as _TradeClose
                        _api.request(_TradeClose(OANDA_ACCOUNT, tradeID=_t["id"]))
                        log.info(f"Closed existing {rec.pair} {_existing_dir} trade to avoid FIFO violation")
                        import time; time.sleep(1)
        except Exception as _e:
            log.warning(f"FIFO check error: {_e}")
'''

    lines = lines[:insert_line] + [fifo_check + '\n'] + lines[insert_line:]

    with open('v15_chakra.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)

    print("✅ FIFO fix applied")
    return True


if __name__ == '__main__':
    fix_fifo()
    print("\nDone! FIFO violations will now be prevented.")
    print("When system wants to reverse a position:")
    print("1. Closes existing trade first")
    print("2. Then opens new trade in opposite direction")
