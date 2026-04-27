class reptile:
    def __init__(self, length):
        self.length = length

class snake(reptile):
    def sliver(self):
        print("I'm a snake 🐍")

s1 = snake(5)
lizard = reptile(3)
print(s1.length)
print(lizard.length)
s1.sliver()
""

