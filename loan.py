owed = float(input('Starting Loan: '))
payment = float(input('Monthly Payment: '))
interest = float(input('Yearly Interest Rate: '))

interest_monthly = (interest / 12) / 100
month = 0

while owed > 0:
    print(owed)
    owed = owed - payment
    owed = owed + (owed * interest_monthly)
    month += 1

print(f'Months to pay off: {month}')