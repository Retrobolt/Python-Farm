
class Tail:
    def __init__(self, value, bone = None):
        self.value = value
        self.bone = bone


part4 = Tail(20, None)
part3 = Tail(15, part4)
part2 = Tail(10, part3)
part1 = Tail(5, part2)

currentPart = part1

while currentPart is not None:
    print(currentPart.value)
    currentPart = currentPart.bone
