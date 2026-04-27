from random import randint

def random_number():
    randomValue = randint(1, 100)
    print("The random number is: ", randomValue)
    return randomValue

trueNumber = random_number()

while True:
    guess = int(input("Guess a number between 1 and 100: "))

    if guess == trueNumber:
        print("Congratulations! You guessed the number.")
        print()
        trueNumber = random_number()
    elif guess < trueNumber:
        print("Too low! Try again.")
    else:
        print("Too high! Try again.")
