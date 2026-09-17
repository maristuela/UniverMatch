import re

class UnpackSpecDescriptions:
    def __init__(self):
        data = open("SpecialtiesDescriptions.txt", "r")
        lines = data.readlines()
        self.dictionary = dict()

        for i in range(0, len(lines) - 1, 2):
            a, b = lines[i], lines[i + 1]
            a = a.strip()
            b = b.strip()
            self.dictionary[a] = b

    def clean_text(self, x):
        cyrillic_only = re.sub(r'[^а-яёА-ЯЁ]', '', x)
        return cyrillic_only.lower()

    def getBySpeciality(self, x):
        return self.dictionary[self.clean_text(x)]

print(UnpackSpecDescriptions().getBySpeciality("Абоба"))