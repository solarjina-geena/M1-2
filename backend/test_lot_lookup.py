from lot_lookup import lot_to_date, find_lot_date
cases = {
    'ZID': '2026-09-04', 'ZIF': '2026-09-06',
    'ZIA': '2026-09-01', 'ZI6': '2026-09-31',
    'ZJ2': '2026-10-27', 'ZJL': '2026-10-12',
    'ZID ': '2026-09-04', 'ZZZ': None,
}
for code, expected in cases.items():
    if code == 'ZI6': expected = None  # Sep 31 invalid
    actual = lot_to_date(code)
    assert actual == expected, (code, actual, expected)
    print('PASS', repr(code), actual)
assert find_lot_date('ZID LOT 추적')['date'] == '2026-09-04'
assert find_lot_date('2026-09-04') is None
print('PASS standalone LOT detection')
